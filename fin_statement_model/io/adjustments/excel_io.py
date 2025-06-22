"""Functions for bulk import and export of adjustments via Excel files."""

import logging
from typing import Any, cast, Iterable
from pathlib import Path
from collections import defaultdict

import pandas as pd
from pydantic import ValidationError

from fin_statement_model.core.adjustments.models import (
    Adjustment,
    AdjustmentType,
)
from fin_statement_model.core.graph import Graph  # Needed for Graph convenience methods
from fin_statement_model.io.exceptions import ReadError, WriteError
from fin_statement_model.io.core.mixins.error_handlers import handle_read_errors
from fin_statement_model.io.adjustments.row_models import AdjustmentRowModel

logger = logging.getLogger(__name__)

# Define expected column names (case-insensitive matching during read)
# Required columns per spec:
REQ_COLS = {"node_name", "period", "value", "reason"}
# Optional columns per spec:
OPT_COLS = {
    "type",
    "tags",
    "scale",
    "scenario",
    "start_period",
    "end_period",
    "priority",
    "user",
    "id",
}
ALL_COLS = REQ_COLS.union(OPT_COLS)

# Map DataFrame column names (lowercase) to Adjustment model fields
COL_TO_FIELD_MAP = {
    "node_name": "node_name",
    "period": "period",
    "value": "value",
    "reason": "reason",
    "type": "type",
    "tags": "tags",
    "scale": "scale",
    "scenario": "scenario",
    "start_period": "start_period",
    "end_period": "end_period",
    "priority": "priority",
    "user": "user",
    "id": "id",
    # Note: timestamp is not expected in input file, generated on creation
}


def _validate_required_columns(columns: Iterable[str]) -> None:
    missing = REQ_COLS - set(columns)
    if missing:
        raise ReadError(
            f"Missing required columns in adjustment Excel file: {missing}",
            source=str(columns),
        )


def _build_error_row(
    raw: dict[str, Any], ve: ValidationError, idx: int
) -> dict[str, Any]:
    error_detail = "; ".join(f"{err['loc'][0]}: {err['msg']}" for err in ve.errors())
    row = {**raw, "error": error_detail}
    logger.debug(f"Row {idx}: Validation failed - {error_detail}")
    return row


# -----------------------------------------------------------------------------
# Minimal file-validation helper (keeps AdjustmentsExcelReader independent from
# Graph-oriented FileBasedReader/DataReader hierarchy).
# -----------------------------------------------------------------------------


class _FileValidationMixin:
    """Provide filesystem helpers without imposing Graph-return contract."""

    file_extensions: tuple[str, ...] | None = None

    def validate_file_exists(self, path: str) -> None:  # noqa: D401
        import os

        if not os.path.exists(path):
            raise ReadError(
                f"File not found: {path}",
                source=path,
                reader_type=self.__class__.__name__,
            )

    def validate_file_extension(
        self, path: str, valid_extensions: tuple[str, ...] | None = None
    ) -> None:  # noqa: D401
        exts = valid_extensions or self.file_extensions
        if not exts:
            return
        if not path.lower().endswith(exts):
            import os as _os

            raise ReadError(
                f"Invalid file extension. Expected one of {exts}, got '{_os.path.splitext(path)[1]}'",
                source=path,
                reader_type=self.__class__.__name__,
            )


# DataReader class for reading adjustments with standardized validation
class AdjustmentsExcelReader(_FileValidationMixin):
    """DataReader for reading adjustments from an Excel file.

    Combines basic *file existence/extension* checks provided by
    :class:`FileBasedReader` with the row-level validation logic previously
    implemented in the private ``_read_excel_impl`` helper.  Removing an extra
    indirection both simplifies stack traces and reduces cognitive load for
    maintainers.
    """

    file_extensions = (".xls", ".xlsx")

    @handle_read_errors()
    def read(
        self, source: str | Path, **_kw: Any
    ) -> tuple[list[Adjustment], pd.DataFrame]:
        """Return list of valid adjustments + error-report DataFrame."""

        path_str = str(source)

        # Basic file checks ---------------------------------------------------
        self.validate_file_exists(path_str)
        self.validate_file_extension(path_str)

        file_path = Path(path_str)
        logger.info("Reading adjustments from Excel file: %s", file_path)

        # ------------------------------------------------------------------
        # Load sheet into DataFrame
        # ------------------------------------------------------------------
        try:
            df = pd.read_excel(file_path, sheet_name=0)
        except FileNotFoundError:
            raise ReadError(
                f"Adjustment Excel file not found: {file_path}", source=str(file_path)
            )
        except Exception as e:  # noqa: BLE001
            raise ReadError(
                f"Failed to read Excel file {file_path}: {e}",
                source=str(file_path),
                original_error=e,
            ) from e

        # ------------------------------------------------------------------
        # Normalise + validate columns
        # ------------------------------------------------------------------
        df.columns = [str(col).lower().strip() for col in df.columns]
        _validate_required_columns(df.columns)

        records = df.to_dict(orient="records")
        valid_adjustments: list[Adjustment] = []
        error_rows: list[dict[str, Any]] = []

        for idx, raw in enumerate(records, start=2):  # Account for header row
            try:
                row_model = AdjustmentRowModel(**raw)
                valid_adjustments.append(row_model.to_adjustment())
            except ValidationError as ve:
                error_rows.append(_build_error_row(raw, ve, idx))

        error_report_df = pd.DataFrame(error_rows)
        if not error_report_df.empty:
            logger.warning(
                "Completed reading adjustments from %s. Found %s valid adjustments and %s errors.",
                file_path,
                len(valid_adjustments),
                len(error_rows),
            )
        else:
            logger.info(
                "Successfully read %s adjustments from %s with no errors.",
                len(valid_adjustments),
                file_path,
            )

        return valid_adjustments, error_report_df


