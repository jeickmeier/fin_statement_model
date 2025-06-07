"""Main orchestration for statement processing.

This module coordinates the overall workflow of loading statements, populating
graphs, and generating DataFrames. It provides the main public API function
for creating statement DataFrames.
"""

import logging
from pathlib import Path
from typing import Any, Optional, Union

import pandas as pd

from fin_statement_model.core.errors import StatementError
from fin_statement_model.core.graph import Graph

from fin_statement_model.statements.structure.builder import StatementStructureBuilder
from fin_statement_model.statements.formatting.formatter import StatementFormatter
from fin_statement_model.statements.orchestration.loader import (
    load_build_register_statements,
)
from fin_statement_model.statements.population.populator import (
    populate_graph_from_statement,
)
from fin_statement_model.statements.registry import StatementRegistry

logger = logging.getLogger(__name__)

__all__ = ["create_statement_dataframe", "populate_graph"]


def populate_graph(registry: StatementRegistry, graph: Graph) -> list[tuple[str, str]]:
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
        logger.warning(
            f"Encountered {len(all_populator_errors)} errors during graph population."
        )
        # Log details if needed: logger.warning(f"Population errors: {all_populator_errors}")

    return [
        (item_id, msg) for stmt_id, item_id, msg in all_populator_errors
    ]  # Return simplified list


def create_statement_dataframe(
    graph: Graph,
    config_path_or_dir: str,
    format_kwargs: Optional[dict[str, Any]] = None,
    enable_node_validation: bool = False,
    node_validation_strict: bool = False,
) -> Union[pd.DataFrame, dict[str, pd.DataFrame]]:
    r"""Load config(s), build structure(s), populate graph, format as DataFrame(s).

    This function orchestrates the entire process of turning statement
    configuration files into pandas DataFrames containing the calculated or
    retrieved financial data.

    It performs the following steps:
    1. Loads configuration(s) from the specified path or directory.
    2. Validates the configuration(s) with optional node ID validation.
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
        enable_node_validation: If True, validates node IDs using UnifiedNodeValidator
            during config parsing and building. Enforces naming conventions early.
        node_validation_strict: If True, treats node validation failures as errors
            instead of warnings. Only applies when enable_node_validation is True.

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
        ...         format_kwargs={'periods': ['2023Q1', '2023Q2']},
        ...         enable_node_validation=True,
        ...         node_validation_strict=True
        ...     )
        ...     # In real code, use logger.debug or logger.info
        ...     logger.debug(f"Income DataFrame head:\n{income_df.head()}")
        ... except FileNotFoundError:
        ...     # Use logger.error or logger.warning
        ...     logger.error("Config file not found.")
        ... except (ConfigurationError, StatementError) as e:
        ...     # Use logger.error or logger.exception
        ...     logger.error(f"Error processing statement: {e}")

        >>> # Process all configs in a directory with node validation
        >>> try:
        ...     all_statements = create_statement_dataframe(
        ...         graph=my_graph,
        ...         config_path_or_dir='configs/',
        ...         enable_node_validation=True,
        ...         node_validation_strict=False  # Warnings only
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
    builder = StatementStructureBuilder(
        enable_node_validation=enable_node_validation,
        node_validation_strict=node_validation_strict,
    )
    format_kwargs = format_kwargs or {}

    # Step 1: Load, Build, Register with node validation
    loaded_ids = load_build_register_statements(
        config_path_or_dir,
        registry,
        builder,
        enable_node_validation=enable_node_validation,
        node_validation_strict=node_validation_strict,
    )
    if not loaded_ids:
        raise StatementError(
            f"No valid statements could be loaded from {config_path_or_dir}"
        )

    # Step 2: Populate Graph (handles errors internally, logs warnings)
    populate_graph(registry, graph)

    # Step 3: Format results
    results: dict[str, pd.DataFrame] = {}
    formatting_errors = []
    for stmt_id in loaded_ids:
        statement = registry.get(stmt_id)
        if not statement:
            logger.error(
                f"Internal error: Statement '{stmt_id}' was loaded but not found in registry."
            )
            formatting_errors.append(
                (stmt_id, "Statement not found in registry after loading")
            )
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
        logger.warning(
            f"Encountered {len(formatting_errors)} errors during formatting."
        )

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
