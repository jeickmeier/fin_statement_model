"""Tests for Cell Range Importer."""

from fin_statement_model.io import import_from_cells
from fin_statement_model.core.nodes import FinancialStatementItemNode


def test_import_from_cells_basic():
    """Test importing from cells with basic configuration."""
    cells = [
        {"row_name": "Revenue", "column_name": "2023", "value": 100.0},
        {"row_name": "COGS", "column_name": "2023", "value": 200.0},
    ]

    graph = import_from_cells(cells)

    assert "Revenue" in graph.nodes
    assert "COGS" in graph.nodes
    assert graph.periods == ["2023"]

    revenue_node = graph.get_node("Revenue")
    assert isinstance(revenue_node, FinancialStatementItemNode)
    assert revenue_node.values == {"2023": 100.0}

    cogs_node = graph.get_node("COGS")
    assert cogs_node.values == {"2023": 200.0}


def test_import_from_cells_multiple_periods():
    """Test importing from cells with multiple periods."""
    cells = [
        {"row_name": "Revenue", "column_name": "2022", "value": 90.0},
        {"row_name": "Revenue", "column_name": "2023", "value": 100.0},
        {"row_name": "COGS", "column_name": "2022", "value": 180.0},
        {"row_name": "COGS", "column_name": "2023", "value": 200.0},
    ]

    graph = import_from_cells(cells)

    assert sorted(graph.periods) == ["2022", "2023"]

    revenue_node = graph.get_node("Revenue")
    assert revenue_node.values == {"2022": 90.0, "2023": 100.0}

    cogs_node = graph.get_node("COGS")
    assert cogs_node.values == {"2022": 180.0, "2023": 200.0}


def test_import_from_cells_with_missing_fields():
    """Test importing when cells have missing fields."""
    cells = [
        {"row_name": "Revenue", "column_name": "2023", "value": 100.0},
        {"row_name": "", "column_name": "2023", "value": 50.0},  # Missing row_name
        {"row_name": "COGS", "column_name": "", "value": 200.0},  # Missing column_name
        {"row_name": "Expenses", "column_name": "2023"},  # Missing value
    ]

    graph = import_from_cells(cells)

    # Only the first valid cell should be imported
    assert "Revenue" in graph.nodes
    assert "COGS" not in graph.nodes  # Skipped due to missing column_name
    assert "Expenses" in graph.nodes  # Value can be None/missing
    assert graph.periods == ["2023"]


def test_import_from_cells_empty():
    """Test importing from empty cells list."""
    graph = import_from_cells([])
    assert graph.periods == []
    assert graph.nodes == {}
