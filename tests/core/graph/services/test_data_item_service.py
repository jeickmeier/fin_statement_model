from fin_statement_model.core.graph.graph import Graph


def test_add_financial_statement_item_updates_periods() -> None:
    g = Graph()
    assert g.periods == []

    g.add_financial_statement_item("Revenue", {"2024": 100.0, "2023": 80.0})
    # Periods should be sorted and unique
    assert g.periods == ["2023", "2024"]


def test_update_financial_statement_item_merge_and_replace() -> None:
    g = Graph()
    g.add_financial_statement_item("A", {"2023": 10.0})

    # Merge update: adds new period keeps old
    g.update_financial_statement_item("A", {"2024": 12.0})
    node = g.get_node("A")
    assert node is not None and node.values == {"2023": 10.0, "2024": 12.0}

    # Replace update: overwrite completely
    g.update_financial_statement_item("A", {"2025": 20.0}, replace_existing=True)
    node = g.get_node("A")
    assert node.values == {"2025": 20.0}
