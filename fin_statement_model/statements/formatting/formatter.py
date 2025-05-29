"""Formatter for financial statements.

This module provides functionality for formatting financial statements
for display or reporting, including applying formatting rules, adding subtotals,
and applying sign conventions.
"""

import pandas as pd
import numpy as np  # Added numpy for NaN handling
from typing import Optional, Any, Union
import logging

from fin_statement_model.statements.structure import StatementStructure
from fin_statement_model.statements.structure import (
    Section,
    CalculatedLineItem,
    SubtotalLineItem,
    StatementItem,
)

# Add core Graph and errors
from fin_statement_model.core.graph import Graph

# Import adjustment types for filtering
from fin_statement_model.core.adjustments.models import AdjustmentFilterInput

# Import the ID resolver
from fin_statement_model.statements.population.id_resolver import IDResolver

# Import the data fetcher
from fin_statement_model.statements.formatting.data_fetcher import DataFetcher

# Import the new formatting utils
from ._formatting_utils import format_numbers
from ._formatting_utils import apply_sign_convention as apply_sign_convention_func

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
        self.config = {}  # TODO: Consider how config is passed/used
        self.default_formats = {
            "precision": 2,
            "use_thousands_separator": True,
            "show_zero_values": True,  # TODO: Check if used
            "show_negative_sign": True,  # TODO: Check if used
            "indent_character": "  ",
            "subtotal_style": "bold",  # TODO: Check if used
            "total_style": "bold",  # TODO: Check if used
            "header_style": "bold",  # TODO: Check if used
        }

    def generate_dataframe(
        self,
        graph: Graph,
        should_apply_signs: bool = True,  # Renamed arg
        include_empty_items: bool = False,
        number_format: Optional[str] = None,
        include_metadata_cols: bool = False,
        # --- Adjustment Integration ---
        adjustment_filter: AdjustmentFilterInput = None,
        add_is_adjusted_column: bool = False,
        # --- End Adjustment Integration ---
    ) -> pd.DataFrame:
        """Generate a formatted DataFrame of the statement including subtotals.

        Queries the graph for data based on the statement structure,
        calculates subtotals, and formats the result.

        Args:
            graph: The core.graph.Graph instance containing the data.
            should_apply_signs: Whether to apply sign conventions after calculation.
            include_empty_items: Whether to include items with no data rows.
            number_format: Optional Python format string for numbers (e.g., ',.2f').
            include_metadata_cols: If True, includes hidden metadata columns
                                   (like sign_convention, node_id) in the output.
            adjustment_filter: Optional filter for applying adjustments during data fetch.
            add_is_adjusted_column: If True, adds a boolean column indicating if the
                                    value for a node/period was adjusted.

        Returns:
            pd.DataFrame: Formatted statement DataFrame with subtotals.
        """
        # Use DataFetcher to get data
        data_fetcher = DataFetcher(self.statement, graph)
        fetch_result = data_fetcher.fetch_all_data(
            adjustment_filter=adjustment_filter,
            include_missing=include_empty_items,
        )

        # Log any warnings/errors from fetching
        if fetch_result.errors.has_warnings() or fetch_result.errors.has_errors():
            fetch_result.errors.log_all(
                prefix=f"Statement '{self.statement.id}' data fetch: "
            )

        data = fetch_result.data
        all_periods = graph.periods

        # Initialize ID resolver for consistent node ID resolution
        id_resolver = IDResolver(self.statement)

        # --- Build Rows Recursively --- #
        rows: list[dict[str, Any]] = []
        indent_char = self.default_formats["indent_character"]

        def process_recursive(
            items_or_sections: list[Union[Section, StatementItem]], current_depth: int
        ) -> None:
            for item in items_or_sections:
                if isinstance(item, Section):
                    process_recursive(item.items, current_depth + 1)
                    if hasattr(item, "subtotal") and item.subtotal:
                        process_recursive(
                            [item.subtotal], current_depth + 1
                        )  # Process subtotal like other items
                elif isinstance(item, StatementItem):
                    # Use ID resolver to get the correct node ID
                    node_id = id_resolver.resolve(item.id, graph)
                    if node_id:
                        item_data = data.get(node_id, {})
                        row_values = {p: item_data.get(p, np.nan) for p in all_periods}

                        if include_empty_items or any(
                            pd.notna(v) for v in row_values.values()
                        ):
                            row = {
                                "Line Item": indent_char * current_depth + item.name,
                                "ID": item.id,
                                **row_values,
                                # Metadata
                                "line_type": self._get_item_type(item),
                                "node_id": node_id,
                                "sign_convention": getattr(item, "sign_convention", 1),
                                "is_subtotal": isinstance(item, SubtotalLineItem),
                                "is_calculated": isinstance(item, CalculatedLineItem),
                            }
                            rows.append(row)

        process_recursive(self.statement.sections, 0)
        # --- End Build Rows --- #

        if not rows:
            return pd.DataFrame(columns=["Line Item", "ID", *all_periods])

        df = pd.DataFrame(rows)

        base_cols = ["Line Item", "ID"]
        metadata_cols = [
            "line_type",
            "node_id",
            "sign_convention",
            "is_subtotal",
            "is_calculated",
        ]

        # --- Adjustment Integration: Add 'is_adjusted' column if requested ---
        adjusted_flag_cols = []
        if add_is_adjusted_column and all_periods:
            # Get node IDs from the dataframe
            node_ids_to_check = []
            for _, row in df.iterrows():
                node_id = row.get("node_id")
                is_calc_or_subtotal = row.get("is_calculated", False) or row.get(
                    "is_subtotal", False
                )
                if node_id and not is_calc_or_subtotal:
                    node_ids_to_check.append(node_id)

            # Use DataFetcher to check adjustments
            if node_ids_to_check:
                adjustment_status = data_fetcher.check_adjustments(
                    node_ids_to_check, all_periods, adjustment_filter
                )
            else:
                adjustment_status = {}

            # Build adjustment columns
            is_adjusted_data = []
            for _, row in df.iterrows():
                node_id = row.get("node_id")
                is_calc_or_subtotal = row.get("is_calculated", False) or row.get(
                    "is_subtotal", False
                )

                if node_id and not is_calc_or_subtotal and node_id in adjustment_status:
                    row_adj_flags = {
                        f"{period}_is_adjusted": adjustment_status[node_id].get(
                            period, False
                        )
                        for period in all_periods
                    }
                else:
                    # For calculated/subtotal items or missing nodes, flags are False
                    row_adj_flags = {
                        f"{period}_is_adjusted": False for period in all_periods
                    }
                is_adjusted_data.append(row_adj_flags)

            if is_adjusted_data:
                adj_df = pd.DataFrame(is_adjusted_data, index=df.index)
                df = pd.concat([df, adj_df], axis=1)
                adjusted_flag_cols = list(adj_df.columns)
        # --- End Adjustment Integration ---

        final_cols = base_cols + all_periods
        if add_is_adjusted_column:
            final_cols += adjusted_flag_cols  # Add adjustment flag columns here
        if include_metadata_cols:
            # Add metadata cols (excluding adjustment flags if they are already added)
            final_cols += [
                m_col for m_col in metadata_cols if m_col not in adjusted_flag_cols
            ]

        for col in final_cols:
            if col not in df.columns:
                df[col] = (
                    np.nan
                    if col in all_periods
                    else ("" if col == "Line Item" else None)
                )

        df = df[final_cols]

        # Use imported function and renamed argument
        if should_apply_signs:  # Check the renamed argument
            # Call the imported function
            df = apply_sign_convention_func(df, all_periods)

        # Use imported function for number formatting
        df = format_numbers(
            df,
            default_formats=self.default_formats,
            number_format=number_format,
            period_columns=all_periods,
        )

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

    def format_html(
        self,
        graph: Graph,
        should_apply_signs: bool = True,  # Use consistent arg name
        include_empty_items: bool = False,
        css_styles: Optional[dict[str, str]] = None,
    ) -> str:
        """Format the statement data as HTML.

        Args:
            graph: The core.graph.Graph instance containing the data.
            should_apply_signs: Whether to apply sign conventions.
            include_empty_items: Whether to include items with no data.
            css_styles: Optional dict of CSS styles for the HTML.

        Returns:
            str: HTML string representing the statement.
        """
        df = self.generate_dataframe(
            graph=graph,
            should_apply_signs=should_apply_signs,
            include_empty_items=include_empty_items,
            # number_format is applied internally by generate_dataframe
        )
        html = df.to_html(index=False)
        if css_styles:
            style_str = "<style>\n"
            for selector, style in css_styles.items():
                style_str += f"{selector} {{ {style} }}\n"
            style_str += "</style>\n"
            html = style_str + html
        return html
