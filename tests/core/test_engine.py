"""Unit tests for the engine module.

This module contains test cases for the CalculationEngine class in engine.py
which is responsible for executing calculations and managing the calculation graph.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
import logging

from fin_statement_model.core.engine import (
    CalculationEngine, 
    CalculationError, 
    NodeError, 
    CircularDependencyError,
    StrategyError
)

class TestCalculationEngine:
    """Test cases for the CalculationEngine class."""

    @pytest.fixture
    def engine(self):
        """Create a CalculationEngine instance for testing."""
        return CalculationEngine()
    
    @pytest.fixture
    def mock_graph(self):
        """Create a mock graph for testing."""
        mock_graph = Mock()
        mock_graph.has_node = Mock(return_value=True)
        mock_graph.add_node = Mock()
        # Add nodes attribute to mock graph for clear_cache_with_graph test
        mock_graph.nodes = {
            "node1": Mock(clear_cache=Mock()),
            "node2": Mock()  # No clear_cache method
        }
        return mock_graph
    
    def test_init(self, engine):
        """Test engine initialization."""
        assert engine._graph is None
        assert hasattr(engine, '_strategy_registry')
        assert hasattr(engine, '_calculation_cache')
        assert engine._calculation_cache == {}
    
    def test_set_graph(self, engine, mock_graph):
        """Test setting a graph."""
        engine.set_graph(mock_graph)
        assert engine._graph == mock_graph
    
    def test_clear_cache(self, engine):
        """Test clearing the calculation cache."""
        # Setup - add something to the cache
        engine._calculation_cache = {'test_key': 'test_value'}
        
        # Execute
        engine.clear_cache()
        
        # Verify
        assert engine._calculation_cache == {}
    
    def test_clear_cache_with_graph(self, engine, mock_graph):
        """Test clearing the cache when a graph with nodes is present."""
        # Setup
        engine.set_graph(mock_graph)
        engine._calculation_cache = {'test_key': 'test_value'}
        
        # Execute
        engine.clear_cache()
        
        # Verify
        assert engine._calculation_cache == {}
        # Verify node-level cache clearing
        mock_graph.nodes["node1"].clear_cache.assert_called_once()
        # Node2 should not raise error even though it doesn't have clear_cache
        assert True  # Just check that we got here without error
    
    def test_reset(self, engine):
        """Test resetting the engine."""
        # Setup - add something to the cache
        engine._calculation_cache = {'test_key': 'test_value'}
        
        # Execute
        engine.reset()
        
        # Verify
        assert engine._calculation_cache == {}
    
    def test_add_calculation_no_graph(self, engine):
        """Test adding a calculation when no graph is set."""
        with pytest.raises(CalculationError) as exc_info:
            engine.add_calculation("test_node", ["input1"], "addition")
        
        assert "No graph assigned to calculation engine" in str(exc_info.value)
    
    def test_add_calculation_unsupported_type(self, engine, mock_graph):
        """Test adding a calculation with an unsupported type."""
        # Setup
        engine.set_graph(mock_graph)
        engine._strategy_registry.has_strategy = Mock(return_value=False)
        
        # Execute and verify
        with pytest.raises(StrategyError) as exc_info:
            engine.add_calculation("test_node", ["input1"], "unsupported_type")
        
        assert "Unsupported calculation type" in str(exc_info.value)
    
    def test_add_calculation_missing_inputs(self, engine, mock_graph):
        """Test adding a calculation with missing input nodes."""
        # Setup
        engine.set_graph(mock_graph)
        engine._strategy_registry.has_strategy = Mock(return_value=True)
        mock_graph.has_node = Mock(side_effect=lambda node_id: node_id != "missing_input")
        
        # Execute and verify
        with pytest.raises(NodeError) as exc_info:
            engine.add_calculation("test_node", ["valid_input", "missing_input"], "addition")
        
        assert "Input nodes not found" in str(exc_info.value)
        assert exc_info.value.node_id == "test_node"
    
    def test_add_calculation_success(self, engine, mock_graph):
        """Test successful addition of a calculation node."""
        # Setup
        engine.set_graph(mock_graph)
        engine._strategy_registry.has_strategy = Mock(return_value=True)
        mock_strategy = Mock()
        engine._strategy_registry.get_strategy = Mock(return_value=mock_strategy)
        
        # Mock logger to verify it's called
        with patch('fin_statement_model.core.engine.logger') as mock_logger:
            # Execute
            node_id = engine.add_calculation("test_node", ["input1", "input2"], "addition", param1="value1")
            
            # Verify logger.info was called
            mock_logger.info.assert_called_once()
            assert "Added calculation node" in mock_logger.info.call_args[0][0]
        
        # Verify
        mock_graph.add_node.assert_called_once()
        args, kwargs = mock_graph.add_node.call_args
        
        # Check that we're passing a StrategyCalculationNode object
        from fin_statement_model.core.nodes import StrategyCalculationNode
        assert isinstance(args[0], StrategyCalculationNode)
        assert args[0].name == "test_node"
        assert args[0].calculation_type == "addition"
        assert args[0].input_names == ["input1", "input2"]
        assert args[0].strategy == mock_strategy
        
        # Verify return value
        assert node_id == "test_node"
    
    def test_add_calculation_with_generic_error(self, engine, mock_graph):
        """Test handling of generic errors when adding a calculation."""
        # Setup
        engine.set_graph(mock_graph)
        engine._strategy_registry.has_strategy = Mock(return_value=True)
        engine._strategy_registry.get_strategy = Mock(side_effect=RuntimeError("Generic error"))
        
        # Execute and verify
        with patch('fin_statement_model.core.engine.logger') as mock_logger:
            with pytest.raises(CalculationError) as exc_info:
                engine.add_calculation("test_node", ["input1"], "addition")
            
            # Verify that logger.error was called
            mock_logger.error.assert_called_once()
            assert "Failed to add calculation" in mock_logger.error.call_args[0][0]
        
        # Verify the error
        assert "Failed to add calculation node" in str(exc_info.value)
        assert hasattr(exc_info.value, 'details')
        assert exc_info.value.details["calculation_type"] == "addition"
        assert "Generic error" in exc_info.value.details["error"]
    
    def test_calculate_no_graph(self, engine):
        """Test calculating when no graph is set."""
        with pytest.raises(CalculationError) as exc_info:
            engine.calculate("test_node", "2022")
        
        assert "No graph assigned to calculation engine" in str(exc_info.value)
    
    def test_calculate_node_not_found(self, engine, mock_graph):
        """Test calculating a node that doesn't exist."""
        # Setup
        engine.set_graph(mock_graph)
        mock_graph.get_node = Mock(return_value=None)
        
        # Execute and verify
        with pytest.raises(NodeError) as exc_info:
            engine.calculate("nonexistent_node", "2022")
        
        assert "Node not found" in str(exc_info.value)
    
    def test_calculate_from_cache(self, engine, mock_graph):
        """Test retrieving a calculation from cache."""
        # Setup
        engine.set_graph(mock_graph)
        mock_node = Mock()
        mock_graph.get_node = Mock(return_value=mock_node)
        
        # Pre-populate the cache
        engine._calculation_cache[("test_node", "2022")] = 100.0
        
        # Execute
        result = engine.calculate("test_node", "2022")
        
        # Verify
        assert result == 100.0
        # The node's methods should not be called since result was from cache
        mock_node.has_value.assert_not_called()
    
    def test_calculate_from_node_value(self, engine, mock_graph):
        """Test calculating using a stored node value."""
        # Setup
        engine.set_graph(mock_graph)
        mock_node = Mock()
        mock_node.has_value = Mock(return_value=True)
        mock_node.get_value = Mock(return_value=200.0)
        mock_graph.get_node = Mock(return_value=mock_node)
        
        # Execute
        result = engine.calculate("test_node", "2022")
        
        # Verify
        assert result == 200.0
        mock_node.has_value.assert_called_once_with("2022")
        mock_node.get_value.assert_called_once_with("2022")
        # Check that the result was cached
        assert engine._calculation_cache[("test_node", "2022")] == 200.0
    
    def test_calculate_using_calculation(self, engine, mock_graph):
        """Test calculating using the node's calculation."""
        # Setup
        engine.set_graph(mock_graph)
        mock_node = Mock()
        mock_node.has_value = Mock(return_value=False)
        mock_node.has_calculation = Mock(return_value=True)
        mock_graph.get_node = Mock(return_value=mock_node)
        
        # Mock _execute_calculation to return a known value
        engine._execute_calculation = Mock(return_value=300.0)
        
        # Execute
        result = engine.calculate("test_node", "2022")
        
        # Verify
        assert result == 300.0
        mock_node.has_value.assert_called_once_with("2022")
        mock_node.has_calculation.assert_called_once()
        engine._execute_calculation.assert_called_once_with(mock_node, "2022")
        # Check that the result was cached
        assert engine._calculation_cache[("test_node", "2022")] == 300.0
    
    def test_calculate_no_value_or_calculation(self, engine, mock_graph):
        """Test calculating a node with no value or calculation."""
        # Setup
        engine.set_graph(mock_graph)
        mock_node = Mock()
        mock_node.has_value = Mock(return_value=False)
        mock_node.has_calculation = Mock(return_value=False)
        mock_graph.get_node = Mock(return_value=mock_node)
        
        # Execute and verify
        with pytest.raises(CalculationError) as exc_info:
            engine.calculate("test_node", "2022")
        
        assert "Node has no value or calculation for period" in str(exc_info.value)
    
    def test_circular_dependency_detection(self, engine, mock_graph):
        """Test detection of circular dependencies during calculation."""
        # Setup
        engine.set_graph(mock_graph)
        
        # Add to the calculation stack to simulate a circular dependency
        engine._calculation_stack = ["node_a"]
        
        # Mock node
        mock_node = Mock()
        mock_graph.get_node = Mock(return_value=mock_node)
        
        # Execute and verify
        with pytest.raises(CircularDependencyError) as exc_info:
            engine.calculate("node_a", "2022")
        
        assert "Circular dependency detected" in str(exc_info.value)
        # Verify the cycle information
        assert hasattr(exc_info.value, 'cycle')
        assert exc_info.value.cycle == ["node_a", "node_a"]
    
    def test_execute_calculation(self, engine, mock_graph):
        """Test executing a calculation on a node."""
        # Setup
        engine.set_graph(mock_graph)
        
        # Create a mock node with calculation attributes
        mock_node = Mock()
        mock_node.name = "test_node"
        mock_node.get_attribute = Mock(side_effect=lambda attr, default=None: {
            "calculation_type": "addition",
            "input_nodes": ["input1", "input2"],
            "parameters": {"param1": "value1"},
            "strategy": None  # Strategy will be fetched from registry
        }.get(attr, default))
        
        # Create a mock calculation strategy
        mock_strategy = Mock()
        mock_strategy.calculate = Mock(return_value=500.0)
        engine._strategy_registry.get_strategy = Mock(return_value=mock_strategy)
        
        # Mock the calculate method to return values for input nodes
        engine.calculate = Mock(side_effect=lambda node_id, period: 
            {"input1": 200.0, "input2": 300.0}.get(node_id))
        
        # Execute
        result = engine._execute_calculation(mock_node, "2022")
        
        # Verify
        assert result == 500.0
        engine.calculate.assert_has_calls([
            call("input1", "2022"),
            call("input2", "2022")
        ])
        mock_strategy.calculate.assert_called_once_with([200.0, 300.0], {"param1": "value1"})
        mock_node.set_value.assert_called_once_with("2022", 500.0)
    
    def test_execute_calculation_no_strategy(self, engine, mock_graph):
        """Test executing a calculation with no strategy specified."""
        # Setup
        engine.set_graph(mock_graph)
        
        # Create a mock node with no strategy
        mock_node = Mock()
        mock_node.name = "test_node"
        mock_node.get_attribute = Mock(side_effect=lambda attr, default=None: {
            "calculation_type": None,
            "input_nodes": ["input1", "input2"],
            "parameters": {},
            "strategy": None
        }.get(attr, default))
        
        # Execute and verify
        with pytest.raises(StrategyError) as exc_info:
            engine._execute_calculation(mock_node, "2022")
        
        assert "No calculation strategy specified for node" in str(exc_info.value)
    
    def test_execute_calculation_with_error(self, engine, mock_graph):
        """Test handling of errors during calculation execution."""
        # Setup
        engine.set_graph(mock_graph)
        
        # Create a mock node with calculation attributes
        mock_node = Mock()
        mock_node.name = "test_node"
        mock_node.get_attribute = Mock(side_effect=lambda attr, default=None: {
            "calculation_type": "addition",
            "input_nodes": ["input1", "input2"],
            "parameters": {},
            "strategy": None
        }.get(attr, default))
        
        # Create a mock calculation strategy that raises an error
        mock_strategy = Mock()
        mock_strategy.calculate = Mock(side_effect=Exception("Calculation failed"))
        engine._strategy_registry.get_strategy = Mock(return_value=mock_strategy)
        
        # Mock the calculate method to return values for input nodes
        engine.calculate = Mock(side_effect=lambda node_id, period: 
            {"input1": 200.0, "input2": 300.0}.get(node_id))
        
        # Execute and verify with logger capture
        with patch('fin_statement_model.core.engine.logger') as mock_logger:
            with pytest.raises(CalculationError) as exc_info:
                engine._execute_calculation(mock_node, "2022")
            
            # Verify logger.error was called
            mock_logger.error.assert_called_once()
            assert "Calculation error for node" in mock_logger.error.call_args[0][0]
        
        # Verify the error details
        assert "Failed to calculate node" in str(exc_info.value)
        assert hasattr(exc_info.value, 'details')
        assert "Calculation failed" in exc_info.value.details["error"]
    
    def test_register_strategy(self, engine):
        """Test registering a calculation strategy."""
        # Setup
        # Create a real subclass of CalculationStrategy
        from fin_statement_model.calculations import CalculationStrategy
        
        class TestStrategy(CalculationStrategy):
            def calculate(self, input_values, parameters=None):
                return 42
                
        test_strategy = TestStrategy()
        
        # Patch the registry's method to avoid actual implementation
        with patch.object(engine._strategy_registry, 'register_strategy'):
            # Execute
            engine.register_strategy("custom_calculation", test_strategy)
            
            # Verify
            engine._strategy_registry.register_strategy.assert_called_once_with(
                "custom_calculation", test_strategy
            )
    
    def test_register_strategy_error(self, engine):
        """Test error handling when registering a strategy fails."""
        # Setup - mock the registry to raise an exception
        engine._strategy_registry.register_strategy = Mock(side_effect=ValueError("Invalid strategy"))
        
        # Execute and verify with logger capture
        with patch('fin_statement_model.core.engine.logger') as mock_logger:
            with pytest.raises(StrategyError) as exc_info:
                engine.register_strategy("custom_calculation", Mock())
            
            # Verify that the error is logged
            mock_logger.error.assert_called_once()
            assert "custom_calculation" in mock_logger.error.call_args[0][0]
            
            # Verify the raised exception
            assert "Failed to register calculation strategy" in str(exc_info.value)
            assert exc_info.value.strategy_type == "custom_calculation"
    
    def test_get_strategy(self, engine):
        """Test retrieving a calculation strategy."""
        # Setup
        mock_strategy = Mock()
        engine._strategy_registry.get_strategy = Mock(return_value=mock_strategy)
        
        # Execute
        strategy = engine.get_strategy("addition")
        
        # Verify
        assert strategy == mock_strategy
        engine._strategy_registry.get_strategy.assert_called_once_with("addition")
    
    def test_get_strategy_error(self, engine):
        """Test error handling when getting a strategy fails."""
        # Setup - mock the registry to raise an exception
        engine._strategy_registry.get_strategy = Mock(side_effect=ValueError("Strategy not found"))
        
        # Execute and verify with logger capture
        with patch('fin_statement_model.core.engine.logger') as mock_logger:
            with pytest.raises(StrategyError) as exc_info:
                engine.get_strategy("unknown_strategy")
            
            # Verify that the error is logged
            mock_logger.error.assert_called_once()
            assert "unknown_strategy" in mock_logger.error.call_args[0][0]
            
            # Verify the raised exception
            assert "Failed to get calculation strategy" in str(exc_info.value)
            assert exc_info.value.strategy_type == "unknown_strategy"
    
    def test_add_calculation_with_specific_error(self, engine, mock_graph):
        """Test that specific errors (StrategyError, NodeError) are re-raised in add_calculation."""
        # Setup
        engine.set_graph(mock_graph)
        
        # Make sure inputs exist
        mock_graph.has_node = Mock(return_value=True)
        # Make sure the strategy is supported
        engine._strategy_registry.has_strategy = Mock(return_value=True)
        
        # Setup a StrategyError to be raised
        strategy_error = StrategyError(
            message="Failed to add node due to strategy error",
            strategy_type="test_strategy",
            node_id="test_node"
        )
        
        # Setup a mock strategy
        mock_strategy = Mock()
        
        # Mock get_strategy to return our mock strategy
        engine._strategy_registry.get_strategy = Mock(return_value=mock_strategy)
        
        # Mock get_node to return a mock node
        mock_node = Mock()
        mock_graph.get_node = Mock(return_value=mock_node)
        
        # Mock add_node to raise our StrategyError
        mock_graph.add_node = Mock(side_effect=strategy_error)
        
        # Execute and verify that the StrategyError is re-raised
        with pytest.raises(StrategyError) as exc_info:
            engine.add_calculation("test_node", ["input1"], "test_strategy")
        
        # Verify it's the same error
        assert exc_info.value is strategy_error
    
    def test_add_calculation_with_node_error(self, engine, mock_graph):
        """Test that NodeError is re-raised in add_calculation."""
        # Setup
        engine.set_graph(mock_graph)
        # Make sure has_strategy passes
        engine._strategy_registry.has_strategy = Mock(return_value=True)
        # Make sure input checks pass
        mock_graph.has_node = Mock(return_value=True)
        
        # Setup a NodeError to be raised
        node_error = NodeError(
            message="Failed to add node due to node error",
            node_id="test_node"
        )
        
        # Setup a mock strategy
        mock_strategy = Mock()
        
        # Mock get_strategy to return our mock strategy
        engine._strategy_registry.get_strategy = Mock(return_value=mock_strategy)
        
        # Mock get_node to return a mock node
        mock_node = Mock()
        mock_graph.get_node = Mock(return_value=mock_node)
        
        # Mock add_node to raise our NodeError
        mock_graph.add_node = Mock(side_effect=node_error)
        
        # Execute and verify that the NodeError is re-raised
        with pytest.raises(NodeError) as exc_info:
            engine.add_calculation("test_node", ["input1"], "test_strategy")
        
        # Verify it's the same error
        assert exc_info.value is node_error 