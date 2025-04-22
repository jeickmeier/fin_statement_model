"""Tests for the logging functionality in the strategies module.

This module tests that the strategies log correctly at various levels.
"""

from unittest.mock import patch

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
    """Mock Node class for testing strategies."""

    def __init__(self, value: float):
        self._value = value

    def calculate(self, period: str) -> float:
        return self._value


def test_addition_strategy_logging():
    """Test that AdditionStrategy logs debug information."""
    with patch("fin_statement_model.core.strategies.strategy.logger") as mock_logger:
        strategy = AdditionStrategy()
        nodes = [MockNode(10.0), MockNode(20.0)]
        strategy.calculate(nodes, "2023Q1")

        mock_logger.debug.assert_called_once_with("Applying addition strategy for period 2023Q1")


def test_subtraction_strategy_logging():
    """Test that SubtractionStrategy logs debug information."""
    with patch("fin_statement_model.core.strategies.strategy.logger") as mock_logger:
        strategy = SubtractionStrategy()
        nodes = [MockNode(30.0), MockNode(10.0)]
        strategy.calculate(nodes, "2023Q1")

        mock_logger.debug.assert_called_once_with("Applying subtraction strategy for period 2023Q1")


def test_multiplication_strategy_logging():
    """Test that MultiplicationStrategy logs debug information."""
    with patch("fin_statement_model.core.strategies.strategy.logger") as mock_logger:
        strategy = MultiplicationStrategy()
        nodes = [MockNode(2.0), MockNode(3.0)]
        strategy.calculate(nodes, "2023Q1")

        mock_logger.debug.assert_called_once_with(
            "Applying multiplication strategy for period 2023Q1"
        )


def test_multiplication_strategy_empty_inputs_logging():
    """Test that MultiplicationStrategy logs warning for empty inputs."""
    with patch("fin_statement_model.core.strategies.strategy.logger") as mock_logger:
        strategy = MultiplicationStrategy()
        strategy.calculate([], "2023Q1")

        mock_logger.warning.assert_called_once_with(
            "Multiplication strategy called with empty inputs, returning 1.0"
        )


def test_division_strategy_logging():
    """Test that DivisionStrategy logs debug information."""
    with patch("fin_statement_model.core.strategies.strategy.logger") as mock_logger:
        strategy = DivisionStrategy()
        nodes = [MockNode(10.0), MockNode(2.0)]
        strategy.calculate(nodes, "2023Q1")

        mock_logger.debug.assert_called_once_with("Applying division strategy for period 2023Q1")


def test_weighted_average_strategy_initialization_logging():
    """Test that WeightedAverageStrategy logs during initialization."""
    with patch("fin_statement_model.core.strategies.strategy.logger") as mock_logger:
        weights = [0.3, 0.7]
        WeightedAverageStrategy(weights=weights)

        mock_logger.info.assert_called_once_with(
            "Initialized WeightedAverageStrategy with weights: [0.3, 0.7]"
        )


def test_weighted_average_strategy_equal_weights_logging():
    """Test that WeightedAverageStrategy logs when using equal weights."""
    with patch("fin_statement_model.core.strategies.strategy.logger") as mock_logger:
        strategy = WeightedAverageStrategy()
        nodes = [MockNode(10.0), MockNode(20.0)]
        strategy.calculate(nodes, "2023Q1")

        mock_logger.debug.assert_any_call("Using equal weights for weighted average.")
        mock_logger.debug.assert_any_call("Applying weighted average strategy for period 2023Q1")


def test_weighted_average_strategy_custom_weights_logging():
    """Test that WeightedAverageStrategy logs when using custom weights."""
    with patch("fin_statement_model.core.strategies.strategy.logger") as mock_logger:
        weights = [0.3, 0.7]
        strategy = WeightedAverageStrategy(weights=weights)
        nodes = [MockNode(10.0), MockNode(20.0)]
        strategy.calculate(nodes, "2023Q1")

        mock_logger.debug.assert_any_call(f"Using provided weights: {weights}")
        mock_logger.debug.assert_any_call("Applying weighted average strategy for period 2023Q1")


def test_custom_formula_strategy_initialization_logging():
    """Test that CustomFormulaStrategy logs during initialization."""
    with patch("fin_statement_model.core.strategies.strategy.logger") as mock_logger:

        def test_formula(values):
            return sum(values.values())

        CustomFormulaStrategy(test_formula)

        mock_logger.info.assert_called_once_with(
            "Initialized CustomFormulaStrategy with function: test_formula"
        )


def test_custom_formula_strategy_calculation_logging():
    """Test that CustomFormulaStrategy logs during calculation."""
    with patch("fin_statement_model.core.strategies.strategy.logger") as mock_logger:

        def test_formula(values):
            return sum(values.values())

        strategy = CustomFormulaStrategy(test_formula)
        nodes = [MockNode(10.0), MockNode(20.0)]
        strategy.calculate(nodes, "2023Q1")

        # Check that debug logging for calculation occurred
        assert any(
            "Applying custom formula strategy for period 2023Q1" in str(call)
            for call in mock_logger.debug.call_args_list
        )
