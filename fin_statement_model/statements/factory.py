"""Statement Factory/Processor module.

Provides high-level functions to orchestrate the process of loading statement
configurations, building structures, populating a financial model graph, and
generating formatted outputs (like DataFrames or files).

This module acts as a primary entry point for users wanting to work with
financial statements defined by configuration files.
"""

import logging
from pathlib import Path
from typing import Any, Union, Optional

import pandas as pd

# Core components
from fin_statement_model.core.graph import Graph
from fin_statement_model.core.errors import (
    FinancialModelError,
    StatementError,
    ConfigurationError,
)

# IO Layer components
from fin_statement_model.io.readers import statement_config_reader
from fin_statement_model.io.writers import statement_writer
from fin_statement_model.io.exceptions import ReadError, WriteError

# Statements layer components
from .config.config import StatementConfig
from fin_statement_model.statements.registry import StatementRegistry
from fin_statement_model.statements.builder import StatementStructureBuilder
from fin_statement_model.statements.populator import populate_graph_from_statement
from fin_statement_model.statements.formatter import StatementFormatter

logger = logging.getLogger(__name__)

__all__ = [
    "create_statement_dataframe",
    "export_statements_to_excel",
    "export_statements_to_json",
    # Removed StatementFactory class, using functions now
]


def _load_build_register_statements(
    config_path_or_dir: str,
    registry: StatementRegistry,
    builder: StatementStructureBuilder,
) -> list[str]:
    """Load, validate, build, and register statement structures from configs.

    This is an internal helper function orchestrating the first part of the
    statement processing pipeline. It reads configurations, validates them using
    StatementConfig, builds the structure using StatementStructureBuilder, and
    registers them with the provided StatementRegistry.

    Args:
        config_path_or_dir: Path to a single statement config file (e.g.,
            'income_statement.yaml') or a directory containing multiple
            config files.
        registry: The StatementRegistry instance to register loaded statements.
        builder: The StatementStructureBuilder instance used to construct
            statement objects from validated configurations.

    Returns:
        A list of statement IDs that were successfully loaded and registered.

    Raises:
        ConfigurationError: If reading or validation of any configuration fails.
        FileNotFoundError: If the `config_path_or_dir` does not exist.
        StatementError: If registration fails (e.g., duplicate ID).
    """
    loaded_statement_ids = []
    errors = []

    try:
        if Path(config_path_or_dir).is_dir():
            raw_configs = statement_config_reader.read_statement_configs_from_directory(
                config_path_or_dir
            )
        elif Path(config_path_or_dir).is_file():
            stmt_id = Path(config_path_or_dir).stem
            raw_config = statement_config_reader.read_statement_config_from_path(config_path_or_dir)
            raw_configs = {stmt_id: raw_config}
        else:
            raise FileNotFoundError(
                f"Config path is not a valid file or directory: {config_path_or_dir}"
            )

    except (ReadError, FileNotFoundError) as e:
        logger.exception(f"Failed to read configuration from {config_path_or_dir}:")
        # Re-raise as a ConfigurationError maybe?
        raise ConfigurationError(
            message=f"Failed to read config: {e}", config_path=config_path_or_dir
        ) from e

    if not raw_configs:
        logger.warning(f"No statement configurations found at {config_path_or_dir}")
        return []

    for stmt_id, raw_data in raw_configs.items():
        try:
            config = StatementConfig(raw_data)
            validation_errors = config.validate_config()
            if validation_errors:
                raise ConfigurationError(
                    f"Invalid configuration for statement '{stmt_id}'",
                    config_path=f"{config_path_or_dir}/{stmt_id}.ext",  # Placeholder path
                    errors=validation_errors,
                )

            statement = builder.build(config)
            registry.register(statement)  # Raises StatementError on conflict
            loaded_statement_ids.append(statement.id)

        except (ConfigurationError, StatementError, ValueError) as e:
            logger.exception(f"Failed to process/register statement '{stmt_id}':")
            errors.append((stmt_id, str(e)))
        except Exception as e:
            logger.exception(
                f"Unexpected error processing statement '{stmt_id}' from {config_path_or_dir}"
            )
            errors.append((stmt_id, f"Unexpected error: {e!s}"))

    # Handle errors - maybe raise an aggregate error if any occurred?
    if errors:
        # For now, just log a warning, processing continues with successfully
        # loaded statements
        error_details = "; ".join([f"{sid}: {msg}" for sid, msg in errors])
        logger.warning(
            f"Encountered {len(errors)} errors during statement loading/building "
            f"from {config_path_or_dir}: {error_details}"
        )
        # Consider raising an aggregated error if needed for stricter handling

    return loaded_statement_ids


