# Cells → Graph importer

"""Simple helper to convert a list of *cell* dictionaries into a core :class:`Graph`.

Each cell dictionary must contain at least the following keys:

* ``row_name`` – the financial statement item (becomes node ID)
* ``column_name`` – the period identifier
* ``value`` – numeric value (int/float)
"""

from typing import Any

from fin_statement_model.core.graph import Graph

__all__ = ["import_from_cells"]


def import_from_cells(cells_info: list[dict[str, Any]]) -> Graph:
    """Return a :class:`Graph` populated from *cells_info*."""
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
