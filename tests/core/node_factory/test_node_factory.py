"""Unit tests for decorator-based registries and NodeFactory helpers.

These tests verify that:
* Core calculation aliases, node types and forecast types are present in their
  respective registries.
* :pyclass:`fin_statement_model.core.node_factory.NodeFactory` helpers
  correctly instantiate calculation and forecast nodes.
* ``create_from_dict`` can round-trip a serialised calculation node.
"""

# mypy: ignore-errors

from __future__ import annotations

import math

from fin_statement_model.core.node_factory import NodeFactory
from fin_statement_model.core.node_factory.registries import (
    CalculationAliasRegistry,
    ForecastTypeRegistry,
    NodeTypeRegistry,
)
from fin_statement_model.core.calculations import (
    AdditionCalculation,
    FormulaCalculation,
)
from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode
from fin_statement_model.core.nodes.calculation_nodes import CalculationNode
from fin_statement_model.core.nodes.forecast_nodes import FixedGrowthForecastNode


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


def test_calculation_alias_registry_contains_builtins():
    """The calculation-alias registry should expose core aliases."""

    assert CalculationAliasRegistry.get("addition") is AdditionCalculation
    assert CalculationAliasRegistry.get("formula") is FormulaCalculation


def test_node_type_registry_contains_builtins():
    """Node-type registry must contain standard item & calculation nodes."""

    assert (
        NodeTypeRegistry.get("financial_statement_item") is FinancialStatementItemNode
    )
    assert NodeTypeRegistry.get("calculation") is CalculationNode


def test_forecast_type_registry_contains_builtins():
    """Forecast-type registry should know the simple growth node."""

    assert ForecastTypeRegistry.get("simple") is FixedGrowthForecastNode


# ---------------------------------------------------------------------------
# Builder helper tests
# ---------------------------------------------------------------------------


def test_create_calculation_node_addition():
    """NodeFactory should build an addition CalculationNode that works."""

    a = FinancialStatementItemNode("a", {"p": 1})
    b = FinancialStatementItemNode("b", {"p": 2})

    calc_node = NodeFactory.create_calculation_node(
        name="sum_ab",
        inputs=[a, b],
        calculation_type="addition",
    )

    assert isinstance(calc_node, CalculationNode)
    assert calc_node.calculate("p") == 3.0


def test_create_forecast_node_simple():
    """NodeFactory should construct a simple FixedGrowthForecastNode."""

    base = FinancialStatementItemNode("rev", {"2023": 100.0})

    fc = NodeFactory.create_forecast_node(
        forecast_type="simple",
        input_node=base,
        base_period="2023",
        forecast_periods=["2024"],
        growth_params=0.1,
    )

    assert isinstance(fc, FixedGrowthForecastNode)
    assert math.isclose(fc.calculate("2024"), 110.0)


def test_create_from_dict_roundtrip():
    """Serialise and deserialise a formula CalculationNode via factory."""

    src = FinancialStatementItemNode("src", {"2023": 10})

    serialised = {
        "type": "calculation",
        "name": "double",
        "inputs": ["src"],
        "calculation_type": "formula",
        "formula_variable_names": ["x"],
        "calculation_args": {"formula": "x * 2"},
    }

    ctx = {"src": src}
    restored = NodeFactory.create_from_dict(serialised, ctx)

    assert restored.calculate("2023") == 20.0
