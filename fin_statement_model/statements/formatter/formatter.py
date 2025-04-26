"""Formatter for financial statements.

This module provides functionality for formatting financial statements
for display or reporting, including applying formatting rules, adding subtotals,
and applying sign conventions.
"""

import pandas as pd
import numpy as np # Added numpy for NaN handling
from typing import Optional, Any, Dict, List, Union # Updated imports
from pandas.api.types import is_numeric_dtype
import logging

from fin_statement_model.statements.structure import StatementStructure
from fin_statement_model.statements.structure import (
    Section,
    LineItem, # Added LineItem
    CalculatedLineItem,
    SubtotalLineItem,
    StatementItem,
)

# Configure logging
logger = logging.getLogger(__name__)


class StatementFormatter:
    """Formats financial statements for display or reporting.

    This class provides methods to transform raw financial data into
    formatted financial statements with proper headers, indentation,
    subtotals, and sign conventions.
    """

    def __init__(self, statement: StatementStructure):
        """Initialize a statement formatter.

        Args:
            statement: The statement structure to format
        """
        self.statement = statement
        self.config = {}
        self.default_formats = {
            "precision": 2,
            "use_thousands_separator": True,
            "show_zero_values": True,
            "show_negative_sign": True,
            "indent_character": "  ",
            "subtotal_style": "bold",
            "total_style": "bold",
            "header_style": "bold",
        }

    def generate_dataframe(
        self,
        data: Dict[str, Dict[str, float]], # Use Dict
        apply_sign_convention: bool = True,
        include_empty_items: bool = False,
        number_format: Optional[str] = None,
        include_metadata_cols: bool = False, # Option to include metadata
    ) -> pd.DataFrame:
        """Generate a formatted DataFrame of the statement including subtotals.

        Combines the statement structure with period data, calculating subtotals
        across multiple periods.

        Args:
            data: Mapping of node IDs to period-value dicts.
            apply_sign_convention: Whether to apply sign conventions after calculation.
            include_empty_items: Whether to include items with no data rows.
            number_format: Optional Python format string for numbers (e.g., ',.2f').
            include_metadata_cols: If True, includes hidden metadata columns
                                   (like sign_convention, node_id) in the output.

        Returns:
            pd.DataFrame: Formatted statement DataFrame with subtotals.
        """
        rows: List[Dict[str, Any]] = [] # Use List
        # Determine all periods present in the data, sorted
        all_periods = sorted(list(set(p for node_data in data.values() for p in node_data))) if data else []

        # --- Recursive Helper Function --- #
        def _process_structure_recursive(
            items_or_sections: List[Union[Section, StatementItem]],
            current_depth: int,
            rows_list: List[Dict[str, Any]],
            all_data: Dict[str, Dict[str, float]],
            periods: List[str],
        ) -> None:
            """Recursively processes structure, calculates, and appends rows."""
            for item in items_or_sections:
                # --- Handle Sections --- #
                if isinstance(item, Section):
                    # Append section header row (optional, decide if needed)
                    # section_header_row = {
                    #     "Line Item": "  " * current_depth + item.name,
                    #     "ID": item.id,
                    #     **{p: np.nan for p in periods}, # Use NaN for headers
                    #     "line_type": "section_header",
                    #     # ... other metadata if needed ...
                    # }
                    # rows_list.append(section_header_row)

                    # Recurse into the section's items
                    _process_structure_recursive(item.items, current_depth + 1, rows_list, all_data, periods)

                    # After processing items, add the section's subtotal if it exists
                    if hasattr(item, 'subtotal') and item.subtotal:
                        self._calculate_and_append_subtotal(
                            item.subtotal, all_data, periods, rows_list, current_depth + 1
                        )
                # --- Handle Standalone Subtotals --- #
                elif isinstance(item, SubtotalLineItem):
                     # This handles subtotals defined directly within items list
                     self._calculate_and_append_subtotal(
                         item, all_data, periods, rows_list, current_depth
                     )
                # --- Handle Line Items (Basic & Calculated) --- #
                elif isinstance(item, (LineItem, CalculatedLineItem)):
                    node_id = getattr(item, "node_id", item.id) # Calculated uses item.id as node_id
                    item_data = all_data.get(node_id, {})
                    row_values = {period: item_data.get(period, np.nan) for period in periods} # Use NaN

                    # Include row only if requested or if it has any non-NaN data
                    if include_empty_items or any(pd.notna(v) for v in row_values.values()):
                        row = {
                            "Line Item": "  " * current_depth + item.name,
                            "ID": item.id,
                            **row_values,
                            # Metadata
                            "line_type": self._get_item_type(item),
                            "node_id": node_id,
                            "sign_convention": getattr(item, "sign_convention", 1),
                            "is_subtotal": isinstance(item, SubtotalLineItem),
                            "is_calculated": isinstance(item, CalculatedLineItem),
                        }
                        rows_list.append(row)
                # --- End Item Type Handling ---
            # --- End Loop --- #
        # --- End Helper Function --- #

        # Start the recursive processing with top-level sections
        _process_structure_recursive(self.statement.sections, 0, rows, data, all_periods)

        # --- DataFrame Creation and Final Formatting --- #
        if not rows:
            # Return empty DataFrame with correct columns if no rows generated
            return pd.DataFrame(columns=["Line Item", "ID", *all_periods])

        df = pd.DataFrame(rows)

        # Define columns: standard first, then periods, then metadata (conditionally)
        base_cols = ["Line Item", "ID"]
        metadata_cols = ["line_type", "node_id", "sign_convention", "is_subtotal", "is_calculated"]
        final_cols = base_cols + all_periods
        if include_metadata_cols:
             final_cols += metadata_cols

        # Ensure all expected columns exist, add if missing (e.g., empty data case)
        for col in final_cols:
             if col not in df.columns:
                 df[col] = np.nan if col in all_periods else ("" if col == "Line Item" else None)

        # Reorder columns
        df = df[final_cols]

        # Apply sign convention AFTER all raw values (including subtotals) are in place
        if apply_sign_convention:
            df = self._apply_sign_convention_to_data(df, all_periods)

        # Format numbers as the final step
        df = self._format_numbers(df, number_format, period_columns=all_periods)

        return df

    def _get_item_type(self, item: StatementItem) -> str:
        """Get the type of a statement item.

        Args:
            item: Statement item to get type for

        Returns:
            str: Item type identifier
        """
        if isinstance(item, Section):
            return "section"
        elif isinstance(item, SubtotalLineItem):
            return "subtotal"
        elif isinstance(item, CalculatedLineItem):
            return "calculated"
        else:
            return "item"

    def _apply_sign_convention_to_data(self, df: pd.DataFrame, period_columns: list[str]) -> pd.DataFrame:
        """Apply sign conventions to the statement values across periods."""
        result = df.copy()
        if "sign_convention" in result.columns:
            for col in period_columns:
                if col in result.columns and is_numeric_dtype(result[col]):
                    mask = result[col].notna()
                    # Ensure sign_convention is treated as numeric if needed
                    sign_col = pd.to_numeric(result.loc[mask, "sign_convention"], errors="coerce").fillna(1)
                    result.loc[mask, col] = (
                        result.loc[mask, col] * sign_col
                    )
        return result

    def _calculate_and_append_subtotal(
        self,
        subtotal_item: SubtotalLineItem,
        all_data: Dict[str, Dict[str, float]],
        periods: List[str],
        rows_list: List[Dict[str, Any]],
        depth: int,
    ) -> None:
        """Calculate subtotal values across periods and append the row."""
        subtotal_values: Dict[str, float] = {}

        # item_ids_to_sum = subtotal_item.item_ids # Use item_ids property
        # OR use input_ids if calculation spec is preferred:
        item_ids_to_sum = subtotal_item.input_ids # From CalculatedLineItem base

        if not item_ids_to_sum:
             logger.warning(f"Subtotal item '{subtotal_item.id}' has no item IDs to sum.")
             return

        for period in periods:
            period_sum = 0.0
            sum_contributors = 0
            for item_id in item_ids_to_sum:
                # Default to NaN if item or period data is missing
                value = all_data.get(item_id, {}).get(period, np.nan)
                if pd.notna(value):
                     period_sum += value
                     sum_contributors += 1

            # Store sum only if at least one contributor was found, otherwise NaN
            subtotal_values[period] = period_sum if sum_contributors > 0 else np.nan

        # Construct the subtotal row
        subtotal_row = {
            "Line Item": "  " * depth + subtotal_item.name,
            "ID": subtotal_item.id,
            **subtotal_values,
            # Metadata
            "line_type": "subtotal",
            "node_id": subtotal_item.id, # Subtotal acts as its own node
            "sign_convention": subtotal_item.sign_convention,
            "is_subtotal": True,
            "is_calculated": True,
        }
        rows_list.append(subtotal_row)
        logger.debug(f"Appended subtotal row for ID: {subtotal_item.id}")

    def _format_numbers(
        self, df: pd.DataFrame, number_format: Optional[str] = None, period_columns: Optional[list[str]] = None
    ) -> pd.DataFrame:
        """Format numeric values in the statement.

        Args:
            df: DataFrame to format numbers in
            number_format: Optional format string
            period_columns: List of columns containing period data to format.
                            If None, attempts to format all numeric columns
                            except metadata/indicators.

        Returns:
            pd.DataFrame: DataFrame with formatted numbers
        """
        result = df.copy()

        if period_columns:
            numeric_cols = [col for col in period_columns if col in result.columns and is_numeric_dtype(result[col])]
        else:
             # Original logic if period_columns not specified
            numeric_cols = [
                col
                for col in result.columns
                if is_numeric_dtype(result[col])
                and col not in ("sign_convention", "depth", "ID") # Added ID
                and not col.startswith("meta_")
                and col != "Line Item" # Ensure Line Item name is not formatted
            ]

        # Format to specified precision
        precision = self.config.get("precision", self.default_formats["precision"])

        if number_format:
            # Use provided format string
            for col in numeric_cols:
                # Check if column exists before applying format
                if col in result.columns:
                    result[col] = result[col].apply(
                        lambda x: f"{x:{number_format}}" if pd.notna(x) else ""
                    )
        else:
            # Use default formatting
            for col in numeric_cols:
                 # Check if column exists before applying format
                if col in result.columns:
                    result[col] = result[col].apply(
                        lambda x: (
                            (f"{x:,.{precision}f}" if pd.notna(x) else "")
                            if self.default_formats["use_thousands_separator"]
                            else (f"{x:.{precision}f}" if pd.notna(x) else "")
                        )
                    )

        return result

    def format_html(
        self,
        data: dict[str, dict[str, float]],
        apply_sign_convention: bool = True,
        include_empty_items: bool = False,
        css_styles: Optional[dict[str, str]] = None,
    ) -> str:
        """Format the statement data as HTML.

        Args:
            data: Mapping of node IDs to period-value dicts.
            apply_sign_convention: Whether to apply sign conventions.
            include_empty_items: Whether to include items with no data.
            css_styles: Optional dict of CSS styles for the HTML.

        Returns:
            str: HTML string representing the statement.
        """
        df = self.generate_dataframe(data, apply_sign_convention, include_empty_items)

        # Convert DataFrame to HTML
        html = df.to_html(index=False)

        # Add CSS styles if provided
        if css_styles:
            style_str = "<style>\n"
            for selector, style in css_styles.items():
                style_str += f"{selector} {{ {style} }}\n"
            style_str += "</style>\n"
            html = style_str + html

        return html
