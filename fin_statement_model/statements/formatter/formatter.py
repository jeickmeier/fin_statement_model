"""Formatter for financial statements.

This module provides functionality for formatting financial statements
for display or reporting, including applying formatting rules, adding subtotals,
and applying sign conventions.
"""

import pandas as pd
from typing import Optional, Any
from pandas.api.types import is_numeric_dtype
import logging

from fin_statement_model.statements.structure import StatementStructure
from fin_statement_model.statements.structure import (
    Section,
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
        data: dict[str, dict[str, float]],
        apply_sign_convention: bool = True,
        include_empty_items: bool = False,
        number_format: Optional[str] = None,
    ) -> pd.DataFrame:
        """Generate a formatted DataFrame of the statement.

        Combines the statement structure with period data.

        Args:
            data: Mapping of node IDs to period-value dicts.
            apply_sign_convention: Whether to apply sign conventions.
            include_empty_items: Whether to include items with no data.
            number_format: Optional format string for numbers

        Returns:
            pd.DataFrame: Formatted statement DataFrame
        """
        # Convert structure to base DataFrame
        # This needs modification to incorporate period data
        # Placeholder: Creates structure, but needs data merge
        rows = []
        all_periods = sorted(list(set(p for node_data in data.values() for p in node_data))) if data else []

        # Helper to recursively build rows including data
        def _process_item_with_data(
            item: StatementItem, depth: int, rows_list: list[dict[str, Any]]
        ) -> None:
            item_data = data.get(getattr(item, "node_id", None), {})
            row = {
                "Line Item": "  " * depth + item.name, # Indentation
                "ID": item.id, # Added ID for clarity
                # Add periods as columns
                **{period: item_data.get(period) for period in all_periods},
                # Metadata (could be added later or made optional)
                "line_type": self._get_item_type(item),
                "node_id": getattr(item, "node_id", None),
                "sign_convention": getattr(item, "sign_convention", 1),
                "is_subtotal": isinstance(item, SubtotalLineItem),
                "is_calculated": isinstance(item, CalculatedLineItem),
            }
            if include_empty_items or any(row[p] is not None for p in all_periods):
                 rows_list.append(row)

            if hasattr(item, "children"):
                for child in item.children:
                    _process_item_with_data(child, depth + 1, rows_list)
            elif isinstance(item, Section):
                for child_item in item.items:
                    _process_item_with_data(child_item, depth + 1, rows_list)

        # Process sections and their items recursively
        for section in self.statement.sections:
            # Section Header (optional, depends on desired format)
            # rows.append({"Line Item": section.name, "ID": section.id, **{p: None for p in all_periods}})
             _process_item_with_data(section, 0, rows)


        if not rows:
            return pd.DataFrame(columns=["Line Item", "ID", *all_periods])

        df = pd.DataFrame(rows)
        # Reorder columns: Line Item, ID, then sorted periods
        cols = ["Line Item", "ID", *all_periods]
        df = df[cols + [c for c in df.columns if c not in cols]] # Keep metadata at end

        # Apply formatting
        if apply_sign_convention:
            df = self._apply_sign_convention_to_data(df, all_periods)

        # Format numbers (apply to period columns only)
        df = self._format_numbers(df, number_format, period_columns=all_periods)

        # TODO: Add subtotals (requires rework for multi-period data)
        # df = self._add_subtotals(df)

        # Remove metadata if not requested - keeping for now
        # if not include_metadata:
        #     metadata_cols = [col for col in df.columns if col.startswith("meta_")]
        #     if metadata_cols:
        #         df = df.drop(columns=metadata_cols)

        return df

    def _process_item(self, item: StatementItem, depth: int, rows: list[dict[str, Any]]) -> None:
        # This method seems less relevant now with _process_item_with_data
        # Keep it for now or remove if fully replaced
        pass

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

    def _apply_sign_convention(self, df: pd.DataFrame) -> pd.DataFrame:
        # This method needs adjustment for multi-period data
        # The logic assumed a single 'value' column
        # Keep for reference, replace with _apply_sign_convention_to_data
        pass

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

    def _add_subtotals(self, df: pd.DataFrame) -> pd.DataFrame:
        # This needs significant rework for multi-period data
        # Placeholder - current logic is single-value based
        logger.warning("Subtotal calculation needs rework for multi-period data.")
        return df

    def _calculate_section_subtotal(self, items: list[dict[str, Any]]) -> float:
        # This needs rework for multi-period data
        pass

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
