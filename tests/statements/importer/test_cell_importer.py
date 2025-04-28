"""Tests for the cell-based importer (deprecated/refactored)."""

from fin_statement_model.io.readers import import_from_cells
from fin_statement_model.core.nodes import FinancialStatementItemNode

# TODO: Remove skip once importer refactor confirmed/removed
# pytest.skip(
#     "Skipping tests for removed/refactored statements.importer module", allow_module_level=True
# )


def test_import_from_cells_empty() -> None:
    """Test importing from an empty list of cells."""
    # Empty input yields an empty graph (no nodes, no periods)
    g = import_from_cells([])
    assert isinstance(g, object)
    assert hasattr(g, "periods")
    assert g.periods == []
    assert g.nodes == {}


def test_import_from_cells_single() -> None:
    """Test importing from a single cell dictionary."""
    # Single cell creates one node with one period/value
    cells = [{"row_name": "Revenue", "column_name": "2020", "value": 100}]
    g = import_from_cells(cells)
    # Periods sorted
    assert g.periods == ["2020"]
    # Node exists
    node = g.nodes.get("Revenue")
    assert isinstance(node, FinancialStatementItemNode)
    assert node.values == {"2020": 100}
    assert node.get_value("2020") == 100


def test_import_from_cells_multiple_same_item() -> None:
    """Test importing multiple cells for the same item (row_name)."""
    # Multiple cells for same row_name aggregate into one node
    cells = [
        {"row_name": "Costs", "column_name": "2020", "value": 50},
        {"row_name": "Costs", "column_name": "2021", "value": 75},
    ]
    g = import_from_cells(cells)
    assert g.periods == ["2020", "2021"]
    node = g.nodes.get("Costs")
    assert node.values == {"2020": 50, "2021": 75}
    assert node.get_value("2021") == 75


def test_import_from_cells_multiple_items() -> None:
    """Test importing cells for multiple different items."""
    # Multiple different row_names create separate nodes
    cells = [
        {"row_name": "A", "column_name": "P1", "value": 1},
        {"row_name": "B", "column_name": "P2", "value": 2},
    ]
    g = import_from_cells(cells)
    assert sorted(g.periods) == ["P1", "P2"]
    assert "A" in g.nodes
    assert "B" in g.nodes
    assert g.nodes["A"].values == {"P1": 1}
    assert g.nodes["B"].values == {"P2": 2}
