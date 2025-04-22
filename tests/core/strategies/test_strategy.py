"""Tests for the strategy module in the Financial Statement Model.

This module contains comprehensive tests for all strategy classes and the registry.
"""

import pytest
from typing import List, Dict

from fin_statement_model.core.strategies.strategy import (
    Strategy,
    AdditionStrategy,
    SubtractionStrategy,
    MultiplicationStrategy,
    DivisionStrategy,
    WeightedAverageStrategy,
    CustomFormulaStrategy,
)
from fin_statement_model.core.strategies.registry import Registry
from fin_statement_model.core.nodes import Node


class MockNode(Node):
    """Mock Node class for testing strategies."""

    def __init__(self, value: float):
        self._value = value

    def calculate(self, period: str) -> float:
        return self._value


# Test Strategy base class
def test_strategy_abstract_base_class():
    """Test that Strategy cannot be instantiated directly."""
    with pytest.raises(TypeError):
        Strategy()


def test_strategy_description():
    """Test the default description property of Strategy."""

    class TestStrategy(Strategy):
        def calculate(self, inputs: List[Node], period: str) -> float:
            return 0.0

    strategy = TestStrategy()
    assert strategy.description == "TestStrategy"


# Test AdditionStrategy
def test_addition_strategy_basic():
    """Test basic addition strategy with multiple inputs."""
    strategy = AdditionStrategy()
    nodes = [MockNode(10.0), MockNode(20.0), MockNode(30.0)]
    result = strategy.calculate(nodes, "2023Q1")
    assert result == 60.0


def test_addition_strategy_empty_inputs():
    """Test addition strategy with empty inputs."""
    strategy = AdditionStrategy()
    result = strategy.calculate([], "2023Q1")
    assert result == 0.0


# Test SubtractionStrategy
def test_subtraction_strategy_basic():
    """Test basic subtraction strategy with multiple inputs."""
    strategy = SubtractionStrategy()
    nodes = [MockNode(100.0), MockNode(20.0), MockNode(30.0)]
    result = strategy.calculate(nodes, "2023Q1")
    assert result == 50.0


def test_subtraction_strategy_single_input():
    """Test subtraction strategy with single input."""
    strategy = SubtractionStrategy()
    nodes = [MockNode(100.0)]
    result = strategy.calculate(nodes, "2023Q1")
    assert result == 100.0


def test_subtraction_strategy_empty_inputs():
    """Test subtraction strategy with empty inputs."""
    strategy = SubtractionStrategy()
    with pytest.raises(ValueError):
        strategy.calculate([], "2023Q1")


# Test MultiplicationStrategy
def test_multiplication_strategy_basic():
    """Test basic multiplication strategy with multiple inputs."""
    strategy = MultiplicationStrategy()
    nodes = [MockNode(2.0), MockNode(3.0), MockNode(4.0)]
    result = strategy.calculate(nodes, "2023Q1")
    assert result == 24.0


def test_multiplication_strategy_empty_inputs():
    """Test multiplication strategy with empty inputs."""
    strategy = MultiplicationStrategy()
    result = strategy.calculate([], "2023Q1")
    assert result == 1.0


# Test DivisionStrategy
def test_division_strategy_basic():
    """Test basic division strategy with multiple inputs."""
    strategy = DivisionStrategy()
    nodes = [MockNode(100.0), MockNode(5.0), MockNode(2.0)]
    result = strategy.calculate(nodes, "2023Q1")
    assert result == 10.0


def test_division_strategy_insufficient_inputs():
    """Test division strategy with insufficient inputs."""
    strategy = DivisionStrategy()
    nodes = [MockNode(100.0)]
    with pytest.raises(ValueError):
        strategy.calculate(nodes, "2023Q1")


def test_division_strategy_zero_denominator():
    """Test division strategy with zero denominator."""
    strategy = DivisionStrategy()
    nodes = [MockNode(100.0), MockNode(0.0)]
    with pytest.raises(ZeroDivisionError):
        strategy.calculate(nodes, "2023Q1")


# Test WeightedAverageStrategy
def test_weighted_average_strategy_basic():
    """Test basic weighted average strategy."""
    strategy = WeightedAverageStrategy(weights=[0.4, 0.6])
    nodes = [MockNode(10.0), MockNode(20.0)]
    result = strategy.calculate(nodes, "2023Q1")
    assert result == 16.0  # (10 * 0.4) + (20 * 0.6)


def test_weighted_average_strategy_default_weights():
    """Test weighted average strategy with default weights."""
    strategy = WeightedAverageStrategy()
    nodes = [MockNode(10.0), MockNode(20.0)]
    result = strategy.calculate(nodes, "2023Q1")
    assert result == 15.0  # Equal weights


def test_weighted_average_strategy_mismatched_weights():
    """Test weighted average strategy with mismatched weights."""
    strategy = WeightedAverageStrategy(weights=[0.4, 0.6])
    nodes = [MockNode(10.0), MockNode(20.0), MockNode(30.0)]
    with pytest.raises(ValueError):
        strategy.calculate(nodes, "2023Q1")


# Test CustomFormulaStrategy
def test_custom_formula_strategy():
    """Test custom formula strategy with a simple formula."""

    def custom_formula(values: Dict[str, float]) -> float:
        return sum(values.values()) * 2

    strategy = CustomFormulaStrategy(custom_formula)
    nodes = [MockNode(10.0), MockNode(20.0)]
    result = strategy.calculate(nodes, "2023Q1")
    assert result == 60.0  # (10 + 20) * 2


# Test Registry
def test_registry_register():
    """Test registering a strategy with the registry."""
    Registry._strategies.clear()  # Clear existing strategies
    Registry.register(AdditionStrategy)
    assert "AdditionStrategy" in Registry._strategies
    assert Registry._strategies["AdditionStrategy"] == AdditionStrategy


def test_registry_register_invalid_type():
    """Test registering an invalid type with the registry."""

    class NotAStrategy:
        pass

    with pytest.raises(TypeError):
        Registry.register(NotAStrategy)


def test_registry_get():
    """Test retrieving a strategy from the registry."""
    Registry._strategies.clear()  # Clear existing strategies
    Registry.register(AdditionStrategy)
    strategy = Registry.get("AdditionStrategy")
    assert strategy == AdditionStrategy


def test_registry_get_nonexistent():
    """Test retrieving a nonexistent strategy from the registry."""
    Registry._strategies.clear()  # Clear existing strategies
    with pytest.raises(KeyError):
        Registry.get("NonexistentStrategy")


def test_registry_list():
    """Test listing all registered strategies."""
    Registry._strategies.clear()  # Clear existing strategies
    Registry.register(AdditionStrategy)
    Registry.register(SubtractionStrategy)
    strategies = Registry.list()
    assert "AdditionStrategy" in strategies
    assert "SubtractionStrategy" in strategies
    assert len(strategies) == 2
