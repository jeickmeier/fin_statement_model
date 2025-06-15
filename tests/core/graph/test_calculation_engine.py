"""Tests for CalculationEngine service covering calculate, recalc_all, cache, builder helpers."""

from __future__ import annotations

import math

import pytest

from fin_statement_model.core.errors import NodeError
from fin_statement_model.core.graph import Graph
from fin_statement_model.core.graph.services.calculation_engine import CalculationEngine


def setup_simple_engine() -> tuple[CalculationEngine, Graph]:
    g = Graph(periods=["2023"])
    # add data and calc nodes
    g.add_financial_statement_item("A", {"2023": 10.0})
    g.add_financial_statement_item("B", {"2023": 5.0})
    g.add_calculation("Sum", ["A", "B"], "addition")
    engine = g._calc_engine
    return engine, g


def test_calculate_and_cache_behavior() -> None:
    engine, g = setup_simple_engine()
    # ensure cache empty
    assert engine.cache == {}
    # calculate and cache
    val = engine.calculate("Sum", "2023")
    assert val == 15.0
    assert engine.cache.get("Sum", {}).get("2023") == 15.0
    # repeated call hits cache
    engine.cache["Sum"]["2023"] = 20.0
    assert engine.calculate("Sum", "2023") == 20.0


def test_clear_all_resets_cache() -> None:
    engine, _ = setup_simple_engine()
    engine.calculate("Sum", "2023")
    assert engine.cache
    engine.clear_all()
    assert engine.cache == {}


def test_recalc_all_populates_cache() -> None:
    engine, g = setup_simple_engine()
    engine.clear_all()
    engine.recalc_all()
    # both periods=default ['2023']
    assert engine.cache["Sum"]["2023"] == 15.0


def test_add_calculation_invalid_inputs() -> None:
    engine, _ = setup_simple_engine()
    with pytest.raises(TypeError):
        engine.add_calculation(
            name="X", input_names="notalist", operation_type="addition"
        )


def test_add_custom_calculation_errors_and_success() -> None:
    engine, g = setup_simple_engine()
    # invalid callable
    with pytest.raises(TypeError):
        engine.add_custom_calculation(name="C1", calculation_func=123)
    # valid custom calc with one input
    # add a data node for input
    g.add_financial_statement_item("X", {"2023": 5.0})
    node = engine.add_custom_calculation(
        name="Custom",
        calculation_func=lambda x: x + 1,
        inputs=["X"],
    )
    assert node.name == "Custom"
    assert math.isclose(g.calculate("Custom", "2023"), 6.0)
    # error when function signature does not match inputs at calculation time
    engine.add_custom_calculation(
        name="BadCustom",
        calculation_func=lambda x, y: x + y,
        inputs=["X"],
    )
    # calculating invokes user function with mismatched args
    with pytest.raises(TypeError):
        g.calculate("BadCustom", "2023")


def test_add_metric_with_missing_nodes() -> None:
    engine, _ = setup_simple_engine()
    with pytest.raises(NodeError):
        engine.add_metric("nonexistent_metric")


def test_ensure_signed_nodes() -> None:
    engine, g = setup_simple_engine()
    created = engine.ensure_signed_nodes(["A"])
    assert created == ["A_signed"]
    assert g.calculate("A_signed", "2023") == -10.0


def test_change_calculation_method_invalid() -> None:
    engine, g = setup_simple_engine()
    # changing non-existent node
    # Attempting to change calculation method on a non-existent node should raise NodeError.
    with pytest.raises(NodeError):
        engine.change_calculation_method("NoNode", "addition")
