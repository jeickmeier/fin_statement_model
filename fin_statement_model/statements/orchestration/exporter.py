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
from fin_statement_model.statements.orchestration.orchestrator import (
    create_statement_dataframe,
)

logger = logging.getLogger(__name__)

__all__ = [
    "export_statements",
    "export_statements_to_excel",
    "export_statements_to_json",
]


def export_statements(
    dfs: dict[str, pd.DataFrame],
    output_dir: str,
    writer_func: Callable[..., None],
    writer_kwargs: dict[str, Any],
    file_suffix: str,
) -> None:
    """Export pre-generated statement DataFrames using the provided writer.

    This function is intentionally *dumb*: it assumes the heavy-lifting has
    already been done by :pyfunc:`create_statement_dataframe` and focuses solely
    on persisting the resulting pandas objects to disk.

    Args:
        dfs: A mapping of ``statement_id`` to pandas ``DataFrame`` instances
            returned by :pyfunc:`create_statement_dataframe`.
        output_dir: Target directory where the files will be written. The
            directory (and any missing parents) is created if it does not yet
            exist.
        writer_func: Concrete low-level writer (e.g.
            :pyfunc:`write_statement_to_excel`). Must accept the dataframe as
            first argument and the destination path as second argument.
        writer_kwargs: Arbitrary keyword arguments forwarded verbatim to
            *writer_func*.
        file_suffix: Extension used for the generated files (e.g. ``".xlsx"``).

    Raises:
        TypeError: If *dfs* is not a mapping of ``str -> DataFrame``.
        WriteError: Propagated if the underlying *writer_func* fails for any
            individual statement.
    """

    if not isinstance(dfs, dict):
        raise TypeError(
            "'dfs' must be a mapping of statement_id to pandas DataFrame. "
            "Call 'create_statement_dataframe' first and pass the result here."
        )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if not dfs:
        logger.warning(
            "Received an empty mapping of DataFrames – nothing to export.")
        return

    export_errors: list[tuple[str, str]] = []

    for stmt_id, df in dfs.items():
        # Ensure stmt_id is filename-safe (replace path separators)
        safe_stmt_id = stmt_id.replace("/", "_").replace("\\", "_")
        file_path = output_path / f"{safe_stmt_id}{file_suffix}"

        try:
            writer_func(df, str(file_path), **writer_kwargs)
            logger.info(
                "Successfully exported statement '%s' to %s", stmt_id, file_path
            )
        except WriteError as e:
            logger.exception(
                "Failed to write %s file for statement '%s'", file_suffix, stmt_id
            )
            export_errors.append((stmt_id, str(e)))
        except Exception as e:  # noqa: BLE001 – re-wrap unknown exceptions
            logger.exception(
                "Unexpected error exporting statement '%s' to %s", stmt_id, file_path
            )
            export_errors.append((stmt_id, f"Unexpected export error: {e!s}"))

    if export_errors:
        error_summary = "; ".join(f"{sid}: {err}" for sid, err in export_errors)
        raise WriteError(
            f"Encountered {len(export_errors)} errors during {file_suffix} export: "
            f"{error_summary}"
        )


def export_statements_to_excel(
    graph: Graph,
    raw_configs: dict[str, dict[str, Any]],
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
        raw_configs: Mapping of statement IDs to configuration dictionaries.
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
        TypeError: If `raw_configs` is not a valid mapping.
        WriteError: If writing any of the Excel files fails.
        FinancialModelError: Potentially other errors from graph operations.

    Example:
        >>> from fin_statement_model.core.graph import Graph
        >>> # Assume 'my_graph' is a pre-populated Graph instance
        >>> # Assume configs exist in './statement_configs/'
        >>> try:
        ...     export_statements_to_excel(
        ...         graph=my_graph,
        ...         raw_configs=my_configs,
        ...         output_dir='./output_excel/',
        ...         writer_kwargs={'freeze_panes': (1, 1)} # Freeze header row/col
        ...     )
        ...     # Use logger.info
        ...     logger.info("Statements exported to ./output_excel/")
        ... except (FileNotFoundError, ConfigurationError, StatementError, WriteError) as e:
        ...     # Use logger.error or logger.exception
        ...     logger.error(f"Export failed: {e}")
    """
    try:
        dfs = create_statement_dataframe(graph, raw_configs, format_kwargs or {})
    except FinancialModelError:
        logger.exception("Failed to generate statement DataFrames for Excel export:")
        raise

    export_statements(
        dfs=dfs,
        output_dir=output_dir,
        writer_func=write_statement_to_excel,
        writer_kwargs=writer_kwargs or {},
        file_suffix=".xlsx",
    )


def export_statements_to_json(
    graph: Graph,
    raw_configs: dict[str, dict[str, Any]],
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
        raw_configs: Mapping of statement IDs to configuration dictionaries.
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
        TypeError: If `raw_configs` is not a valid mapping.
        WriteError: If writing any of the JSON files fails.
        FinancialModelError: Potentially other errors from graph operations.

    Example:
        >>> from fin_statement_model.core.graph import Graph
        >>> # Assume 'my_graph' is a pre-populated Graph instance
        >>> # Assume configs exist in './statement_configs/'
        >>> try:
        ...     export_statements_to_json(
        ...         graph=my_graph,
        ...         raw_configs=my_configs,
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

    try:
        dfs = create_statement_dataframe(graph, raw_configs, format_kwargs or {})
    except FinancialModelError:
        logger.exception("Failed to generate statement DataFrames for JSON export:")
        raise

    export_statements(
        dfs=dfs,
        output_dir=output_dir,
        writer_func=write_statement_to_json,
        writer_kwargs=final_writer_kwargs,
        file_suffix=".json",
    )
