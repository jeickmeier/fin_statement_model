"""Unit tests for the nodes module.

This module contains test cases for all node classes defined in the nodes module.
Each test class focuses on testing a specific node type and its functionality.
"""

import pytest
from fin_statement_model.core.nodes import (
    Node,
    FinancialStatementItemNode,
    CalculationNode,
    AdditionCalculationNode,
    SubtractionCalculationNode,
    MultiplicationCalculationNode,
    DivisionCalculationNode,
    StrategyCalculationNode,
    MetricCalculationNode,
    TwoPeriodAverageNode,
    FormulaCalculationNode,
)

class TestFinancialStatementItemNode:
    """Test cases for FinancialStatementItemNode."""

    def test_initialization(self):
        """Test proper initialization of FinancialStatementItemNode."""
        values = {"2022": 1000.0, "2021": 900.0}
        node = FinancialStatementItemNode("revenue", values)
        assert node.name == "revenue"
        assert node.values == values

    def test_calculate_existing_period(self):
        """Test calculation for an existing period."""
        values = {"2022": 1000.0, "2021": 900.0}
        node = FinancialStatementItemNode("revenue", values)
        assert node.calculate("2022") == 1000.0
        assert node.calculate("2021") == 900.0

    def test_calculate_missing_period(self):
        """Test calculation for a missing period returns 0.0."""
        values = {"2022": 1000.0, "2021": 900.0}
        node = FinancialStatementItemNode("revenue", values)
        assert node.calculate("2020") == 0.0

class TestAdditionCalculationNode:
    """Test cases for AdditionCalculationNode."""

    def test_addition_calculation(self):
        """Test basic addition calculation."""
        node1 = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        node2 = FinancialStatementItemNode("other_income", {"2022": 100.0})
        node = AdditionCalculationNode("total_income", [node1, node2])
        assert node.calculate("2022") == 1100.0

    def test_addition_with_zero(self):
        """Test addition with zero values."""
        node1 = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        node2 = FinancialStatementItemNode("other_income", {"2022": 0.0})
        node = AdditionCalculationNode("total_income", [node1, node2])
        assert node.calculate("2022") == 1000.0

    def test_addition_with_negative(self):
        """Test addition with negative values."""
        node1 = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        node2 = FinancialStatementItemNode("other_income", {"2022": -100.0})
        node = AdditionCalculationNode("total_income", [node1, node2])
        assert node.calculate("2022") == 900.0

class TestSubtractionCalculationNode:
    """Test cases for SubtractionCalculationNode."""

    def test_subtraction_calculation(self):
        """Test basic subtraction calculation."""
        node1 = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        node2 = FinancialStatementItemNode("expenses", {"2022": 600.0})
        node = SubtractionCalculationNode("profit", [node1, node2])
        assert node.calculate("2022") == 400.0

    def test_subtraction_with_zero(self):
        """Test subtraction with zero values."""
        node1 = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        node2 = FinancialStatementItemNode("expenses", {"2022": 0.0})
        node = SubtractionCalculationNode("profit", [node1, node2])
        assert node.calculate("2022") == 1000.0

    def test_subtraction_with_negative(self):
        """Test subtraction with negative values."""
        node1 = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        node2 = FinancialStatementItemNode("expenses", {"2022": -100.0})
        node = SubtractionCalculationNode("profit", [node1, node2])
        assert node.calculate("2022") == 1100.0

class TestMultiplicationCalculationNode:
    """Test cases for MultiplicationCalculationNode."""

    def test_multiplication_calculation(self):
        """Test basic multiplication calculation."""
        node1 = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        node2 = FinancialStatementItemNode("margin", {"2022": 0.4})
        node = MultiplicationCalculationNode("profit", [node1, node2])
        assert node.calculate("2022") == 400.0

    def test_multiplication_with_zero(self):
        """Test multiplication with zero values."""
        node1 = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        node2 = FinancialStatementItemNode("margin", {"2022": 0.0})
        node = MultiplicationCalculationNode("profit", [node1, node2])
        assert node.calculate("2022") == 0.0

    def test_multiplication_with_negative(self):
        """Test multiplication with negative values."""
        node1 = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        node2 = FinancialStatementItemNode("margin", {"2022": -0.4})
        node = MultiplicationCalculationNode("profit", [node1, node2])
        assert node.calculate("2022") == -400.0

