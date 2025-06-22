# Cells → Graph importer

"""Importer for converting a list of cell dictionaries into a Graph.

This module provides a simple helper function, `import_from_cells`, for creating
a `Graph` object from a list of "cell" dictionaries. This is useful for cases
where data is represented as a sparse list of individual data points rather than
a structured table.

Each dictionary in the list represents a single cell and is expected to contain
keys for `row_name` (the item), `column_name` (the period), and `value`.
"""

from typing import Any

from fin_statement_model.core.graph import Graph

__all__ = ["import_from_cells"]


def import_from_cells(cells_info: list[dict[str, Any]]) -> Graph:
    """Create a `Graph` from a list of cell data dictionaries.

    This function processes a list of dictionaries, where each dictionary
    represents a single data point (a "cell"). It groups the cells by item name,
    collects all unique periods, and then constructs a `Graph` populated with
    `FinancialStatementItemNode` instances.

    Args:
        cells_info: A list of dictionaries, where each dictionary must contain
            'row_name', 'column_name', and 'value' keys.

    Returns:
        A new `Graph` object populated with the data from the cells.
    """
    # Group cells by row_name to aggregate values per financial statement item
    items: dict[str, dict[str, Any]] = {}
    unique_periods: set[str] = set()

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
    graph = Graph(periods=sorted(unique_periods))

    # Create data nodes directly; avoids older convenience wrappers
    from fin_statement_model.core.nodes import FinancialStatementItemNode

    for name, values in items.items():
        graph.add_node(FinancialStatementItemNode(name=name, values=values))

    return graph
