"""Functions for bulk import and export of adjustments via Excel files."""

import logging
from typing import Optional, Any, cast
from pathlib import Path
from collections import defaultdict

import pandas as pd

from fin_statement_model.core.adjustments.models import (
    Adjustment,
    AdjustmentType,
    AdjustmentTag,
    DEFAULT_SCENARIO,
)
from fin_statement_model.core.graph import Graph  # Needed for Graph convenience methods
from fin_statement_model.io.exceptions import ReadError, WriteError
from fin_statement_model.io.core import FileBasedReader, handle_read_errors

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


def _parse_tags(tag_str: Optional[str]) -> set[AdjustmentTag]:
    """Parse a comma-separated tag string into a set."""
    if pd.isna(tag_str) or not isinstance(tag_str, str) or not tag_str.strip():
        return set()
    return set(tag.strip() for tag in tag_str.split(",") if tag.strip())


def _read_excel_impl(path: str | Path) -> tuple[list[Adjustment], pd.DataFrame]:
    """Read adjustments from an Excel file.

    Expects the first sheet to contain adjustment data.
    Validates required columns and attempts to parse each row into an Adjustment object.
    Rows that fail validation are collected into an error report DataFrame.

    Args:
        path: Path to the Excel file.

    Returns:
        A tuple containing:
            - list[Adjustment]: A list of successfully parsed Adjustment objects.
            - pd.DataFrame: A DataFrame containing rows that failed validation,
                          with an added 'error' column explaining the issue.

    Raises:
        ReadError: If the file cannot be read, sheet is missing, or required
                   columns are not found.
    """
    file_path = Path(path)
    logger.info(f"Reading adjustments from Excel file: {file_path}")

    try:
        # Read the first sheet by default
        df = pd.read_excel(file_path, sheet_name=0)
    except FileNotFoundError:
        raise ReadError(
            f"Adjustment Excel file not found: {file_path}", source=str(file_path)
        )
    except Exception as e:
        # Catch other potential pandas read errors (e.g., bad format, permissions)
        raise ReadError(
            f"Failed to read Excel file {file_path}: {e}",
            source=str(file_path),
            original_error=e,
        )

    # Normalize column names to lowercase for case-insensitive matching
    df.columns = [str(col).lower().strip() for col in df.columns]
    actual_cols = set(df.columns)

    # Check for required columns
    missing_req_cols = REQ_COLS - actual_cols
    if missing_req_cols:
        raise ReadError(
            f"Missing required columns in adjustment Excel file: {missing_req_cols}",
            source=str(file_path),
        )

    valid_adjustments: list[Adjustment] = []
    error_rows: list[dict[str, Any]] = []

    for index, row in df.iterrows():
        adj_data: dict[str, Any] = {}
        parse_errors: list[str] = []

        # Map columns to Adjustment fields
        for col_name, field_name in COL_TO_FIELD_MAP.items():
            if col_name in df.columns:
                value = row[col_name]
                # Handle potential NaNs from Excel
                if pd.isna(value):
                    adj_data[field_name] = None
                else:
                    # Specific type conversions / parsing
                    try:
                        if field_name == "tags":
                            adj_data[field_name] = _parse_tags(str(value))
                        elif field_name == "type":
                            adj_data[field_name] = AdjustmentType(str(value).lower())
                        elif field_name == "priority":
                            adj_data[field_name] = int(value)
                        elif field_name in {"scale", "value"}:
                            adj_data[field_name] = float(value)
                        elif field_name == "id":
                            # Allow specific UUIDs from input
                            from uuid import UUID  # Local import

                            adj_data[field_name] = UUID(str(value))
                        else:
                            # Default to string conversion for others (node_name, period, etc.)
                            adj_data[field_name] = str(value)
                    except ValueError as e:
                        parse_errors.append(
                            f"Column '{col_name}': Invalid value '{value}' ({e})"
                        )
                    except Exception as e:
                        parse_errors.append(
                            f"Column '{col_name}': Error parsing value '{value}' ({e})"
                        )
            else:
                # Optional field not present
                adj_data[field_name] = None

        # Fill defaults for optional fields if not provided/mapped
        adj_data.setdefault("scenario", DEFAULT_SCENARIO)
        adj_data.setdefault("scale", 1.0)
        adj_data.setdefault("priority", 0)
        adj_data.setdefault("type", AdjustmentType.ADDITIVE)
        adj_data.setdefault("tags", set())

        # Remove None values for fields that shouldn't be None if missing (handled by Pydantic defaults later)
        # This is mainly for fields where None might cause issues if explicitly passed to Pydantic
        # e.g., pydantic might handle default factories better if key is absent vs. key=None
        # Let's be explicit for required ones:
        if adj_data.get("node_name") is None:
            parse_errors.append("Column 'node_name': Missing value")
        if adj_data.get("period") is None:
            parse_errors.append("Column 'period': Missing value")
        if adj_data.get("value") is None:
            parse_errors.append("Column 'value': Missing value")
        if adj_data.get("reason") is None:
            parse_errors.append("Column 'reason': Missing value")

        if parse_errors:
            error_detail = "; ".join(parse_errors)
            error_row = row.to_dict()
            error_row["error"] = error_detail
            error_rows.append(error_row)
            logger.debug(f"Row {index + 2}: Validation failed - {error_detail}")
            continue

        # Attempt to create the Adjustment object (final validation)
        try:
            # Filter out keys with None values before passing to Adjustment, let Pydantic handle defaults
            final_adj_data = {k: v for k, v in adj_data.items() if v is not None}
            adjustment = Adjustment(**final_adj_data)
            valid_adjustments.append(adjustment)
        except Exception as e:
            error_detail = f"Pydantic validation failed: {e}"
            error_row = row.to_dict()
            error_row["error"] = error_detail
            error_rows.append(error_row)
            logger.debug(f"Row {index + 2}: Pydantic validation failed - {e}")

    error_report_df = pd.DataFrame(error_rows)
    if not error_report_df.empty:
        logger.warning(
            f"Completed reading adjustments from {file_path}. Found {len(valid_adjustments)} valid adjustments and {len(error_rows)} errors."
        )
    else:
        logger.info(
            f"Successfully read {len(valid_adjustments)} adjustments from {file_path} with no errors."
        )

    return valid_adjustments, error_report_df


