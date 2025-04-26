"""Formatter for financial statements.

This module provides functionality for formatting financial statements
for display or reporting, including applying formatting rules, adding subtotals,
and applying sign conventions.
"""

import pandas as pd
import numpy as np # Added numpy for NaN handling
from typing import Optional, Any, Union, Callable # Updated imports, added Callable
import logging

from fin_statement_model.statements.structure import StatementStructure
from fin_statement_model.statements.structure import (
    Section,
    LineItem, # Added LineItem
    CalculatedLineItem,
    SubtotalLineItem,
    StatementItem,
)

# Add core Graph and errors
from fin_statement_model.core.graph import Graph
from fin_statement_model.core.errors import NodeError, CalculationError

# Import the new formatting utils
from ._formatting_utils import format_numbers
from ._formatting_utils import apply_sign_convention as apply_sign_convention_func

# Configure logging
logger = logging.getLogger(__name__)


def _fetch_data_from_graph(statement: StatementStructure, graph: Graph) -> dict[str, dict[str, float]]:
    """Fetch necessary node data from the graph for the statement structure."""
    data: dict[str, dict[str, float]] = {}
    all_items = statement.get_all_items() # Method to get all relevant items
    periods = graph.periods

    if not periods:
        logger.warning(f"Graph has no periods defined. Cannot fetch data for statement '{statement.id}'.")
        return {}

    logger.debug(f"Fetching data for statement '{statement.id}' across periods: {periods}")

    processed_node_ids = set()

    for item in all_items:
        node_id = None
        if isinstance(item, LineItem):
            node_id = item.node_id
        elif isinstance(item, (CalculatedLineItem, SubtotalLineItem)):
            # Calculation/Subtotal items also represent nodes in the graph
            node_id = item.id

        if node_id and node_id not in processed_node_ids:
            processed_node_ids.add(node_id)
            # Check if node exists in graph before trying to calculate
            if graph.has_node(node_id):
                values = {}
                for period in periods:
                    try:
                        # Use graph.calculate which handles caching and errors
                        value = graph.calculate(node_id, period)
                        # Ensure value is float or NaN, handle potential None/other types if necessary
                        values[period] = float(value) if pd.notna(value) else np.nan
                    except (NodeError, CalculationError) as e:
                        logger.warning(f"Error calculating node '{node_id}' for period '{period}': {e}. Setting value to NaN.")
                        values[period] = np.nan
                    except Exception as e:
                        logger.error(f"Unexpected error calculating node '{node_id}' for period '{period}': {e}. Setting value to NaN.", exc_info=True)
                        values[period] = np.nan
                data[node_id] = values
            else:
                logger.warning(f"Node '{node_id}' defined in statement structure '{statement.id}' but not found in graph. Skipping data fetch.")
                # Optionally fill with NaNs if needed for formatting
                # data[node_id] = {period: np.nan for period in periods}

    logger.debug(f"Finished fetching data for {len(data)} nodes for statement '{statement.id}'.")
    return data


