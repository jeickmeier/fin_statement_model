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


def test_manipulator_replace_node_updates_calculation_result() -> None:
    """Replacing a node should propagate to dependent calculation nodes."""
    g = Graph(periods=["2023"])
    m = GraphManipulator(g)

    g.add_financial_statement_item("A", {"2023": 2.0})
    g.add_financial_statement_item("B", {"2023": 3.0})
    g.add_calculation(
        name="SumAB",
        input_names=["A", "B"],
        operation_type="addition",
    )

    # Verify initial calculation
    assert g.calculate("SumAB", "2023") == 5.0

    # Replace node B with different value
    new_b = FinancialStatementItemNode("B", {"2023": 4.0})
    m.replace_node("B", new_b)

    # Recalculation should reflect new value (2 + 4)
    assert g.calculate("SumAB", "2023") == 6.0


def test_replace_node_performance() -> None:
    """Replacing a single node in a large graph should be fast (<5 ms)."""
    import time

    periods = ["2023"]
    g = Graph(periods=periods)
    m = GraphManipulator(g)

    # Create 5 000 independent data nodes
    for i in range(5000):
        g.add_financial_statement_item(f"N{i}", {"2023": float(i)})

    # Add a calculation node that depends on one of them to ensure linkage
    g.add_calculation(
        name="TestCalc",
        input_names=["N0", "N1"],
        operation_type="addition",
    )

    # Time the replacement of N1
    start = time.perf_counter()
    m.replace_node("N1", FinancialStatementItemNode("N1", {"2023": 123.0}))
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert (
        elapsed_ms < 5.0
    ), f"Node replacement took {elapsed_ms:.3f} ms, expected <5 ms"


def test_set_value_clears_node_cache() -> None:
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
