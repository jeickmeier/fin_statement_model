"""Unit tests for the node_factory module.

This module contains test cases for the NodeFactory class and its methods.
Each test class focuses on testing a specific factory method and its functionality.
"""

import pytest
from unittest.mock import Mock, patch
from fin_statement_model.core.node_factory import NodeFactory
from fin_statement_model.core.nodes import (
    FinancialStatementItemNode,
    CalculationNode,
    AdditionCalculationNode,
    SubtractionCalculationNode,
    MultiplicationCalculationNode,
    DivisionCalculationNode,
    StrategyCalculationNode,
    FormulaCalculationNode,
)
from fin_statement_model.forecasts import (
    ForecastNode,
    FixedGrowthForecastNode,
    CurveGrowthForecastNode,
    StatisticalGrowthForecastNode,
    CustomGrowthForecastNode,
    AverageValueForecastNode,
    AverageHistoricalGrowthForecastNode,
)

class TestNodeFactory:
    """Test cases for NodeFactory class."""

    def test_create_financial_statement_item(self):
        """Test creating a financial statement item node."""
        values = {"2022": 1000.0, "2021": 900.0}
        node = NodeFactory.create_financial_statement_item("revenue", values)
        assert isinstance(node, FinancialStatementItemNode)
        assert node.name == "revenue"
        assert node.values == values

    def test_create_financial_statement_item_invalid_name(self):
        """Test creating a financial statement item with invalid name."""
        values = {"2022": 1000.0}
        with pytest.raises(ValueError, match="Node name must be a non-empty string"):
            NodeFactory.create_financial_statement_item("", values)
        with pytest.raises(ValueError, match="Node name must be a non-empty string"):
            NodeFactory.create_financial_statement_item(None, values)

    def test_create_calculation_node_legacy(self):
        """Test creating calculation nodes using legacy node types."""
        node1 = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        node2 = FinancialStatementItemNode("expenses", {"2022": 600.0})
        
        # Test addition
        node = NodeFactory.create_calculation_node("profit", [node1, node2], "addition", use_legacy=True)
        assert isinstance(node, AdditionCalculationNode)
        assert node.calculate("2022") == 1600.0
        
        # Test subtraction
        node = NodeFactory.create_calculation_node("profit", [node1, node2], "subtraction", use_legacy=True)
        assert isinstance(node, SubtractionCalculationNode)
        assert node.calculate("2022") == 400.0
        
        # Test multiplication
        node = NodeFactory.create_calculation_node("profit", [node1, node2], "multiplication", use_legacy=True)
        assert isinstance(node, MultiplicationCalculationNode)
        assert node.calculate("2022") == 600000.0
        
        # Test division
        node = NodeFactory.create_calculation_node("margin", [node1, node2], "division", use_legacy=True)
        assert isinstance(node, DivisionCalculationNode)
        assert node.calculate("2022") == 1.6666666666666667

    @patch('fin_statement_model.core.node_factory.CalculationStrategyRegistry')
    def test_create_calculation_node_strategy(self, mock_registry):
        """Test creating calculation nodes using strategy pattern."""
        # Setup mock strategy
        mock_strategy = Mock()
        mock_strategy.calculate.return_value = 100.0
        mock_registry.get_strategy.return_value = mock_strategy
        
        node1 = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        node2 = FinancialStatementItemNode("expenses", {"2022": 600.0})
        
        # Test strategy-based calculation
        node = NodeFactory.create_calculation_node("profit", [node1, node2], "addition")
        assert isinstance(node, StrategyCalculationNode)
        assert node.calculate("2022") == 100.0
        
        # Verify strategy was retrieved
        mock_registry.get_strategy.assert_called_once_with("addition")

    def test_create_calculation_node_invalid_inputs(self):
        """Test creating calculation nodes with invalid inputs."""
        with pytest.raises(ValueError, match="Node name must be a non-empty string"):
            NodeFactory.create_calculation_node("", [], "addition")
            
        with pytest.raises(ValueError, match="Calculation node must have at least one input"):
            NodeFactory.create_calculation_node("profit", [], "addition")
            
        with pytest.raises(ValueError, match="Invalid calculation type"):
            NodeFactory.create_calculation_node("profit", [FinancialStatementItemNode("revenue", {"2022": 1000.0})], "invalid_type")

    def test_create_forecast_node_fixed(self):
        """Test creating a fixed growth forecast node."""
        base_node = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        forecast_periods = ["2023", "2024"]
        growth_rate = 0.1
        
        node = NodeFactory.create_forecast_node(
            "revenue_forecast",
            base_node,
            "2022",
            forecast_periods,
            "fixed",
            growth_rate
        )
        
        assert isinstance(node, FixedGrowthForecastNode)
        assert node.calculate("2023") == 1100.0
        assert node.calculate("2024") == 1210.0

    def test_create_forecast_node_curve(self):
        """Test creating a curve growth forecast node."""
        base_node = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        forecast_periods = ["2023", "2024"]
        growth_rates = [0.1, 0.15]
        
        node = NodeFactory.create_forecast_node(
            "revenue_forecast",
            base_node,
            "2022",
            forecast_periods,
            "curve",
            growth_rates
        )
        
        assert isinstance(node, CurveGrowthForecastNode)
        assert node.calculate("2023") == 1100.0
        assert node.calculate("2024") == 1265.0

    def test_create_forecast_node_statistical(self):
        """Test creating a statistical growth forecast node."""
        base_node = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        forecast_periods = ["2023", "2024"]
        
        def growth_func():
            return 0.1
            
        node = NodeFactory.create_forecast_node(
            "revenue_forecast",
            base_node,
            "2022",
            forecast_periods,
            "statistical",
            growth_func
        )
        
        assert isinstance(node, StatisticalGrowthForecastNode)
        # Note: Exact values will vary due to random nature

    def test_create_forecast_node_invalid_params(self):
        """Test creating forecast nodes with invalid parameters."""
        base_node = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        forecast_periods = ["2023", "2024"]
        
        # Test invalid base node
        with pytest.raises(ValueError, match="Base node is required for forecast"):
            NodeFactory.create_forecast_node("forecast", None, "2022", forecast_periods, "fixed", 0.1)
            
        # Test invalid base period
        with pytest.raises(ValueError, match="Base period must be a non-empty string"):
            NodeFactory.create_forecast_node("forecast", base_node, "", forecast_periods, "fixed", 0.1)
            
        # Test invalid forecast periods
        with pytest.raises(ValueError, match="Forecast periods must not be empty"):
            NodeFactory.create_forecast_node("forecast", base_node, "2022", [], "fixed", 0.1)
            
        # Test invalid forecast type
        with pytest.raises(ValueError, match="Invalid forecast type"):
            NodeFactory.create_forecast_node("forecast", base_node, "2022", forecast_periods, "invalid", 0.1)
            
        # Test invalid growth parameters for fixed type
        with pytest.raises(ValueError, match="For fixed growth forecast, growth_params must be a number"):
            NodeFactory.create_forecast_node("forecast", base_node, "2022", forecast_periods, "fixed", "invalid")
            
        # Test invalid growth parameters for curve type
        with pytest.raises(ValueError, match="For curve growth forecast, growth_params must be a list"):
            NodeFactory.create_forecast_node("forecast", base_node, "2022", forecast_periods, "curve", 0.1)

    def test_create_metric_node(self):
        """Test creating a metric calculation node."""
        node1 = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        node2 = FinancialStatementItemNode("expenses", {"2022": 600.0})
        
        def profit_formula(revenue, expenses):
            return revenue - expenses
            
        node = NodeFactory.create_metric_node(
            "profit",
            [node1, node2],
            profit_formula,
            "Net profit calculation"
        )
        
        assert isinstance(node, CalculationNode)
        assert node.calculate("2022") == 400.0

    def test_create_metric_node_invalid_inputs(self):
        """Test creating metric nodes with invalid inputs."""
        with pytest.raises(ValueError, match="Node name must be a non-empty string"):
            NodeFactory.create_metric_node("", [], lambda x: x)
            
        with pytest.raises(ValueError, match="Metric node must have at least one input"):
            NodeFactory.create_metric_node("profit", [], lambda x: x)
            
        with pytest.raises(ValueError, match="Formula must be a callable function"):
            NodeFactory.create_metric_node("profit", [FinancialStatementItemNode("revenue", {"2022": 1000.0})], "not_callable") 