def _populate_graph(registry: StatementRegistry, graph: Graph) -> list[tuple[str, str]]:
    """Populate the graph with nodes based on registered statements.

    Internal helper function that iterates through all statements registered
    in the `registry` and uses `populate_graph_from_statement` to add the
    corresponding nodes and relationships to the `graph`.

    Args:
        registry: The StatementRegistry containing the statements to process.
        graph: The Graph instance to be populated.

    Returns:
        A list of tuples, where each tuple contains (item_id, error_message)
        for any items that failed during population. Returns an empty list if
        population was successful for all items.
    """
    all_populator_errors = []
    statements = registry.get_all_statements()
    if not statements:
        logger.warning("No statements registered to populate the graph.")
        return []

    for statement in statements:
        populator_errors = populate_graph_from_statement(statement, graph)
        if populator_errors:
            all_populator_errors.extend(
                [(statement.id, item_id, msg) for item_id, msg in populator_errors]
            )

    if all_populator_errors:
        logger.warning(f"Encountered {len(all_populator_errors)} errors during graph population.")
        # Log details if needed: logger.warning(f"Population errors: {all_populator_errors}")

    return [
        (item_id, msg) for stmt_id, item_id, msg in all_populator_errors
    ]  # Return simplified list


def create_statement_dataframe(
    graph: Graph,
    config_path_or_dir: str,
    format_kwargs: Optional[dict[str, Any]] = None,
) -> Union[pd.DataFrame, dict[str, pd.DataFrame]]:
    r"""Load config(s), build structure(s), populate graph, format as DataFrame(s).

    This function orchestrates the entire process of turning statement
    configuration files into pandas DataFrames containing the calculated or
    retrieved financial data.

    It performs the following steps:
    1. Loads configuration(s) from the specified path or directory.
    2. Validates the configuration(s).
    3. Builds the internal statement structure(s).
    4. Registers the structure(s).
    5. Populates the provided `graph` with nodes based on the statement(s).
       (Assumes the graph might already contain necessary data nodes or will
       fetch them).
    6. Formats the statement data from the graph into pandas DataFrame(s).

    Args:
        graph: The core.graph.Graph instance to use and populate. This graph
            should ideally contain the necessary base data nodes (e.g.,
            actuals) before calling this function, or nodes should be capable
            of fetching their data.
        config_path_or_dir: Path to a single statement config file (e.g.,
            './configs/income_statement.yaml') or a directory containing
            multiple config files (e.g., './configs/').
        format_kwargs: Optional dictionary of keyword arguments passed directly
            to the `StatementFormatter.generate_dataframe` method. This can
            be used to control aspects like date ranges, periods, or number
            formatting. See `StatementFormatter` documentation for details.

    Returns:
        If `config_path_or_dir` points to a single file, returns a single
        pandas DataFrame representing that statement.
        If `config_path_or_dir` points to a directory, returns a dictionary
        mapping statement IDs (derived from filenames) to their corresponding
        pandas DataFrames.

    Raises:
        ConfigurationError: If loading or validating configurations fails.
        StatementError: If registering statements fails or if no valid
            statements can be processed.
        FileNotFoundError: If `config_path_or_dir` does not exist or is not a
            valid file or directory.
        FinancialModelError: Potentially other errors from graph operations
            during population or formatting.

    Example:
        >>> from fin_statement_model.core.graph import Graph
        >>> # Assume 'my_graph' is a pre-populated Graph instance
        >>> # Assume 'configs/income_stmt.yaml' defines an income statement
        >>> try:
        ...     income_df = create_statement_dataframe(
        ...         graph=my_graph,
        ...         config_path_or_dir='configs/income_stmt.yaml',
        ...         format_kwargs={'periods': ['2023Q1', '2023Q2']}
        ...     )
        ...     # In real code, use logger.debug or logger.info
        ...     logger.debug(f"Income DataFrame head:\n{income_df.head()}")
        ... except FileNotFoundError:
        ...     # Use logger.error or logger.warning
        ...     logger.error("Config file not found.")
        ... except (ConfigurationError, StatementError) as e:
        ...     # Use logger.error or logger.exception
        ...     logger.error(f"Error processing statement: {e}")

        >>> # Process all configs in a directory
        >>> try:
        ...     all_statements = create_statement_dataframe(
        ...         graph=my_graph,
        ...         config_path_or_dir='configs/'
        ...     )
        ...     balance_sheet_df = all_statements.get('balance_sheet')
        ...     if balance_sheet_df is not None:
        ...         # Use logger.info
        ...         logger.info("Balance Sheet DataFrame created.")
        ... except FileNotFoundError:
        ...     # Use logger.error or logger.warning
        ...     logger.error("Config directory not found.")
        ... except StatementError as e:
        ...     # Use logger.error or logger.exception
        ...     logger.error(f"Error processing statements: {e}")
    """
    registry = StatementRegistry()
    builder = StatementStructureBuilder()
    format_kwargs = format_kwargs or {}

    # Step 1: Load, Build, Register
    loaded_ids = _load_build_register_statements(config_path_or_dir, registry, builder)
    if not loaded_ids:
        raise StatementError(f"No valid statements could be loaded from {config_path_or_dir}")

    # Step 2: Populate Graph (handles errors internally, logs warnings)
    _populate_graph(registry, graph)

    # Step 3: Format results
    results: dict[str, pd.DataFrame] = {}
    formatting_errors = []
    for stmt_id in loaded_ids:
        statement = registry.get(stmt_id)
        if not statement:
            logger.error(
                f"Internal error: Statement '{stmt_id}' was loaded but not found in registry."
            )
            formatting_errors.append((stmt_id, "Statement not found in registry after loading"))
            continue
        try:
            formatter = StatementFormatter(statement)
            df = formatter.generate_dataframe(graph, **format_kwargs)
            results[stmt_id] = df
        except Exception as e:
            logger.exception(f"Failed to format statement '{stmt_id}'")
            formatting_errors.append((stmt_id, f"Formatting error: {e!s}"))

    if formatting_errors:
        # Decide policy: raise error, or return partial results?
        # For now, log warning and return what succeeded.
        logger.warning(f"Encountered {len(formatting_errors)} errors during formatting.")

    # Return single DF or Dict based on input type
    is_single_file = Path(config_path_or_dir).is_file()
    if is_single_file and len(results) == 1:
        return next(iter(results.values()))
    elif is_single_file and not results:
        raise StatementError(
            f"Failed to generate DataFrame for statement from file: {config_path_or_dir}"
        )
    else:
        # Return dict for directory input, or if multiple results came from single file (unexpected)
        return results


