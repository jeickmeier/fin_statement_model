"""Unit tests for the CalculationEngine class.

This module contains test cases for the CalculationEngine class which is responsible
for managing calculations in the financial statement graph.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from fin_statement_model.core.calculation_engine import CalculationEngine
from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import (Node, CalculationNode, AdditionCalculationNode,
                    SubtractionCalculationNode, MultiplicationCalculationNode,
                    DivisionCalculationNode, MetricCalculationNode, StrategyCalculationNode)


class TestCalculationEngine:
    """Test cases for the CalculationEngine class."""

    @pytest.fixture
    def graph(self):
        """Create a mock graph for testing."""
        return Mock(spec=Graph)

    @pytest.fixture
    def engine(self, graph):
        """Create a CalculationEngine instance for testing."""
        return CalculationEngine(graph)
    
    def test_init(self, engine, graph):
        """Test CalculationEngine initialization."""
        assert engine.graph == graph
    
    def test_add_calculation_addition(self, engine, graph):
        """Test adding an addition calculation node."""
        # Setup
        name = "total_revenue"
        input_names = ["revenue_us", "revenue_eu"]
        operation_type = "addition"
        
        # Mock input nodes
        mock_node_us = Mock(spec=Node)
        mock_node_eu = Mock(spec=Node)
        graph.get_node.side_effect = lambda x: {"revenue_us": mock_node_us, "revenue_eu": mock_node_eu}.get(x)
        
        # Mock result node
        mock_result_node = Mock(spec=AdditionCalculationNode)
        
        # Mock NodeFactory
        with patch('fin_statement_model.core.calculation_engine.NodeFactory') as mock_factory:
            mock_factory.create_calculation_node.return_value = mock_result_node
            
            # Execute
            result = engine.add_calculation(name, input_names, operation_type)
            
            # Verify
            graph.get_node.assert_has_calls([call("revenue_us"), call("revenue_eu")])
            mock_factory.create_calculation_node.assert_called_once_with(
                name, [mock_node_us, mock_node_eu], operation_type
            )
            graph.add_node.assert_called_once_with(mock_result_node)
            assert result == mock_result_node
            assert hasattr(mock_result_node, "input_names")
            assert mock_result_node.input_names == input_names
    
    def test_add_calculation_subtraction(self, engine, graph):
        """Test adding a subtraction calculation node."""
        # Setup
        name = "profit"
        input_names = ["revenue", "expenses"]
        operation_type = "subtraction"
        
        # Mock input nodes
        mock_revenue = Mock(spec=Node)
        mock_expenses = Mock(spec=Node)
        graph.get_node.side_effect = lambda x: {"revenue": mock_revenue, "expenses": mock_expenses}.get(x)
        
        # Mock result node
        mock_result_node = Mock(spec=SubtractionCalculationNode)
        
        # Mock NodeFactory
        with patch('fin_statement_model.core.calculation_engine.NodeFactory') as mock_factory:
            mock_factory.create_calculation_node.return_value = mock_result_node
            
            # Execute
            result = engine.add_calculation(name, input_names, operation_type)
            
            # Verify
            graph.get_node.assert_has_calls([call("revenue"), call("expenses")])
            mock_factory.create_calculation_node.assert_called_once_with(
                name, [mock_revenue, mock_expenses], operation_type
            )
            graph.add_node.assert_called_once_with(mock_result_node)
            assert result == mock_result_node
    
    def test_add_calculation_multiplication(self, engine, graph):
        """Test adding a multiplication calculation node."""
        # Setup
        name = "revenue_growth"
        input_names = ["revenue", "growth_factor"]
        operation_type = "multiplication"
        
        # Mock input nodes
        mock_revenue = Mock(spec=Node)
        mock_factor = Mock(spec=Node)
        graph.get_node.side_effect = lambda x: {"revenue": mock_revenue, "growth_factor": mock_factor}.get(x)
        
        # Mock result node
        mock_result_node = Mock(spec=MultiplicationCalculationNode)
        
        # Mock NodeFactory
        with patch('fin_statement_model.core.calculation_engine.NodeFactory') as mock_factory:
            mock_factory.create_calculation_node.return_value = mock_result_node
            
            # Execute
            result = engine.add_calculation(name, input_names, operation_type)
            
            # Verify
            graph.get_node.assert_has_calls([call("revenue"), call("growth_factor")])
            mock_factory.create_calculation_node.assert_called_once_with(
                name, [mock_revenue, mock_factor], operation_type
            )
            graph.add_node.assert_called_once_with(mock_result_node)
            assert result == mock_result_node
    
    def test_add_calculation_division(self, engine, graph):
        """Test adding a division calculation node."""
        # Setup
        name = "profit_margin"
        input_names = ["profit", "revenue"]
        operation_type = "division"
        
        # Mock input nodes
        mock_profit = Mock(spec=Node)
        mock_revenue = Mock(spec=Node)
        graph.get_node.side_effect = lambda x: {"profit": mock_profit, "revenue": mock_revenue}.get(x)
        
        # Mock result node
        mock_result_node = Mock(spec=DivisionCalculationNode)
        
        # Mock NodeFactory
        with patch('fin_statement_model.core.calculation_engine.NodeFactory') as mock_factory:
            mock_factory.create_calculation_node.return_value = mock_result_node
            
            # Execute
            result = engine.add_calculation(name, input_names, operation_type)
            
            # Verify
            graph.get_node.assert_has_calls([call("profit"), call("revenue")])
            mock_factory.create_calculation_node.assert_called_once_with(
                name, [mock_profit, mock_revenue], operation_type
            )
            graph.add_node.assert_called_once_with(mock_result_node)
            assert result == mock_result_node
    
    def test_add_calculation_custom_params(self, engine, graph):
        """Test adding a calculation node with custom parameters."""
        # Setup
        name = "weighted_average"
        input_names = ["score1", "score2", "score3"]
        operation_type = "weighted_average"
        weights = [0.5, 0.3, 0.2]
        
        # Mock input nodes
        mock_score1 = Mock(spec=Node)
        mock_score2 = Mock(spec=Node)
        mock_score3 = Mock(spec=Node)
        graph.get_node.side_effect = lambda x: {
            "score1": mock_score1, "score2": mock_score2, "score3": mock_score3
        }.get(x)
        
        # Mock result node
        mock_result_node = Mock(spec=CalculationNode)
        
        # Mock NodeFactory
        with patch('fin_statement_model.core.calculation_engine.NodeFactory') as mock_factory:
            mock_factory.create_calculation_node.return_value = mock_result_node
            
            # Execute
            result = engine.add_calculation(name, input_names, operation_type, weights=weights)
            
            # Verify
            graph.get_node.assert_has_calls([call("score1"), call("score2"), call("score3")])
            mock_factory.create_calculation_node.assert_called_once_with(
                name, [mock_score1, mock_score2, mock_score3], operation_type, weights=weights
            )
            graph.add_node.assert_called_once_with(mock_result_node)
            assert result == mock_result_node
    
    def test_add_calculation_missing_input(self, engine, graph):
        """Test adding a calculation with a missing input node."""
        # Setup
        name = "profit"
        input_names = ["revenue", "nonexistent_node"]
        operation_type = "subtraction"
        
        # Mock only one input node exists
        mock_revenue = Mock(spec=Node)
        graph.get_node.side_effect = lambda x: {"revenue": mock_revenue}.get(x)
        
        # Execute and verify
        with pytest.raises(ValueError) as exc_info:
            engine.add_calculation(name, input_names, operation_type)
        assert "Input node 'nonexistent_node' not found in graph" in str(exc_info.value)
    
    def test_add_metric_formula_based(self, engine, graph):
        """Test adding a metric calculation node with a formula."""
        # Setup
        metric_name = "gross_margin"
        
        # Mock METRIC_DEFINITIONS
        metric_def = {
            "inputs": ["gross_profit", "revenue"],
            "formula": "gross_profit / revenue",
            "description": "Gross profit as a percentage of revenue"
        }
        
        # Mock input nodes
        mock_gross_profit = Mock(spec=Node)
        mock_revenue = Mock(spec=Node)
        graph.get_node.side_effect = lambda x: {
            "gross_profit": mock_gross_profit, "revenue": mock_revenue
        }.get(x)
        
        # Mock result node
        mock_result_node = Mock(spec=MetricCalculationNode)
        
        # Patch dependencies
        with patch('fin_statement_model.core.calculation_engine.METRIC_DEFINITIONS', 
                   {"gross_margin": metric_def}), \
             patch('fin_statement_model.core.calculation_engine.NodeFactory') as mock_factory:
            
            mock_factory.create_metric_node.return_value = mock_result_node
            
            # Execute
            result = engine.add_metric(metric_name)
            
            # Verify
            graph.get_node.assert_has_calls([call("gross_profit"), call("revenue")])
            mock_factory.create_metric_node.assert_called_once()
            # We can't verify the exact formula function as it's created dynamically
            assert mock_factory.create_metric_node.call_args[0][0] == metric_name
            assert mock_factory.create_metric_node.call_args[0][1] == [mock_gross_profit, mock_revenue]
            assert mock_factory.create_metric_node.call_args[0][3] == "Gross profit as a percentage of revenue"
            graph.add_node.assert_called_once_with(mock_result_node)
            assert result == mock_result_node
    
    def test_add_metric_custom_name(self, engine, graph):
        """Test adding a metric with a custom node name."""
        # Setup
        metric_name = "gross_margin"
        node_name = "custom_gross_margin"
        
        # Mock METRIC_DEFINITIONS
        metric_def = {
            "inputs": ["gross_profit", "revenue"],
            "formula": "gross_profit / revenue",
            "description": "Gross profit as a percentage of revenue"
        }
        
        # Mock input nodes
        mock_gross_profit = Mock(spec=Node)
        mock_revenue = Mock(spec=Node)
        graph.get_node.side_effect = lambda x: {
            "gross_profit": mock_gross_profit, "revenue": mock_revenue
        }.get(x)
        
        # Mock result node
        mock_result_node = Mock(spec=MetricCalculationNode)
        
        # Patch dependencies
        with patch('fin_statement_model.core.calculation_engine.METRIC_DEFINITIONS', 
                   {"gross_margin": metric_def}), \
             patch('fin_statement_model.core.calculation_engine.NodeFactory') as mock_factory:
            
            mock_factory.create_metric_node.return_value = mock_result_node
            
            # Execute
            result = engine.add_metric(metric_name, node_name)
            
            # Verify
            assert mock_factory.create_metric_node.call_args[0][0] == node_name
            graph.add_node.assert_called_once_with(mock_result_node)
            assert result == mock_result_node
    
    def test_add_metric_missing_metric(self, engine, graph):
        """Test adding a non-existent metric."""
        # Setup
        metric_name = "nonexistent_metric"
        
        # Patch dependencies
        with patch('fin_statement_model.core.calculation_engine.METRIC_DEFINITIONS', {}):
            # Execute and verify
            with pytest.raises(ValueError) as exc_info:
                engine.add_metric(metric_name)
            assert f"Metric '{metric_name}' not found in metric definitions" in str(exc_info.value)
    
    def test_add_metric_missing_input(self, engine, graph):
        """Test adding a metric with missing input nodes."""
        # Setup
        metric_name = "gross_margin"
        
        # Mock METRIC_DEFINITIONS
        metric_def = {
            "inputs": ["gross_profit", "revenue"],
            "formula": "gross_profit / revenue"
        }
        
        # Mock only one input node exists
        mock_gross_profit = Mock(spec=Node)
        graph.get_node.side_effect = lambda x: {"gross_profit": mock_gross_profit}.get(x)
        
        # Patch dependencies
        with patch('fin_statement_model.core.calculation_engine.METRIC_DEFINITIONS', 
                   {"gross_margin": metric_def}):
            # Execute and verify
            with pytest.raises(ValueError) as exc_info:
                engine.add_metric(metric_name)
            assert "Required input 'revenue' for metric 'gross_margin' not found in graph" in str(exc_info.value)
    
    def test_add_metric_invalid_definition(self, engine, graph):
        """Test adding a metric with an invalid definition."""
        # Setup
        metric_name = "invalid_metric"
        
        # Mock METRIC_DEFINITIONS with invalid metric (no formula or function)
        metric_def = {
            "inputs": ["value1", "value2"],
            "description": "Invalid metric"
        }
        
        # Patch dependencies
        with patch('fin_statement_model.core.calculation_engine.METRIC_DEFINITIONS', 
                   {"invalid_metric": metric_def}):
            # Execute and verify
            with pytest.raises(ValueError) as exc_info:
                engine.add_metric(metric_name)
            assert "Metric 'invalid_metric' definition is invalid" in str(exc_info.value)
    
    def test_calculate(self, engine, graph):
        """Test calculating a node value."""
        # Setup
        node_name = "profit"
        period = "2022"
        expected_result = 1000.0
        
        # Mock graph.calculate to return our expected result
        graph.calculate.return_value = expected_result
        
        # Execute
        result = engine.calculate(node_name, period)
        
        # Verify
        graph.calculate.assert_called_once_with(node_name, period)
        assert result == expected_result
    
    def test_calculate_all_nodes(self, engine, graph):
        """Test calculating all nodes for a period."""
        # Setup
        period = "2022"
        expected_results = {
            "revenue": 5000.0,
            "expenses": 4000.0,
            "profit": 1000.0
        }
        
        # Mock graph.calculate to return our expected results
        graph.calculate.return_value = expected_results
        
        # Execute
        results = engine.calculate(period=period)
        
        # Verify
        graph.calculate.assert_called_once_with(None, period)
        assert results == expected_results
    
    def test_calculate_all_periods(self, engine, graph):
        """Test calculating a node for all periods."""
        # Setup
        node_name = "profit"
        expected_results = {
            "2021": 800.0,
            "2022": 1000.0,
            "2023": 1200.0
        }
        
        # Mock graph.calculate to return our expected results
        graph.calculate.return_value = expected_results
        
        # Execute
        results = engine.calculate(node_name=node_name)
        
        # Verify
        graph.calculate.assert_called_once_with(node_name, None)
        assert results == expected_results
    
    def test_recalculate_all(self, engine, graph):
        """Test recalculating all nodes for all periods."""
        # Setup
        periods = ["2021", "2022", "2023"]
        
        # Mock graph methods
        mock_node1 = Mock(spec=Node)
        mock_node2 = Mock(spec=Node)
        graph.periods = periods
        graph.topological_sort.return_value = ["node1", "node2"]
        graph.get_node.side_effect = lambda x: {"node1": mock_node1, "node2": mock_node2}.get(x)
        
        # Execute
        engine.recalculate_all()
        
        # Verify
        graph.clear_all_caches.assert_called_once()
        graph.topological_sort.assert_called_once()
        
        # Each node should be calculated for each period
        assert mock_node1.calculate.call_count == 3
        assert mock_node2.calculate.call_count == 3
        mock_node1.calculate.assert_has_calls([call("2021"), call("2022"), call("2023")])
        mock_node2.calculate.assert_has_calls([call("2021"), call("2022"), call("2023")])
    
    def test_recalculate_all_custom_periods(self, engine, graph):
        """Test recalculating with custom periods list."""
        # Setup
        periods = ["2022", "2023"]  # Subset of periods
        
        # Mock graph methods
        mock_node1 = Mock(spec=Node)
        mock_node2 = Mock(spec=Node)
        graph.periods = ["2021", "2022", "2023", "2024"]  # Full list of periods
        graph.topological_sort.return_value = ["node1", "node2"]
        graph.get_node.side_effect = lambda x: {"node1": mock_node1, "node2": mock_node2}.get(x)
        
        # Execute
        engine.recalculate_all(periods)
        
        # Verify
        # Only the specified periods should be calculated
        assert mock_node1.calculate.call_count == 2
        assert mock_node2.calculate.call_count == 2
        mock_node1.calculate.assert_has_calls([call("2022"), call("2023")])
        mock_node2.calculate.assert_has_calls([call("2022"), call("2023")])
    
    def test_recalculate_all_with_error(self, engine, graph):
        """Test recalculating with an error in one calculation."""
        # Setup
        periods = ["2021", "2022"]
        
        # Mock graph methods
        mock_node1 = Mock(spec=Node)
        mock_node2 = Mock(spec=Node)
        # Make the first call to node1.calculate raise an error
        mock_node1.calculate.side_effect = [ValueError("Invalid period"), None]
        
        graph.periods = periods
        graph.topological_sort.return_value = ["node1", "node2"]
        graph.get_node.side_effect = lambda x: {"node1": mock_node1, "node2": mock_node2}.get(x)
        
        # Execute - should not raise exception
        engine.recalculate_all()
        
        # Verify - should continue with other calculations
        assert mock_node1.calculate.call_count == 2
        assert mock_node2.calculate.call_count == 2
    
    def test_get_available_operations(self, engine):
        """Test getting available calculation operations."""
        # Setup
        expected_operations = {
            "addition": "Adds all input values",
            "subtraction": "Subtracts from first value"
        }
        
        # Patch CalculationStrategyRegistry
        with patch('fin_statement_model.core.calculation_engine.CalculationStrategyRegistry') as mock_registry:
            mock_registry.list_strategies.return_value = expected_operations
            
            # Execute
            result = engine.get_available_operations()
            
            # Verify
            mock_registry.list_strategies.assert_called_once()
            assert result == expected_operations
    
    def test_change_calculation_strategy(self, engine, graph):
        """Test changing a node's calculation strategy."""
        # Setup
        node_name = "profit_margin"
        new_strategy_name = "weighted_average"
        kwargs = {"weights": [0.6, 0.4]}
        
        # Mock node
        mock_node = Mock(spec=StrategyCalculationNode)
        graph.get_node.return_value = mock_node
        
        # Mock strategy
        mock_strategy = Mock()
        
        # Patch CalculationStrategyRegistry
        with patch('fin_statement_model.core.calculation_engine.CalculationStrategyRegistry') as mock_registry:
            mock_registry.get_strategy.return_value = mock_strategy
            
            # Execute
            engine.change_calculation_strategy(node_name, new_strategy_name, **kwargs)
            
            # Verify
            graph.get_node.assert_called_once_with(node_name)
            mock_registry.get_strategy.assert_called_once_with(new_strategy_name, **kwargs)
            mock_node.set_strategy.assert_called_once_with(mock_strategy)
            mock_node.clear_cache.assert_called_once()
    
    def test_change_calculation_strategy_node_not_found(self, engine, graph):
        """Test changing strategy for a non-existent node."""
        # Setup
        node_name = "nonexistent_node"
        new_strategy_name = "weighted_average"
        
        # Mock node not found
        graph.get_node.return_value = None
        
        # Execute and verify
        with pytest.raises(ValueError) as exc_info:
            engine.change_calculation_strategy(node_name, new_strategy_name)
        assert f"Node '{node_name}' not found in graph" in str(exc_info.value)
    
    def test_change_calculation_strategy_wrong_node_type(self, engine, graph):
        """Test changing strategy for a node that's not a StrategyCalculationNode."""
        # Setup
        node_name = "simple_node"
        new_strategy_name = "weighted_average"
        
        # Mock node with wrong type
        mock_node = Mock(spec=Node)  # Not a StrategyCalculationNode
        graph.get_node.return_value = mock_node
        
        # Execute and verify
        with pytest.raises(ValueError) as exc_info:
            engine.change_calculation_strategy(node_name, new_strategy_name)
        assert f"Node '{node_name}' is not a StrategyCalculationNode" in str(exc_info.value)
    
    def test_add_metric_formula_evaluation_error(self, engine, graph):
        """Test adding a metric with a formula that causes an evaluation error."""
        # Setup
        metric_name = "problematic_metric"
        
        # Mock METRIC_DEFINITIONS with a formula that will cause an evaluation error
        metric_def = {
            "inputs": ["value1", "value2"],
            "formula": "value1 / value2",  # Will cause division by zero when value2 is 0
            "description": "A metric that will cause an evaluation error"
        }
        
        # Mock input nodes to return values that will cause an error
        mock_value1 = Mock(spec=Node)
        mock_value1.calculate.return_value = 10.0
        
        mock_value2 = Mock(spec=Node)
        mock_value2.calculate.return_value = 0.0  # Will cause division by zero
        
        graph.get_node.side_effect = lambda x: {
            "value1": mock_value1, "value2": mock_value2
        }.get(x)
        
        # Mock result node
        mock_result_node = Mock(spec=MetricCalculationNode)
        
        # Patch dependencies
        with patch('fin_statement_model.core.calculation_engine.METRIC_DEFINITIONS', 
                   {metric_name: metric_def}), \
             patch('fin_statement_model.core.calculation_engine.NodeFactory') as mock_factory:
            
            mock_factory.create_metric_node.return_value = mock_result_node
            
            # Execute
            result = engine.add_metric(metric_name)
            
            # Verify
            graph.get_node.assert_has_calls([call("value1"), call("value2")])
            mock_factory.create_metric_node.assert_called_once()
            graph.add_node.assert_called_once_with(mock_result_node)
            
            # Now we need to verify that the formula_func handles evaluation errors
            # Extract the formula function from the call
            formula_func = mock_factory.create_metric_node.call_args[0][2]
            
            # Test that it raises ValueError with the expected message pattern
            with pytest.raises(ValueError) as excinfo:
                formula_func(10.0, 0.0)  # This should cause a division by zero error
            
            assert "Error evaluating formula" in str(excinfo.value)
            assert "division by zero" in str(excinfo.value)
    
    def test_recalculate_all_with_general_exception(self, engine, graph):
        """Test recalculating with a non-ValueError exception in calculations."""
        # Setup
        periods = ["2021", "2022"]
        
        # Mock graph methods
        mock_node1 = Mock(spec=Node)
        mock_node2 = Mock(spec=Node)
        
        # Make node1.calculate raise a non-ValueError exception for the first period
        mock_node1.calculate.side_effect = [
            RuntimeError("Some unexpected error"),  # First call raises RuntimeError
            None  # Second call succeeds
        ]
        
        graph.periods = periods
        graph.topological_sort.return_value = ["node1", "node2"]
        graph.get_node.side_effect = lambda x: {"node1": mock_node1, "node2": mock_node2}.get(x)
        
        # Execute - should not raise exception and continue with other calculations
        with patch('fin_statement_model.core.calculation_engine.logger') as mock_logger:
            engine.recalculate_all()
            
            # Verify logger.error was called with the expected message
            mock_logger.error.assert_called_once()
            assert "Error calculating node1 for 2021" in mock_logger.error.call_args[0][0]
            assert "Some unexpected error" in mock_logger.error.call_args[0][0]
        
        # Verify - should continue with other calculations
        assert mock_node1.calculate.call_count == 2
        assert mock_node2.calculate.call_count == 2 