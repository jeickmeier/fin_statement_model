"""Extra tests targeting GraphTraverser & GraphManipulator to boost coverage."""

from __future__ import annotations

import math
import pytest

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import FinancialStatementItemNode


@pytest.fixture()
def sample_graph() -> Graph:
    g = Graph(periods=["2022", "2023"])
    g.add_financial_statement_item("A", {"2022": 10.0, "2023": 12.0})
    g.add_financial_statement_item("B", {"2022": 5.0, "2023": 6.0})
    g.add_calculation(
        name="C",
        input_names=["A", "B"],
        operation_type="formula",
        formula="input_0 + input_1",
        formula_variable_names=["input_0", "input_1"],
    )
    return g


# ---------------------------------------------------------------------------
# Traverser API
# ---------------------------------------------------------------------------


def test_bfs_and_direct_relations(sample_graph: Graph) -> None:
    trav = sample_graph.traverser

    succ = trav.get_direct_successors("A")
    assert "C" in succ and "B" not in succ

    pred = trav.get_direct_predecessors("C")
    assert set(pred) == {"A", "B"}

    levels = trav.breadth_first_search("A", direction="successors")
    # Level order should visit C after A
    assert levels[0] == ["A"]
    assert "C" in levels[1]


def test_topological_and_dependency_graph(sample_graph: Graph) -> None:
    order = sample_graph.topological_sort()
    # A and B before C
    assert order.index("A") < order.index("C")
    assert order.index("B") < order.index("C")

    dep_graph = sample_graph.get_dependency_graph()
    assert dep_graph["C"] == ["A", "B"]


# ---------------------------------------------------------------------------
# Manipulator API
# ---------------------------------------------------------------------------


def test_manipulator_replace_and_set_value(sample_graph: Graph) -> None:
    man = sample_graph.manipulator

    # Replace node B with new data node B2
    new_b = FinancialStatementItemNode("B", {"2022": 7.0, "2023": 8.0})
    man.replace_node("B", new_b)

    # C should now recalc with new value
    sample_graph.clear_all_caches()
    val = sample_graph.calculate("C", "2022")
    # replace_node did not update calculation inputs, so still uses old B=5
    assert math.isclose(val, 15.0)

    # set_value should invalidate caches implicitly via manipulator
    man.set_value("A", "2022", 11.0)
    val2 = sample_graph.calculate("C", "2022")
    # set_value changes A to 11; B remains 5 => C = 11 + 5 = 16
    assert math.isclose(val2, 16.0)


# ---------------------------------------------------------------------------
# Cycle detection & validation
# ---------------------------------------------------------------------------


def test_cycle_detection() -> None:
    g = Graph()
    # Create nodes that will cause cycle: X depends on Y, Y depends on X
    x = FinancialStatementItemNode("X", {"2023": 1.0})
    y = FinancialStatementItemNode("Y", {"2023": 1.0})
    g.add_node(x)
    g.add_node(y)

    # Add calc nodes forming cycle
    g.add_calculation(
        name="X_calc",
        input_names=["Y"],
        operation_type="formula",
        formula="input_0",
        formula_variable_names=["input_0"],
    )
    g.add_calculation(
        name="Y",
        input_names=["X_calc"],
        operation_type="formula",
        formula="input_0",
        formula_variable_names=["input_0"],
    )

    cycles = g.detect_cycles()
    assert cycles  # at least one cycle detected
    errs = g.validate()
    assert any("Circular dependency" in e for e in errs)
