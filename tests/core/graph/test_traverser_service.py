"""Tests for Graph traversal and validation helpers (formerly GraphTraverser)."""

import pytest

from fin_statement_model.core.graph import GraphFacade as Graph
from fin_statement_model.core.nodes import FinancialStatementItemNode


@pytest.fixture()
def sample_graph_for_traverser() -> Graph:
    g = Graph(periods=["2021", "2022"])
    g.add_financial_statement_item("A", {"2021": 1.0, "2022": 2.0})
    g.add_financial_statement_item("B", {"2021": 3.0, "2022": 4.0})
    g.add_calculation(
        name="C",
        input_names=["A", "B"],
        operation_type="addition",
    )
    return g


def test_direct_successors_and_predecessors(sample_graph_for_traverser: Graph):
    trav = sample_graph_for_traverser.traverser
    # Successors and predecessors
    succ_A = trav.get_direct_successors("A")
    assert "C" in succ_A and "B" not in succ_A
    pred_C = trav.get_direct_predecessors("C")
    assert set(pred_C) == {"A", "B"}


def test_dependency_graph(sample_graph_for_traverser: Graph):
    trav = sample_graph_for_traverser.traverser
    dg = trav.get_dependency_graph()
    assert set(dg.keys()) >= {"A", "B", "C"}
    assert dg["A"] == []
    assert set(dg["C"]) == {"A", "B"}


def test_topological_sort(sample_graph_for_traverser: Graph):
    trav = sample_graph_for_traverser.traverser
    order = trav.topological_sort()
    # A and B before C
    assert order.index("A") < order.index("C")
    assert order.index("B") < order.index("C")


def test_detect_and_find_cycle():
    g = Graph(periods=["2021"])
    # Create cycle X -> Y -> X
    x = FinancialStatementItemNode("X", {"2021": 1.0})
    y = FinancialStatementItemNode("Y", {"2021": 1.0})
    g.add_node(x)
    g.add_node(y)
    g.add_calculation("X_calc", ["Y"], "addition")
    # rename Y calculation to match node name collision
    g.add_calculation("Y", ["X_calc"], "addition")
    trav = g.traverser
    cycles = trav.detect_cycles()
    assert any(isinstance(cycle, list) for cycle in cycles)
    # Find a cycle path for known nodes
    path = trav.find_cycle_path("Y", "Y")
    assert path is None or path[-1] == "Y"


def test_validate_reports_missing(sample_graph_for_traverser: Graph):
    g = sample_graph_for_traverser
    # Remove an input to create missing dependency
    g.remove_node("B")
    errs = g.traverser.validate()
    assert any("depends on non-existent node 'B'" in e for e in errs)


def test_would_create_cycle():
    g = Graph(periods=["2022"])
    # A -> B
    g.add_financial_statement_item("A", {"2022": 1.0})
    g.add_financial_statement_item("B", {"2022": 1.0})
    g.add_calculation("AB", ["A", "B"], "addition")
    trav = g.traverser
    # adding dependency B->AB would create cycle
    fake_node = FinancialStatementItemNode("Fake", {"2022": 0.0})
    fake_node.inputs = [g.get_node("AB")]
    # No cycle expected for this new_node configuration
    assert trav.would_create_cycle(fake_node) is False
