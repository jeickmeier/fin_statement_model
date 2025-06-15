"""Unit tests for `fin_statement_model.core.graph` facade layer.

These tests focus on the glue code we kept inside `Graph` after the recent
service-extraction refactor.  They exercise public APIs only (no private
attributes) and aim to push coverage of the `core/graph` package above the
project-wide 85 % threshold.
"""

from __future__ import annotations

import math
from uuid import UUID

from fin_statement_model.core.adjustments.models import AdjustmentType
from fin_statement_model.core.graph import Graph

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_simple_graph() -> Graph:
    """Return a graph with two data nodes – Revenue and COGS – for 2023."""
    g = Graph(periods=["2023"])
    g.add_financial_statement_item("Revenue", {"2023": 100.0})
    g.add_financial_statement_item("COGS", {"2023": 60.0})
    return g


# ---------------------------------------------------------------------------
# Basic node operations
# ---------------------------------------------------------------------------


def test_add_financial_statement_item_calculate() -> None:
    g = _make_simple_graph()
    assert math.isclose(g.calculate("Revenue", "2023"), 100.0)
    assert math.isclose(g.calculate("COGS", "2023"), 60.0)


# ---------------------------------------------------------------------------
# Calculation helpers (delegated to CalculationEngine)
# ---------------------------------------------------------------------------


def test_add_calculation_formula() -> None:
    g = _make_simple_graph()

    # Create a formula calculation node for gross profit
    gp_node = g.add_calculation(
        name="GrossProfit",
        input_names=["Revenue", "COGS"],
        operation_type="formula",
        formula="input_0 - input_1",
        formula_variable_names=["input_0", "input_1"],
    )

    assert gp_node.name == "GrossProfit"
    assert math.isclose(g.calculate("GrossProfit", "2023"), 40.0)


# ---------------------------------------------------------------------------
# ensure_signed_nodes / change_calculation_method
# ---------------------------------------------------------------------------


def test_ensure_signed_nodes_and_change_method() -> None:
    g = _make_simple_graph()

    # Create negative sign node explicitly
    g.add_item("Revenue_signed", formula="-(Revenue)")
    assert math.isclose(g.calculate("Revenue_signed", "2023"), -100.0)

    # Change formula to identity (addition of single input)
    g.replace_node(code="Revenue_signed", formula="Revenue")
    assert math.isclose(g.calculate("Revenue_signed", "2023"), 100.0)


# ---------------------------------------------------------------------------
# Adjustment service facade
# ---------------------------------------------------------------------------


def test_adjustments_workflow() -> None:
    g = _make_simple_graph()

    # Gross profit node for testing adjustments
    g.add_calculation(
        name="GrossProfit",
        input_names=["Revenue", "COGS"],
        operation_type="formula",
        formula="input_0 - input_1",
        formula_variable_names=["input_0", "input_1"],
    )

    base_value = g.calculate("GrossProfit", "2023")
    assert math.isclose(base_value, 40.0)

    # Add a replacement adjustment overriding value to 50
    adj_id = g.add_adjustment(
        node_name="GrossProfit",
        period="2023",
        value=50.0,
        reason="Manager override",
        adj_type=AdjustmentType.REPLACEMENT,
    )
    assert isinstance(adj_id, UUID)

    val, flag = g.get_adjusted_value("GrossProfit", "2023", return_flag=True)
    assert flag is True
    assert math.isclose(val, 50.0)

    # Ensure was_adjusted reflects the change
    assert g.was_adjusted("GrossProfit", "2023") is True


# ---------------------------------------------------------------------------
# Traversal delegates
# ---------------------------------------------------------------------------


def test_topological_sort_and_cycles() -> None:
    g = _make_simple_graph()
    g.add_calculation(
        name="GrossProfit",
        input_names=["Revenue", "COGS"],
        operation_type="formula",
        formula="input_0 - input_1",
        formula_variable_names=["input_0", "input_1"],
    )

    order = g.topological_sort()
    # Revenue & COGS must appear before GrossProfit
    assert order.index("Revenue") < order.index("GrossProfit")
    assert order.index("COGS") < order.index("GrossProfit")

    # No cycles expected
    assert g.detect_cycles() == []
    assert g.validate() == []