# Public API: delegate to standardized reader
def read_excel(path: str | Path) -> tuple[list[Adjustment], pd.DataFrame]:
    """Read adjustments from an Excel file.

    Args:
        path: Path to the Excel file.

    Returns:
        tuple[list[Adjustment], pd.DataFrame]:
            1. List of successfully parsed adjustments (added to the graph).
            2. Error report DataFrame (empty if no row-level errors).
    """
    return AdjustmentsExcelReader().read(path)


def write_excel(adjustments: list[Adjustment], path: str | Path) -> None:
    """Write a list of adjustments to an Excel file.

    Writes adjustments to separate sheets based on their scenario.
    The columns will match the optional fields defined for reading.

    Args:
        adjustments: A list of Adjustment objects to write.
        path: Path for the output Excel file.

    Raises:
        WriteError: If writing to the file fails.
    """
    file_path = Path(path)
    logger.info(f"Writing {len(adjustments)} adjustments to Excel file: {file_path}")

    # Group adjustments by scenario
    grouped_by_scenario: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for adj in adjustments:
        # Use model_dump for serialization, exclude fields we don't usually export
        adj_dict = adj.model_dump(exclude={"timestamp"})  # Exclude timestamp by default
        # Convert complex types to simple types for Excel
        adj_dict["id"] = str(adj_dict.get("id"))
        raw_type = adj_dict.get("type")
        # Cast to AdjustmentType to access .value safely if present
        adj_dict["type"] = cast(AdjustmentType, raw_type).value if raw_type else None
        adj_dict["tags"] = ",".join(sorted(adj_dict.get("tags", set())))
        grouped_by_scenario[adj.scenario].append(adj_dict)

    if not grouped_by_scenario:
        logger.warning("No adjustments provided to write_excel. Creating empty file.")
        # Create an empty file or handle as desired
        try:
            pd.DataFrame().to_excel(file_path, index=False)
        except Exception as e:
            raise WriteError(
                f"Failed to write empty Excel file {file_path}: {e}",
                target=str(file_path),
                original_error=e,
            )
        return

    try:
        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            for scenario, scenario_adjustments in grouped_by_scenario.items():
                df = pd.DataFrame(scenario_adjustments)
                # Reorder columns for consistency
                cols_ordered = [c for c in COL_TO_FIELD_MAP if c in df.columns]
                cols_ordered += [c for c in df.columns if c not in cols_ordered]
                df = df[cols_ordered]
                # Sheet names must be valid
                safe_scenario_name = (
                    scenario.replace(":", "-").replace("/", "-").replace("\\", "-")[:31]
                )
                df.to_excel(writer, sheet_name=safe_scenario_name, index=False)
        logger.info(f"Successfully wrote adjustments to {file_path}")
    except Exception as e:
        logger.error(
            f"Failed to write adjustments to Excel file {file_path}: {e}", exc_info=True
        )
        raise WriteError(
            f"Failed to write adjustments to Excel: {e}",
            target=str(file_path),
            original_error=e,
        )


# --- Graph Convenience Methods ---


def load_adjustments_from_excel(
    graph: Graph, path: str | Path, replace: bool = False
) -> tuple[list[Adjustment], pd.DataFrame]:
    """Reads adjustments from Excel and adds them to the graph.

    Args:
        graph: The Graph instance to add adjustments to.
        path: Path to the Excel file.
        replace: If True, clear existing adjustments in the manager before adding new ones.

    Returns:
        tuple[list[Adjustment], pd.DataFrame]: The error report DataFrame from `read_excel`.
                   Empty if no errors occurred.
    """
    logger.info(
        f"Loading adjustments from Excel ({path}) into graph. Replace={replace}"
    )
    valid_adjustments, error_report_df = read_excel(path)

    if replace:
        logger.debug("Clearing existing adjustments before loading.")
        graph.adjustment_manager.clear_all()

    added_count = 0
    for adj in valid_adjustments:
        try:
            graph.adjustment_manager.add_adjustment(adj)
            added_count += 1
        except Exception as e:
            logger.error(
                f"Failed to add valid adjustment {adj.id} to graph: {e}", exc_info=True
            )
            # Optionally add this failure to the error report?
            error_row = adj.model_dump(mode="json")
            error_row["error"] = f"Failed to add to graph: {e}"
            # Need to handle DataFrame append carefully if modifying during iteration
            # Simplest is to report read errors, log add errors.

    logger.info(f"Added {added_count} adjustments to the graph from {path}.")
    if not error_report_df.empty:
        logger.warning(
            f"Encountered {len(error_report_df)} errors during Excel read process."
        )

    return valid_adjustments, error_report_df


def export_adjustments_to_excel(graph: Graph, path: str | Path) -> None:
    """Exports all adjustments from the graph to an Excel file.

    Args:
        graph: The Graph instance containing adjustments.
        path: Path for the output Excel file.
    """
    logger.info(f"Exporting all adjustments from graph to Excel ({path}).")
    all_adjustments = graph.list_all_adjustments()
    write_excel(all_adjustments, path)


# Note: These helpers were previously monkey-patched onto Graph for convenience.  The
# project now avoids such runtime patching; call the functions explicitly, e.g.::
#
#     from fin_statement_model.io.adjustments.excel_io import load_adjustments_from_excel
#     load_adjustments_from_excel(graph, "adjustments.xlsx", replace=True)
