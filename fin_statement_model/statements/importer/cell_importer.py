"""Importer module for reading cell-based financial statement data into a FinancialStatementGraph."""

from typing import Any
from fin_statement_model.statements.graph.financial_graph import FinancialStatementGraph

__all__ = ["import_from_cells"]


def import_from_cells(cells_info: list[dict[str, Any]]) -> FinancialStatementGraph:
    """Import a list of cell dictionaries into a FinancialStatementGraph.

    Each cell dict should include at minimum:
    - 'row_name': identifier for the line item
    - 'column_name': the period label
    - 'value': the numeric value

    Args:
        cells_info: List of cell metadata dictionaries.

    Returns:
        A FinancialStatementGraph populated with detected periods and items.
    """
    # Group cells by row_name to aggregate values per financial statement item
    items: dict[str, dict[str, Any]] = {}
    unique_periods: set = set()

    for cell in cells_info:
        # Clean the item name and period
        item_name = cell.get("row_name", "").strip()
        period = cell.get("column_name", "").strip()
        value = cell.get("value")

        if not item_name or not period:
            continue

        unique_periods.add(period)
        if item_name not in items:
            items[item_name] = {}
        items[item_name][period] = value

    # Sort periods and create the graph
    sorted_periods = sorted(unique_periods)
    fsg = FinancialStatementGraph(periods=sorted_periods)

    # Add each financial statement item to the graph
    for name, values in items.items():
        fsg.add_financial_statement_item(name, values)

    return fsg
