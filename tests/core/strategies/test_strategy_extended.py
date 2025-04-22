"""Extended tests for the strategy module to increase test coverage.

This module contains additional tests that target specific code paths
in the strategy module to increase overall test coverage.
"""

import pytest
from unittest.mock import patch
from typing import Dict

from fin_statement_model.core.strategies.strategy import (
    AdditionStrategy,
    SubtractionStrategy,
    MultiplicationStrategy,
    DivisionStrategy,
    WeightedAverageStrategy,
    CustomFormulaStrategy,
)
from fin_statement_model.core.nodes import Node


class MockNode(Node):
    """Mock Node class for testing strategies with configurable names."""

    def __init__(self, value: float, name: str = None):
        self._value = value
        self.name = name

    def calculate(self, period: str) -> float:
        return self._value


# Test strategy descriptions
def test_all_strategy_descriptions():
    """Test the description property of all strategy classes."""
    # Test AdditionStrategy description
    addition_strategy = AdditionStrategy()
    assert addition_strategy.description == "Addition (sum of all inputs)"

    # Test SubtractionStrategy description
    subtraction_strategy = SubtractionStrategy()
    assert (
        subtraction_strategy.description
        == "Subtraction (first input minus sum of subsequent inputs)"
    )

    # Test MultiplicationStrategy description
    multiplication_strategy = MultiplicationStrategy()
    assert multiplication_strategy.description == "Multiplication (product of all inputs)"

    # Test DivisionStrategy description
    division_strategy = DivisionStrategy()
    assert division_strategy.description == "Division (first input / product of subsequent inputs)"


# Additional WeightedAverageStrategy tests
def test_weighted_average_strategy_with_zero_inputs():
    """Test weighted average strategy with empty input list."""
    strategy = WeightedAverageStrategy()
    with pytest.raises(ValueError, match="requires at least one input node"):
        strategy.calculate([], "2023Q1")


def test_weighted_average_strategy_description_with_weights():
    """Test the description property of WeightedAverageStrategy with weights."""
    weights = [0.3, 0.7]
    strategy = WeightedAverageStrategy(weights=weights)
    assert f"Weighted Average (using provided weights: {weights})" in strategy.description


def test_weighted_average_strategy_description_without_weights():
    """Test the description property of WeightedAverageStrategy without weights."""
    strategy = WeightedAverageStrategy()
    assert strategy.description == "Weighted Average (using equal weights)"


# Additional CustomFormulaStrategy tests
def test_custom_formula_strategy_with_invalid_function():
    """Test CustomFormulaStrategy with a non-callable formula function."""
    with pytest.raises(TypeError, match="must be callable"):
        CustomFormulaStrategy("not_a_function")


def test_custom_formula_strategy_non_numeric_result():
    """Test CustomFormulaStrategy when the formula returns a non-numeric value that can be cast to float."""

    def formula_returns_string(values: Dict[str, float]) -> str:
        return "123.45"  # A string that can be cast to float

    strategy = CustomFormulaStrategy(formula_returns_string)
    nodes = [MockNode(10.0)]

    with patch("fin_statement_model.core.strategies.strategy.logger") as mock_logger:
        result = strategy.calculate(nodes, "2023Q1")
        assert result == 123.45
        mock_logger.warning.assert_called_once()


def test_custom_formula_strategy_non_castable_result():
    """Test CustomFormulaStrategy when the formula returns a value that cannot be cast to float."""

    def formula_returns_invalid(values: Dict[str, float]) -> str:
        return "not_a_number"

    strategy = CustomFormulaStrategy(formula_returns_invalid)
    nodes = [MockNode(10.0)]

    with pytest.raises(ValueError, match="could not be cast to float"):
        strategy.calculate(nodes, "2023Q1")


def test_custom_formula_strategy_with_error_in_formula():
    """Test CustomFormulaStrategy when the formula function raises an exception."""

    def formula_with_error(values: Dict[str, float]) -> float:
        raise KeyError("Test error: Missing required key")

    strategy = CustomFormulaStrategy(formula_with_error)
    nodes = [MockNode(10.0)]

    with pytest.raises(ValueError, match="Error in custom formula"):
        strategy.calculate(nodes, "2023Q1")


def test_custom_formula_strategy_with_named_nodes():
    """Test CustomFormulaStrategy with nodes that have names."""

    def formula_using_names(values: Dict[str, float]) -> float:
        return values["revenue"] * 2 - values["costs"]

    strategy = CustomFormulaStrategy(formula_using_names)
    nodes = [MockNode(100.0, name="revenue"), MockNode(40.0, name="costs")]

    result = strategy.calculate(nodes, "2023Q1")
    assert result == 160.0  # (100 * 2) - 40


def test_custom_formula_strategy_with_unnamed_and_named_nodes():
    """Test CustomFormulaStrategy with a mix of named and unnamed nodes."""

    def formula_mixed_names(values: Dict[str, float]) -> float:
        return values["revenue"] + values["input_1"] + values["input_2"]

    strategy = CustomFormulaStrategy(formula_mixed_names)
    nodes = [
        MockNode(100.0, name="revenue"),
        MockNode(20.0, name=""),  # Empty name, should become input_1
        MockNode(30.0),  # No name attribute, should become input_2
    ]

    result = strategy.calculate(nodes, "2023Q1")
    assert result == 150.0  # 100 + 20 + 30


def test_custom_formula_strategy_description():
    """Test the description property of CustomFormulaStrategy."""

    def my_test_formula(values: Dict[str, float]) -> float:
        return sum(values.values())

    strategy = CustomFormulaStrategy(my_test_formula)
    assert strategy.description == "Custom Formula (using function: my_test_formula)"


def test_custom_formula_strategy_with_lambda():
    """Test CustomFormulaStrategy with a lambda function (no __name__)."""
    # Lambda functions don't have a standard __name__
    strategy = CustomFormulaStrategy(lambda x: sum(x.values()))

    # The description should handle anonymous functions
    assert "Custom Formula (using function: " in strategy.description

    # Test calculation works
    nodes = [MockNode(10.0), MockNode(20.0)]
    result = strategy.calculate(nodes, "2023Q1")
    assert result == 30.0