# DataReader class for reading adjustments with standardized validation
class AdjustmentsExcelReader(FileBasedReader):
    """DataReader for reading adjustments from an Excel file with consistent validation and error handling."""

    @handle_read_errors()
    def read(  # type: ignore[override]
        self, source: str | Path, **kwargs: Any
    ) -> tuple[list[Adjustment], pd.DataFrame]:
        """Read adjustments using FileBasedReader validation."""
        path_str = str(source)
        self.validate_file_exists(path_str)
        self.validate_file_extension(path_str, (".xls", ".xlsx"))
        return _read_excel_impl(path_str)


# Public API: delegate to standardized reader
def read_excel(path: str | Path) -> tuple[list[Adjustment], pd.DataFrame]:
    """Read adjustments from an Excel file.

    Args:
        path: Path to the Excel file.

    Returns:
        Tuple of valid Adjustment list and error report DataFrame.
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
) -> pd.DataFrame:
    """Reads adjustments from Excel and adds them to the graph.

    Args:
        graph: The Graph instance to add adjustments to.
        path: Path to the Excel file.
        replace: If True, clear existing adjustments in the manager before adding new ones.

    Returns:
        pd.DataFrame: The error report DataFrame from `read_excel`.
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

    return error_report_df


def export_adjustments_to_excel(graph: Graph, path: str | Path) -> None:
    """Exports all adjustments from the graph to an Excel file.

    Args:
        graph: The Graph instance containing adjustments.
        path: Path for the output Excel file.
    """
    logger.info(f"Exporting all adjustments from graph to Excel ({path}).")
    all_adjustments = graph.list_all_adjustments()
    write_excel(all_adjustments, path)


# Add convenience methods to Graph class directly?
# This uses module patching which can sometimes be debated, but keeps the Graph API clean.
# Alternatively, users would call fin_statement_model.io.adjustments_excel.load_adjustments_from_excel(graph, path)
setattr(Graph, "load_adjustments_from_excel", load_adjustments_from_excel)
setattr(Graph, "export_adjustments_to_excel", export_adjustments_to_excel)
