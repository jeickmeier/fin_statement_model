"""Tests for GraphManipulator mutation helpers."""

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.graph.manipulator import GraphManipulator
from fin_statement_model.core.nodes import FinancialStatementItemNode


def test_manipulator_add_and_remove_node() -> None:
    g = Graph()
    m = GraphManipulator(g)
    # Add node
    node = FinancialStatementItemNode("X", {"2023": 1.0})
    m.add_node(node)
    assert g.has_node("X")
    # Remove node
    m.remove_node("X")
    assert not g.has_node("X")


def test_manipulator_replace_node_and_update_calculation(monkeypatch) -> None:
    g = Graph(periods=["2023"])
    m = GraphManipulator(g)
    # Setup two nodes and a calc
    g.add_financial_statement_item("A", {"2023": 2.0})
    g.add_financial_statement_item("B", {"2023": 3.0})
    g.add_calculation(
        name="SumAB",
        input_names=["A", "B"],
        operation_type="addition",
    )
    # Replace B
    new_b = FinancialStatementItemNode("B", {"2023": 4.0})
    # Spy on update calculation nodes
    called = False

    def fake_update():
        nonlocal called
        called = True

    # monkeypatch the private update method
    m._update_calculation_nodes = fake_update  # type: ignore
    m.replace_node("B", new_b)
    # Should have invoked update
    assert called
    # Inputs were updated via replacement hook; calculation may still use old inputs until real update.


def test_set_value_clears_node_cache(monkeypatch) -> None:
    g = Graph(periods=["2023"])
    m = GraphManipulator(g)
    g.add_financial_statement_item("Z", {"2023": 5.0})
    # Custom node with per-node cache
    node = FinancialStatementItemNode("Y", {"2023": 10.0})
    g.add_node(node)

    # Patch clear_cache on node
    cleared = False

    def fake_clear_cache():
        nonlocal cleared
        cleared = True

    node.clear_cache = fake_clear_cache

    # set value
    m.set_value("Y", "2023", 20.0)
    assert cleared
    assert node.calculate("2023") == 20.0


def test_clear_all_caches_on_nodes() -> None:
    g = Graph(periods=["2023"])
    m = GraphManipulator(g)

    # Node with cache
    class DummyNode(FinancialStatementItemNode):
        def __init__(self, name, vals):
            super().__init__(name, vals)
            self.cleared = False

        def clear_cache(self):
            self.cleared = True

    dn = DummyNode("D", {"2023": 1.0})
    g.add_node(dn)
    m.clear_all_caches()
    assert dn.cleared
