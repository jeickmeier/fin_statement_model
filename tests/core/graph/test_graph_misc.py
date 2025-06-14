"""Miscellaneous tests covering Graph misc methods, TraversalService, and service classes."""

from __future__ import annotations

import pytest

from uuid import UUID
from fin_statement_model.core.graph import Graph
from fin_statement_model.core.graph.services.period_service import PeriodService
from fin_statement_model.core.graph.services.adjustment_service import AdjustmentService
from fin_statement_model.core.adjustments.models import AdjustmentType
from fin_statement_model.core.nodes import FinancialStatementItemNode
from fin_statement_model.core.errors import NodeError

# ---------------------------------------------------------------------------
# PeriodService tests
# ---------------------------------------------------------------------------


def test_period_service_reference_mutation() -> None:
    # Use valid period identifiers to align with new Period parsing logic
    periods = ["2022", "2024"]
    ps = PeriodService(periods)

    # Add missing period '2023' (should insert in chronological order)
    ps.add_periods(["2023"])
    assert periods == ["2022", "2023", "2024"]

    # Adding duplicates and a new future period '2025'
    ps.add_periods(["2024", "2025"])
    assert periods == ["2022", "2023", "2024", "2025"]


# ---------------------------------------------------------------------------
# AdjustmentService tests
# ---------------------------------------------------------------------------


def test_adjustment_service_basic_flow() -> None:
    svc = AdjustmentService()
    # No adjustments initially
    assert svc.list_all_adjustments() == []
    # Add adjustment
    adj_id = svc.add_adjustment(
        node_name="n",
        period="p",
        value=2.0,
        reason="r",
        adj_type=AdjustmentType.ADDITIVE,
    )
    assert isinstance(adj_id, UUID)
    # Retrieve
    adjs = svc.get_adjustments("n", "p")
    assert len(adjs) == 1
    # Apply
    val, flag = svc.apply_adjustments(1.0, adjs)
    assert val == 3.0 and flag
    # was_adjusted
    assert svc.was_adjusted("n", "p")
    # Remove
    assert svc.remove_adjustment(adj_id)
    assert svc.list_all_adjustments() == []
    # clear_all resets
    svc.clear_all()
    assert svc.list_all_adjustments() == []


# ---------------------------------------------------------------------------
# Graph facade misc tests
# ---------------------------------------------------------------------------


def test_graph_clear_and_node_methods() -> None:
    g = Graph(periods=["2020"])
    # add data node
    g.add_financial_statement_item("X", {"2020": 1.0})
    assert g.has_node("X")
    assert g.get_node("X") is not None
    # clear resets graph
    g.clear()
    assert not g.has_node("X")
    assert g.periods == []
    assert list(g.nodes) == []


def test_update_financial_statement_item_and_items_list() -> None:
    g = Graph(periods=["2020"])
    g.add_financial_statement_item("Y", {"2020": 5.0})
    # update merge
    g.update_financial_statement_item("Y", {"2021": 6.0})
    assert "2021" in g.periods
    node = g.get_node("Y")
    assert isinstance(node, FinancialStatementItemNode)
    assert 6.0 == node.values.get("2021")
    # replace_existing replaces values but does not remove old periods
    g.update_financial_statement_item("Y", {"2022": 7.0}, replace_existing=True)
    # Periods accumulate (2020 from initial, 2021 from first update, 2022 now)
    assert set(g.periods) == {"2020", "2021", "2022"}
    assert node.values == {"2022": 7.0}
    # get_financial_statement_items
    items = g.get_financial_statement_items()
    assert len(items) == 1 and items[0].name == "Y"


def test_graph_repr_and_merge_from() -> None:
    g1 = Graph(periods=["2020"])
    g1.add_financial_statement_item("A", {"2020": 1.0})
    r = repr(g1)
    assert "Total Nodes: 1" in r and "FS Items: 1" in r

    # Merge with another graph
    g2 = Graph(periods=["2021"])
    node_b = FinancialStatementItemNode("B", {"2021": 2.0})
    g2.add_node(node_b)
    g1.merge_from(g2)
    assert "2021" in g1.periods
    assert g1.has_node("B")
    # Merge updating values
    g3 = Graph()
    g3.add_financial_statement_item("A", {"2021": 3.0})
    g1.merge_from(g3)
    # A.values should include 2021
    val = g1.calculate("A", "2021")
    assert val == 3.0


def test_recalculate_and_clear_caches() -> None:
    g = Graph(periods=["2022"])
    g.add_financial_statement_item("A", {"2022": 10.0})
    g.add_financial_statement_item("B", {"2022": 2.0})
    g.add_calculation(
        name="D",
        input_names=["A", "B"],
        operation_type="formula",
        formula="input_0 / input_1",
        formula_variable_names=["input_0", "input_1"],
    )
    # initial calculate
    assert g.calculate("D", "2022") == 5.0
    # recalculate_all
    g.recalculate_all(["2022"])
    # change B and recalc_all
    g.set_value("B", "2022", 5.0)
    g.recalculate_all()
    assert g.calculate("D", "2022") == 2.0
    # clear caches
    g.clear_calculation_cache()
    assert g.calculate("D", "2022") == 2.0
    # Facade traversal methods
    calc_nodes = g.get_calculation_nodes()
    assert "D" in calc_nodes
    deps = g.get_dependencies("D")
    assert set(deps) == {"A", "B"}
    # direct successors/predecessors
    succ = g.get_direct_successors("A")
    assert "D" in succ
    pred = g.get_direct_predecessors("D")
    assert set(pred) == {"A", "B"}
    # breadth first search
    bfs = g.breadth_first_search("A", direction="successors")
    assert bfs[0] == ["A"] and "D" in bfs[1]
    # topological sort
    ts = g.topological_sort()
    assert ts.index("A") < ts.index("D")
    # validate / detect cycles
    assert g.validate() == []
    assert g.detect_cycles() == []
    # Invalid add_periods type
    with pytest.raises(TypeError):
        g.add_periods("notalist")
    # recalculate_all wrong input type
    with pytest.raises(TypeError):
        g.recalculate_all(123)  # type error
    # replace_node on non-existent node should raise NodeError
    with pytest.raises(NodeError):
        g.replace_node("missing", "notanode")
    # set_value errors
    with pytest.raises(ValueError):
        g.set_value("D", "2021", 1.0)  # period not exists
    # Wrong value type on calculation node raises NotImplementedError
    with pytest.raises(NotImplementedError):
        g.set_value("D", "2022", "bad")  # wrong value type
    # merge_from invalid argument
    with pytest.raises(TypeError):
        g.merge_from("not a graph")
    # get_metric_info error path
    with pytest.raises(ValueError):
        g.get_metric_info("no_metric")
    # get_adjusted_value without adjustments returns base value
    base = g.calculate("D", "2022")
    assert g.get_adjusted_value("D", "2022") == base
    # return_flag calculates tuple
    val_flag = g.get_adjusted_value("D", "2022", return_flag=True)
    assert isinstance(val_flag, tuple) and val_flag[0] == base