class TestDivisionCalculationNode:
    """Test cases for DivisionCalculationNode."""

    def test_division_calculation(self):
        """Test basic division calculation."""
        node1 = FinancialStatementItemNode("net_income", {"2022": 400.0})
        node2 = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        node = DivisionCalculationNode("margin", [node1, node2])
        assert node.calculate("2022") == 0.4

    def test_division_by_zero(self):
        """Test division by zero raises ZeroDivisionError."""
        node1 = FinancialStatementItemNode("net_income", {"2022": 400.0})
        node2 = FinancialStatementItemNode("revenue", {"2022": 0.0})
        node = DivisionCalculationNode("margin", [node1, node2])
        with pytest.raises(ZeroDivisionError):
            node.calculate("2022")

    def test_division_with_negative(self):
        """Test division with negative values."""
        node1 = FinancialStatementItemNode("net_income", {"2022": -400.0})
        node2 = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        node = DivisionCalculationNode("margin", [node1, node2])
        assert node.calculate("2022") == -0.4

class TestFormulaCalculationNode:
    """Test cases for FormulaCalculationNode."""

    def test_simple_formula(self):
        """Test calculation with a simple formula."""
        inputs = {
            "revenue": FinancialStatementItemNode("revenue", {"2022": 1000.0}),
            "expenses": FinancialStatementItemNode("expenses", {"2022": 600.0})
        }
        node = FormulaCalculationNode("profit", inputs, "revenue - expenses")
        assert node.calculate("2022") == 400.0

    def test_complex_formula(self):
        """Test calculation with a complex formula."""
        inputs = {
            "revenue": FinancialStatementItemNode("revenue", {"2022": 1000.0}),
            "costs": FinancialStatementItemNode("costs", {"2022": 600.0}),
            "tax_rate": FinancialStatementItemNode("tax_rate", {"2022": 0.3})
        }
        node = FormulaCalculationNode("net_income", inputs, "(revenue - costs) * (1 - tax_rate)")
        assert node.calculate("2022") == 280.0

    def test_invalid_variable(self):
        """Test formula with invalid variable raises ValueError."""
        inputs = {
            "revenue": FinancialStatementItemNode("revenue", {"2022": 1000.0})
        }
        node = FormulaCalculationNode("profit", inputs, "revenue - invalid_var")
        with pytest.raises(ValueError):
            node.calculate("2022")

class TestTwoPeriodAverageNode:
    """Test cases for TwoPeriodAverageNode."""

    def test_average_calculation(self):
        """Test basic average calculation."""
        class MockGraph:
            def __init__(self):
                self.periods = ["2021", "2022"]

        input_node = FinancialStatementItemNode("assets", {
            "2021": 1000.0,
            "2022": 1200.0
        })
        graph = MockGraph()
        node = TwoPeriodAverageNode("avg_assets", input_node, graph)
        assert node.calculate("2022") == 1100.0

    def test_first_period_error(self):
        """Test calculation for first period raises ValueError."""
        class MockGraph:
            def __init__(self):
                self.periods = ["2021", "2022"]

        input_node = FinancialStatementItemNode("assets", {
            "2021": 1000.0,
            "2022": 1200.0
        })
        graph = MockGraph()
        node = TwoPeriodAverageNode("avg_assets", input_node, graph)
        with pytest.raises(ValueError):
            node.calculate("2021")

    def test_invalid_period(self):
        """Test calculation for invalid period raises ValueError."""
        class MockGraph:
            def __init__(self):
                self.periods = ["2021", "2022"]

        input_node = FinancialStatementItemNode("assets", {
            "2021": 1000.0,
            "2022": 1200.0
        })
        graph = MockGraph()
        node = TwoPeriodAverageNode("avg_assets", input_node, graph)
        with pytest.raises(ValueError):
            node.calculate("2023")

class TestStrategyCalculationNode:
    """Test cases for StrategyCalculationNode."""

    class MockStrategy:
        def calculate(self, inputs, period):
            return sum(node.calculate(period) for node in inputs)

    def test_strategy_calculation(self):
        """Test calculation using a strategy."""
        node1 = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        node2 = FinancialStatementItemNode("other_income", {"2022": 100.0})
        strategy = self.MockStrategy()
        node = StrategyCalculationNode("total_income", [node1, node2], strategy)
        assert node.calculate("2022") == 1100.0

    def test_strategy_change(self):
        """Test changing strategy at runtime."""
        node1 = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        node2 = FinancialStatementItemNode("other_income", {"2022": 100.0})
        strategy1 = self.MockStrategy()
        node = StrategyCalculationNode("total_income", [node1, node2], strategy1)
        assert node.calculate("2022") == 1100.0

        class NewStrategy:
            def calculate(self, inputs, period):
                return max(node.calculate(period) for node in inputs)

        strategy2 = NewStrategy()
        node.set_strategy(strategy2)
        assert node.calculate("2022") == 1000.0 