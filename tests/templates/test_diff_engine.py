"""Unit tests for Template Registry diff helpers.

These tests exercise the stand-alone diff helpers without touching the
filesystem-backed registry.  Fixtures build small in-memory Graphs so the
diff logic can be validated quickly.
"""

from __future__ import annotations

from fin_statement_model.core.graph import Graph
from fin_statement_model.templates import diff as diff_helpers


# ---------------------------------------------------------------------------
# Helper – build simple graph
# ---------------------------------------------------------------------------

def _build_graph(
    *, revenue: float = 100.0, cogs: float = 60.0, formula: str = "rev - cost"
) -> Graph:  # noqa: D401
    """Return a minimal graph with Revenue, COGS and GrossProfit calculation."""

    g = Graph(periods=["2023"])
    _ = g.add_financial_statement_item("Revenue", {"2023": revenue})
    _ = g.add_financial_statement_item("COGS", {"2023": cogs})

    _ = g.add_calculation(
        name="GrossProfit",
        input_names=["Revenue", "COGS"],
        operation_type="formula",
        formula_variable_names=["rev", "cost"],
        formula=formula,
    )
    return g


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_identical_graphs_produce_empty_diff() -> None:
    g1 = _build_graph()
    g2 = g1.clone(deep=True)

    result = diff_helpers.diff(g1, g2)

    assert result.structure.added_nodes == []
    assert result.structure.removed_nodes == []
    assert result.structure.changed_nodes == {}
    assert result.values is not None
    # values diff should be empty as graphs are identical
    assert result.values.changed_cells == {}


def test_structure_diff_detects_formula_change() -> None:
    g1 = _build_graph(formula="rev - cost")
    g2 = _build_graph(formula="rev - cost * 0.9")

    result = diff_helpers.diff(g1, g2, include_values=False)

    assert "GrossProfit" in result.structure.changed_nodes
    assert result.structure.added_nodes == []
    assert result.structure.removed_nodes == []


def test_value_diff_detects_data_changes_without_structure_change() -> None:
    g1 = _build_graph(cogs=60.0)
    g2 = _build_graph(cogs=65.0)

    result = diff_helpers.diff(g1, g2, include_values=True)

    # Structure should be identical (no formula / node changes)
    assert result.structure.changed_nodes == {}

    assert result.values is not None
    # Expect at least one changed cell (COGS value)
    changed_keys = list(result.values.changed_cells)
    assert any(key.startswith("COGS|") for key in changed_keys) 