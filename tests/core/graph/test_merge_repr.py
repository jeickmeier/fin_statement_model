from __future__ import annotations

from fin_statement_model.core.graph import Graph


def _build_graph(periods: list[str], items: dict[str, dict[str, float]]) -> Graph:
    """Helper to create a Graph pre-populated with *FinancialStatementItem* nodes."""
    g = Graph(periods=periods)
    for name, values in items.items():
        g.add_financial_statement_item(name, values)
    return g


def test_merge_from_adds_and_updates_nodes() -> None:
    """Merging two graphs should combine periods and node values correctly."""
    g1 = _build_graph(["2023"], {"Revenue": {"2023": 100.0}})
    g2 = _build_graph(
        ["2024"],
        {
            "Revenue": {"2024": 120.0},  # existing node (values will be merged)
            "COGS": {"2024": 60.0},  # new node (will be added)
        },
    )

    # Perform merge
    g1.merge_from(g2)

    # Period from g2 should now be present
    assert "2024" in g1.periods

    # Existing node values should have been updated
    revenue = g1.get_node("Revenue")
    assert revenue is not None and revenue.values["2024"] == 120.0  # type: ignore[index]

    # New node should have been added
    assert g1.get_node("COGS") is not None


def test_graph_repr_includes_key_information() -> None:
    """The custom ``__repr__`` string should include node counts and period list."""
    g = _build_graph(["2023"], {"Revenue": {"2023": 100.0}, "COGS": {"2023": 60.0}})

    # Add a simple calculation node (gross profit) to trigger calculation-specific repr logic
    from fin_statement_model.core.nodes.calculation_nodes import FormulaCalculationNode

    rev = g.get_node("Revenue")
    cogs = g.get_node("COGS")
    assert rev is not None and cogs is not None

    calc_node = FormulaCalculationNode(
        "GrossProfit",
        inputs={"rev": rev, "cost": cogs},
        formula="rev - cost",
    )
    g.add_node(calc_node)

    rep = repr(g)
    # The representation should now include counts for calculations and dependencies
    assert "Calculations: 1" in rep and "Dependencies" in rep and "Periods" in rep
