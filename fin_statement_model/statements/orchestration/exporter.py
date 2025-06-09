"""Statement export functionality.

This module handles exporting financial statements to various file formats
including Excel and JSON. It provides both internal helper functions and
public API functions for exporting statements.
"""

import logging
from pathlib import Path
from typing import Any, Callable, Optional

import pandas as pd

from fin_statement_model.core.errors import FinancialModelError
from fin_statement_model.core.graph import Graph
from fin_statement_model.io import write_statement_to_excel, write_statement_to_json
from fin_statement_model.io.exceptions import WriteError

logger = logging.getLogger(__name__)

__all__ = [
    "export_statements",
    "export_statements_to_excel",
    "export_statements_to_json",
]


def export_statements(
    graph: Graph,
    config_path_or_dir: str,
    output_dir: str,
    format_kwargs: dict[str, Any],
    writer_func: Callable[..., None],
    writer_kwargs: dict[str, Any],
    file_suffix: str,
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
            (e.g., `write_statement_to_excel`).
        writer_kwargs: Optional arguments passed directly to the `writer_func`.
        file_suffix: The file extension to use for output files (e.g., ".xlsx").

    Raises:
        WriteError: If any errors occur during the file writing process.
        FinancialModelError: If errors occur during DataFrame generation.
        FileNotFoundError: If config path doesn't exist.
    """
    # Import here to avoid circular dependency
    from fin_statement_model.statements.orchestration.orchestrator import (
        create_statement_dataframe,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Load statement configuration(s) into memory if a path was provided
    def _parse_config_file(file_path: Path) -> dict[str, Any] | None:
        """Parse a YAML or JSON statement configuration file into a dictionary.

        Returns None if the file cannot be parsed or the root element is not a mapping.
        """
        # Security: Check file size to prevent memory exhaustion
        max_size = 10 * 1024 * 1024  # 10MB limit
        if file_path.stat().st_size > max_size:
            logger.warning("Config file '%s' exceeds size limit (%d bytes) - skipping", file_path, max_size)
            return None

        try:
            if file_path.suffix.lower() == ".json":
                import json
                data = json.loads(file_path.read_text(encoding="utf-8"))
            else:
                # Fallback to YAML for .yaml / .yml extensions (PyYAML is a dependency)
                import yaml
                data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                logger.warning(
                    "Statement config '%s' is not a mapping at the root level – skipping", file_path
                )
                return None
            return data  # type: ignore[return-value]
        except (json.JSONDecodeError, yaml.YAMLError) as exc:
            logger.warning("Failed to parse statement config file '%s': %s", file_path, exc)
            return None
        except Exception as exc:
            logger.exception(
                "Failed to parse statement config file '%s': %s", file_path, exc
            )
            return None

    # Determine raw_configs based on the provided argument type
    raw_configs: dict[str, dict[str, Any]]
    if isinstance(config_path_or_dir, (str, Path)):
        cfg_path = Path(config_path_or_dir)
        if not cfg_path.exists():
            raise FileNotFoundError(f"Config path '{cfg_path}' does not exist.")
        if cfg_path.is_dir():
            raw_configs = {}
            for item in cfg_path.iterdir():
                if item.is_file() and item.suffix.lower() in {".yaml", ".yml", ".json"}:
                    parsed_cfg = _parse_config_file(item)
                    if parsed_cfg:
                        stmt_id = str(parsed_cfg.get("id", item.stem))
                        raw_configs[stmt_id] = parsed_cfg
            if not raw_configs:
                raise FileNotFoundError(
                    f"No valid statement configuration files found in directory '{cfg_path}'."
                )
        else:
            parsed_cfg = _parse_config_file(cfg_path)
            if parsed_cfg is None:
                raise FileNotFoundError(
                    f"Failed to parse statement configuration file '{cfg_path}'."
                )
            stmt_id = str(parsed_cfg.get("id", cfg_path.stem))
            raw_configs = {stmt_id: parsed_cfg}
    elif isinstance(config_path_or_dir, dict):
        # Already provided a mapping of configs
        raw_configs = config_path_or_dir  # type: ignore[assignment]
    else:
        raise TypeError(
            "config_path_or_dir must be a path to a config file/directory or a mapping of configs."
        )

    try:
        dfs = create_statement_dataframe(graph, raw_configs, format_kwargs)
    except FinancialModelError:
        logger.exception("Failed to generate statement dataframes for export:")
        raise  # Re-raise critical errors from generation step

    if not dfs:
        logger.warning(
            f"No DataFrames generated, nothing to export to {file_suffix} files."
        )
        return

    # Standardize to dictionary format
    if isinstance(dfs, pd.DataFrame):
        # Derive a sensible statement ID when only a single DataFrame is returned
        if isinstance(config_path_or_dir, (str, Path)):
            # Use file/dir name if a path was provided
            path_obj = Path(config_path_or_dir)
            stmt_id = path_obj.stem if path_obj.is_file() else "statement"
        else:
            # Fallback to the first key in the raw_configs mapping
            stmt_id = next(iter(raw_configs.keys()))
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
            logger.exception(
                f"Failed to write {file_suffix} file for statement '{stmt_id}':"
            )
            export_errors.append((stmt_id, str(e)))
        except Exception as e:
            logger.exception(
                f"Unexpected error exporting statement '{stmt_id}' to {file_suffix}."
            )
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
            Excel writer (`write_statement_to_excel`), such as
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
    export_statements(
        graph=graph,
        config_path_or_dir=config_path_or_dir,
        output_dir=output_dir,
        format_kwargs=format_kwargs or {},
        writer_func=write_statement_to_excel,
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
            JSON writer (`write_statement_to_json`). Common options
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

    export_statements(
        graph=graph,
        config_path_or_dir=config_path_or_dir,
        output_dir=output_dir,
        format_kwargs=format_kwargs or {},
        writer_func=write_statement_to_json,
        writer_kwargs=final_writer_kwargs,
        file_suffix=".json",
    )
