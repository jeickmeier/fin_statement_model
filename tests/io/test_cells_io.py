"""Tests for `fin_statement_model.io.graph.cells_io.import_from_cells` helper.

The helper is thin but critical for spreadsheet-style ingestion workflows. We
verify it builds a `Graph` with expected nodes and values from a list of cell
records.
"""

from __future__ import annotations

from fin_statement_model.io.graph.cells_io import import_from_cells


def test_import_from_cells_basic() -> None:
    """Ensure cells are aggregated into a Graph with correct values."""
    cells = [
        {"row_name": "Revenue", "column_name": "2023", "value": 100.0},
        {"row_name": "Revenue", "column_name": "2024", "value": 120.0},
        {"row_name": "COGS", "column_name": "2023", "value": 60.0},
        {"row_name": "COGS", "column_name": "2024", "value": 72.0},
    ]

    graph = import_from_cells(cells)

    # Expect two nodes and two periods
    assert set(graph.nodes.keys()) == {"Revenue", "COGS"}
    assert graph.periods == ["2023", "2024"]

    revenue_node = graph.nodes["Revenue"]
    cogs_node = graph.nodes["COGS"]

    assert revenue_node.values == {"2023": 100.0, "2024": 120.0}
    assert cogs_node.values == {"2023": 60.0, "2024": 72.0}