def _export_statements(
    graph: Graph,
    config_path_or_dir: str,
    output_dir: str,
    format_kwargs: Optional[dict[str, Any]],
    writer_func: callable,  # Function to call for writing (e.g., write_to_excel)
    writer_kwargs: Optional[dict[str, Any]],
    file_suffix: str,  # e.g., ".xlsx" or ".json"
) -> None:
    """Generate and export statement DataFrames using a specific writer function.

    Internal helper function that takes generated DataFrames (or generates them
    if needed via `create_statement_dataframe`) and uses the provided
    `writer_func` to save them to disk.

    Args:
        graph: The core.graph.Graph instance.
        config_path_or_dir: Path to config file or directory.
        output_dir: Directory where output files will be saved.
        format_kwargs: Optional arguments for `create_statement_dataframe`.
        writer_func: The function responsible for writing a DataFrame to a file
            (e.g., `statement_writer.write_statement_to_excel`).
        writer_kwargs: Optional arguments passed directly to the `writer_func`.
        file_suffix: The file extension to use for output files (e.g., ".xlsx").

    Raises:
        WriteError: If any errors occur during the file writing process.
        FinancialModelError: If errors occur during DataFrame generation.
        FileNotFoundError: If config path doesn't exist.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        dfs = create_statement_dataframe(graph, config_path_or_dir, format_kwargs)
    except FinancialModelError:
        logger.exception("Failed to generate statement dataframes for export:")
        raise  # Re-raise critical errors from generation step

    if not dfs:
        logger.warning(f"No DataFrames generated, nothing to export to {file_suffix} files.")
        return

    # Standardize to dictionary format
    if isinstance(dfs, pd.DataFrame):
        # Try to get a meaningful name if it was a single file
        stmt_id = (
            Path(config_path_or_dir).stem if Path(config_path_or_dir).is_file() else "statement"
        )
        dfs_dict = {stmt_id: dfs}
    else:
        dfs_dict = dfs

    export_errors = []
    for stmt_id, df in dfs_dict.items():
        # Ensure stmt_id is filename-safe (basic replacement)
        safe_stmt_id = stmt_id.replace("/", "_").replace("\\", "_")
        file_path = output_path / f"{safe_stmt_id}{file_suffix}"
        try:
            writer_func(df, str(file_path), **writer_kwargs)
            logger.info(f"Successfully exported statement '{stmt_id}' to {file_path}")
        except WriteError as e:
            logger.exception(f"Failed to write {file_suffix} file for statement '{stmt_id}':")
            export_errors.append((stmt_id, str(e)))
        except Exception as e:
            logger.exception(f"Unexpected error exporting statement '{stmt_id}' to {file_suffix}.")
            export_errors.append((stmt_id, f"Unexpected export error: {e!s}"))

    if export_errors:
        error_summary = "; ".join([f"{sid}: {err}" for sid, err in export_errors])
        raise WriteError(
            f"Encountered {len(export_errors)} errors during {file_suffix} export: {error_summary}"
        )


def export_statements_to_excel(
    graph: Graph,
    config_path_or_dir: str,
    output_dir: str,
    format_kwargs: Optional[dict[str, Any]] = None,
    writer_kwargs: Optional[dict[str, Any]] = None,
) -> None:
    """Generate statement DataFrames and export them to individual Excel files.

    Loads configurations, builds statements, populates the graph (if necessary),
    generates DataFrames for each statement, and saves each DataFrame to a
    separate `.xlsx` file in the specified `output_dir`.

    Args:
        graph: The core.graph.Graph instance containing necessary data.
        config_path_or_dir: Path to a single statement config file or a
            directory containing multiple config files.
        output_dir: The directory where the resulting Excel files will be saved.
            File names will be derived from the statement IDs (e.g.,
            'income_statement.xlsx').
        format_kwargs: Optional dictionary of arguments passed to
            `StatementFormatter.generate_dataframe` when creating the DataFrames.
        writer_kwargs: Optional dictionary of arguments passed to the underlying
            Excel writer (`io.writers.write_statement_to_excel`), such as
            `sheet_name` or engine options.

    Raises:
        ConfigurationError: If loading or validating configurations fails.
        StatementError: If processing statements fails critically.
        FileNotFoundError: If `config_path_or_dir` is not found.
        WriteError: If writing any of the Excel files fails.
        FinancialModelError: Potentially other errors from graph operations.

    Example:
        >>> from fin_statement_model.core.graph import Graph
        >>> # Assume 'my_graph' is a pre-populated Graph instance
        >>> # Assume configs exist in './statement_configs/'
        >>> try:
        ...     export_statements_to_excel(
        ...         graph=my_graph,
        ...         config_path_or_dir='./statement_configs/',
        ...         output_dir='./output_excel/',
        ...         writer_kwargs={'freeze_panes': (1, 1)} # Freeze header row/col
        ...     )
        ...     # Use logger.info
        ...     logger.info("Statements exported to ./output_excel/")
        ... except (FileNotFoundError, ConfigurationError, StatementError, WriteError) as e:
        ...     # Use logger.error or logger.exception
        ...     logger.error(f"Export failed: {e}")
    """
    _export_statements(
        graph=graph,
        config_path_or_dir=config_path_or_dir,
        output_dir=output_dir,
        format_kwargs=format_kwargs or {},
        writer_func=statement_writer.write_statement_to_excel,
        writer_kwargs=writer_kwargs or {},
        file_suffix=".xlsx",
    )


def export_statements_to_json(
    graph: Graph,
    config_path_or_dir: str,
    output_dir: str,
    format_kwargs: Optional[dict[str, Any]] = None,
    writer_kwargs: Optional[dict[str, Any]] = None,
) -> None:
    """Generate statement DataFrames and export them to individual JSON files.

    Loads configurations, builds statements, populates the graph (if necessary),
    generates DataFrames for each statement, and saves each DataFrame to a
    separate `.json` file in the specified `output_dir`.

    Args:
        graph: The core.graph.Graph instance containing necessary data.
        config_path_or_dir: Path to a single statement config file or a
            directory containing multiple config files.
        output_dir: The directory where the resulting JSON files will be saved.
            File names will be derived from the statement IDs (e.g.,
            'balance_sheet.json').
        format_kwargs: Optional dictionary of arguments passed to
            `StatementFormatter.generate_dataframe` when creating the DataFrames.
        writer_kwargs: Optional dictionary of arguments passed to the underlying
            JSON writer (`io.writers.write_statement_to_json`). Common options
            include `orient` (e.g., 'records', 'columns', 'split') and `indent`.
            Defaults to 'records' orient and indent=2 if not provided.

    Raises:
        ConfigurationError: If loading or validating configurations fails.
        StatementError: If processing statements fails critically.
        FileNotFoundError: If `config_path_or_dir` is not found.
        WriteError: If writing any of the JSON files fails.
        FinancialModelError: Potentially other errors from graph operations.

    Example:
        >>> from fin_statement_model.core.graph import Graph
        >>> # Assume 'my_graph' is a pre-populated Graph instance
        >>> # Assume configs exist in './statement_configs/'
        >>> try:
        ...     export_statements_to_json(
        ...         graph=my_graph,
        ...         config_path_or_dir='./statement_configs/',
        ...         output_dir='./output_json/',
        ...         writer_kwargs={'orient': 'split', 'indent': 4}
        ...     )
        ...     # Use logger.info
        ...     logger.info("Statements exported to ./output_json/")
        ... except (FileNotFoundError, ConfigurationError, StatementError, WriteError) as e:
        ...     # Use logger.error or logger.exception
        ...     logger.error(f"Export failed: {e}")
    """
    final_writer_kwargs = writer_kwargs or {}
    # Set JSON specific defaults if not provided
    final_writer_kwargs.setdefault("orient", "records")
    final_writer_kwargs.setdefault("indent", 2)

    _export_statements(
        graph=graph,
        config_path_or_dir=config_path_or_dir,
        output_dir=output_dir,
        format_kwargs=format_kwargs or {},
        writer_func=statement_writer.write_statement_to_json,
        writer_kwargs=final_writer_kwargs,
        file_suffix=".json",
    )


# Removed create_statement_json as DataFrame approach is used for consistency now.
# If direct dict export is needed, add a separate function.
# def create_statement_json(...):
#     ... # Logic to fetch raw data dict using formatter._fetch_data_from_graph