# Helper class for processing the statement structure
class _StructureProcessor:
    def __init__(
        self,
        statement: StatementStructure,
        all_data: dict[str, dict[str, float]],
        periods: list[str],
        include_empty_items: bool,
        indent_char: str,
        get_item_type_func: Callable, # Pass the type getter func
    ):
        self.statement = statement
        self.all_data = all_data
        self.periods = periods
        self.include_empty_items = include_empty_items
        self.indent_char = indent_char
        self._get_item_type = get_item_type_func
        self.rows: list[dict[str, Any]] = []

    def process(self) -> list[dict[str, Any]]:
        """Processes the statement structure and returns the list of rows."""
        self._process_recursive(self.statement.sections, 0)
        return self.rows

    def _calculate_and_append_subtotal(
        self,
        subtotal_item: SubtotalLineItem,
        depth: int,
    ) -> None:
        """Calculate subtotal values across periods and append the row."""
        subtotal_values: dict[str, float] = {}
        item_ids_to_sum = subtotal_item.input_ids # From CalculatedLineItem base

        if not item_ids_to_sum:
             logger.warning(f"Subtotal item '{subtotal_item.id}' has no item IDs to sum.")
             return

        for period in self.periods:
            period_sum = 0.0
            sum_contributors = 0
            for item_id in item_ids_to_sum:
                value = self.all_data.get(item_id, {}).get(period, np.nan)
                if pd.notna(value):
                     period_sum += value
                     sum_contributors += 1

            subtotal_values[period] = period_sum if sum_contributors > 0 else np.nan

        subtotal_row = {
            "Line Item": self.indent_char * depth + subtotal_item.name,
            "ID": subtotal_item.id,
            **subtotal_values,
            # Metadata
            "line_type": "subtotal",
            "node_id": subtotal_item.id,
            "sign_convention": subtotal_item.sign_convention,
            "is_subtotal": True,
            "is_calculated": True, # Subtotals are implicitly calculated
        }
        self.rows.append(subtotal_row)
        logger.debug(f"Appended subtotal row for ID: {subtotal_item.id}")

    def _process_recursive(
        self,
        items_or_sections: list[Union[Section, StatementItem]],
        current_depth: int,
    ) -> None:
        """Recursively processes structure, calculates, and appends rows."""
        for item in items_or_sections:
            if isinstance(item, Section):
                # Recurse into the section's items
                self._process_recursive(item.items, current_depth + 1)
                # After processing items, add the section's subtotal if it exists
                if hasattr(item, "subtotal") and item.subtotal:
                    self._calculate_and_append_subtotal(
                        item.subtotal, current_depth + 1
                    )
            elif isinstance(item, SubtotalLineItem):
                 # This handles subtotals defined directly within items list
                 self._calculate_and_append_subtotal(
                     item, current_depth
                 )
            elif isinstance(item, (LineItem, CalculatedLineItem)):
                node_id = getattr(item, "node_id", item.id)
                item_data = self.all_data.get(node_id, {})
                row_values = {period: item_data.get(period, np.nan) for period in self.periods}

                if self.include_empty_items or any(pd.notna(v) for v in row_values.values()):
                    row = {
                        "Line Item": self.indent_char * current_depth + item.name,
                        "ID": item.id,
                        **row_values,
                        # Metadata
                        "line_type": self._get_item_type(item), # Use passed func
                        "node_id": node_id,
                        "sign_convention": getattr(item, "sign_convention", 1),
                        "is_subtotal": isinstance(item, SubtotalLineItem),
                        "is_calculated": isinstance(item, CalculatedLineItem),
                    }
                    self.rows.append(row)


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
        self.config = {} # TODO: Consider how config is passed/used
        self.default_formats = {
            "precision": 2,
            "use_thousands_separator": True,
            "show_zero_values": True, # TODO: Check if used
            "show_negative_sign": True, # TODO: Check if used
            "indent_character": "  ",
            "subtotal_style": "bold", # TODO: Check if used
            "total_style": "bold", # TODO: Check if used
            "header_style": "bold", # TODO: Check if used
        }

    def generate_dataframe(
        self,
        graph: Graph,
        should_apply_signs: bool = True, # Renamed arg
        include_empty_items: bool = False,
        number_format: Optional[str] = None,
        include_metadata_cols: bool = False,
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

        Returns:
            pd.DataFrame: Formatted statement DataFrame with subtotals.
        """
        data = _fetch_data_from_graph(self.statement, graph)
        all_periods = graph.periods

        processor = _StructureProcessor(
            statement=self.statement,
            all_data=data,
            periods=all_periods,
            include_empty_items=include_empty_items,
            indent_char=self.default_formats["indent_character"],
            get_item_type_func=self._get_item_type,
        )
        rows = processor.process()

        if not rows:
            return pd.DataFrame(columns=["Line Item", "ID", *all_periods])

        df = pd.DataFrame(rows)

        base_cols = ["Line Item", "ID"]
        metadata_cols = ["line_type", "node_id", "sign_convention", "is_subtotal", "is_calculated"]
        final_cols = base_cols + all_periods
        if include_metadata_cols:
             final_cols += metadata_cols

        for col in final_cols:
             if col not in df.columns:
                 df[col] = np.nan if col in all_periods else ("" if col == "Line Item" else None)

        df = df[final_cols]

        # Use imported function and renamed argument
        if should_apply_signs: # Check the renamed argument
            # Call the imported function
            df = apply_sign_convention_func(df, all_periods)

        # Use imported function for number formatting
        df = format_numbers(
            df,
            default_formats=self.default_formats,
            number_format=number_format,
            period_columns=all_periods
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
        should_apply_signs: bool = True, # Use consistent arg name
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
            include_empty_items=include_empty_items
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
