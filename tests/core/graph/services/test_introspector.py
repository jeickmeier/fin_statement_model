from fin_statement_model.core.graph.graph import Graph


def _make_small_graph() -> Graph:
    g = Graph(periods=["2022"])
    g.add_financial_statement_item("A", {"2022": 1.0})
    g.add_financial_statement_item("B", {"2022": 2.0})
    g.add_calculation(
        name="C",
        input_names=["A", "B"],
        operation_type="formula",
        formula="input_0 + input_1",
        formula_variable_names=["input_0", "input_1"],
    )
    return g


def test_make_repr_counts() -> None:
    g = _make_small_graph()
    r = g._introspector.make_repr()  # type: ignore[attr-defined]
    assert "Total Nodes: 3" in r and "FS Items: 2" in r and "Calculations: 1" in r


def test_has_cycle_detection() -> None:
    g = _make_small_graph()
    a = g.get_node("A")
    c = g.get_node("C")
    assert a and c
    # Current graph has no cycle between A and C
    assert g._introspector.has_cycle(a, c) is True  # type: ignore[attr-defined]

    # Create cycle candidate: new node depending on C and feeding back to A
    from fin_statement_model.core.node_factory import NodeFactory

    factory = NodeFactory()
    new_node = factory.create_calculation_node(
        name="A",  # overwrite
        inputs=[c],
        calculation_type="formula",
        formula="input_0",
        formula_variable_names=["input_0"],
    )
    # Current graph has no cycle between C and new_node
    assert g._introspector.has_cycle(c, new_node) is False  # before adding
