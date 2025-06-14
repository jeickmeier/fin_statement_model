from fin_statement_model.core.graph.graph import Graph


def test_merge_nodes_and_periods() -> None:
    g1 = Graph(periods=["2020"])
    g1.add_financial_statement_item("A", {"2020": 1.0})

    g2 = Graph(periods=["2021"])
    g2.add_financial_statement_item("B", {"2021": 2.0})

    # Existing node in both graphs to test value merge
    g2.add_financial_statement_item("A", {"2021": 3.0})

    added, updated = g1._merge_service.merge_from(g2)  # type: ignore[attr-defined]

    # B should be added, A should be updated
    assert added == 1 and updated == 1
    assert "2021" in g1.periods and g1.get_node("B") is not None
    # A values merged
    node_a = g1.get_node("A")
    assert node_a.values == {"2020": 1.0, "2021": 3.0}
