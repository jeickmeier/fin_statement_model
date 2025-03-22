"""Unit tests for the graph module to increase coverage.

This module contains additional test cases for the Graph class to achieve 100% code coverage.
These tests focus on edge cases and error handling not covered by the main test suite.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import (
    Node,
    FinancialStatementItemNode, 
    CalculationNode,
    AdditionCalculationNode,
    SubtractionCalculationNode, 
    MultiplicationCalculationNode,
    DivisionCalculationNode,
)
from fin_statement_model.core.errors import NodeError, GraphError, CalculationError, CircularDependencyError
from fin_statement_model.core.engine import CalculationEngine


class TestReplacingNodes:
    """Test case for replacing nodes and updating calculation nodes."""
    
    def test_replace_node(self):
        """Test replacing a node with update_calculation_nodes."""
        graph = Graph()
        
        # Add initial nodes
        revenue = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        expenses = FinancialStatementItemNode("expenses", {"2022": 600.0})
        graph.add_node(revenue)
        graph.add_node(expenses)
        
        # Create calculation node with input_names rather than relying on the nodes
        profit_node = Mock(spec=CalculationNode)
        profit_node.name = "profit"
        profit_node.input_names = ["revenue", "expenses"]
        profit_node.inputs = [revenue, expenses]
        profit_node.calculate = Mock(return_value=400.0)
        
        graph.add_node(profit_node)
        
        # Check initial value
        assert graph.calculate("profit", "2022") == 400.0
        
        # Replace revenue node with new node having higher value
        new_revenue = FinancialStatementItemNode("revenue", {"2022": 2000.0})
        
        # Update the mock to return the new calculation after replacement
        profit_node.calculate = Mock(return_value=1400.0)
        
        graph.replace_node("revenue", new_revenue)
        
        # Verify calculation node updates its inputs during replace_node
        profit_node.calculate.assert_not_called()  # Not called during replace_node
        
        # Calculation happens when we call calculate
        assert graph.calculate("profit", "2022") == 1400.0
        profit_node.calculate.assert_called_once_with("2022")


class TestTopologicalSort:
    """Test cases for topological sort with cycles."""

    def test_topological_sort_with_cycle(self):
        """Test topological sort with a cycle."""
        graph = Graph()
        
        # Create nodes with cyclic dependencies
        a_node = Mock(spec=CalculationNode)
        a_node.name = "a"
        
        b_node = Mock(spec=CalculationNode)
        b_node.name = "b"
        
        # Create a cycle: a -> b -> a
        a_node.inputs = [b_node]
        b_node.inputs = [a_node]
        
        graph.nodes = {"a": a_node, "b": b_node}
        
        # Verify cycle detection
        with pytest.raises(ValueError, match="Cycle detected"):
            graph.topological_sort()


class TestRecalculateAll:
    """Test cases for recalculate_all method with exceptions."""

    def test_recalculate_all_with_value_error(self):
        """Test recalculate_all with a node that raises ValueError."""
        graph = Graph(periods=["2022"])
        
        # Create a node that raises ValueError when calculated
        node = Mock(spec=Node)
        node.name = "error_node"
        node._cache = {}
        node.calculate.side_effect = ValueError("Test error")
        
        graph.nodes = {"error_node": node}
        
        # Should continue despite the error
        graph.recalculate_all("2022")
        
        # Verify node was attempted
        node.calculate.assert_called_once_with("2022")


class TestImportData:
    """Test cases for import_data method."""

    def test_import_data_with_periods(self):
        """Test import_data when graph already has periods."""
        graph = Graph(periods=["2021", "2022"])
        
        # Data with a period not in graph periods
        data = {"node": {"2021": 100, "2022": 200, "2023": 300}}
        
        with pytest.raises(ValueError, match="Data contains periods not in graph periods"):
            graph.import_data(data)
    
    def test_import_data_with_dict_value_error(self):
        """Test import_data with invalid dict structure."""
        graph = Graph()
        
        # Invalid structure - value is not a dict
        invalid_data = {"node": "not_a_dict"}
        
        with pytest.raises(ValueError, match="Invalid data format"):
            graph.import_data(invalid_data)
    
    def test_import_data_with_value_type_error(self):
        """Test import_data with invalid value type."""
        graph = Graph()
        
        # Invalid value type - not a number
        invalid_data = {"node": {"2022": "not_a_number"}}
        
        with pytest.raises(ValueError, match="Invalid value for node"):
            graph.import_data(invalid_data)
            
    def test_import_data_with_existing_node(self):
        """Test import_data with existing node."""
        graph = Graph()
        
        # Create the node first
        node = FinancialStatementItemNode("existing_node", {})
        graph.add_node(node)
        
        # Then import data for it
        data = {"existing_node": {"2022": 100}}
        graph.import_data(data)
        
        # Verify value was set
        assert graph.calculate("existing_node", "2022") == 100


class TestToDataFrame:
    """Test cases for to_dataframe method."""

    def test_to_dataframe_with_missing_values(self):
        """Test to_dataframe with nodes missing values for some periods."""
        graph = Graph(periods=["2021", "2022", "2023"])
        
        # Add node with incomplete period data
        node = FinancialStatementItemNode("node", {"2021": 100, "2023": 300})
        graph.add_node(node)
        
        # Generate dataframe
        df = graph.to_dataframe()
        
        # Check that missing period has NaN
        assert pd.isna(df.loc["node", "2022"])
        assert df.loc["node", "2021"] == 100
        assert df.loc["node", "2023"] == 300


class TestGetCalculationNodes:
    """Test cases for get_calculation_nodes method."""

    def test_get_calculation_nodes(self):
        """Test get_calculation_nodes."""
        graph = Graph()
        
        # Create a mock node with has_calculation method
        regular_node = Mock(spec=Node)
        regular_node.name = "regular"
        regular_node.has_calculation = Mock(return_value=False)
        
        calc_node = Mock(spec=Node)
        calc_node.name = "calculation"
        calc_node.has_calculation = Mock(return_value=True)
        
        # Add nodes to graph
        graph.nodes = {
            "regular": regular_node,
            "calculation": calc_node
        }
        
        # Get calculation nodes
        calc_nodes = graph.get_calculation_nodes()
        
        # Only calculation node should be returned
        assert calc_nodes == ["calculation"]
        assert "regular" not in calc_nodes


class TestGetDependencies:
    """Test cases for get_dependencies method."""

    def test_get_dependencies_node_error(self):
        """Test get_dependencies with a node that doesn't exist."""
        graph = Graph()
        
        # Should raise NodeError for non-existent node
        with pytest.raises(NodeError, match="does not exist"):
            graph.get_dependencies("nonexistent_node")
    
    def test_get_dependencies_node_no_inputs(self):
        """Test get_dependencies for a node without inputs."""
        graph = Graph()
        
        # Create a node without 'inputs' attribute
        node = Mock(spec=Node)
        node.name = "basic_node"
        
        # Add to graph
        graph.nodes = {"basic_node": node}
        
        # Should return empty list
        assert graph.get_dependencies("basic_node") == []


class TestClear:
    """Test cases for clear method with calculation engine."""

    def test_clear_with_calculation_engine(self):
        """Test clear method with calculation engine."""
        graph = Graph()
        
        # Mock calculation engine
        engine = Mock(spec=CalculationEngine)
        graph._calculation_engine = engine
        
        # Clear graph
        graph.clear()
        
        # Verify engine reset was called
        engine.reset.assert_called_once()
        
    def test_clear_without_calculation_engine(self):
        """Test clear method without calculation engine."""
        graph = Graph()
        graph.nodes = {"node": Mock()}
        graph._periods = ["2022"]
        
        # Clear graph
        graph.clear()
        
        # Verify graph is cleared
        assert len(graph.nodes) == 0
        assert len(graph._periods) == 0
        
    @patch('logging.getLogger')    
    def test_clear_with_failing_calculation_engine(self, mock_get_logger):
        """Test clear with a calculation engine that raises an exception."""
        graph = Graph()
        
        # Mock logger
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        # Mock calculation engine with reset that raises an exception
        engine = Mock(spec=CalculationEngine)
        engine.reset.side_effect = Exception("Error resetting engine")
        graph._calculation_engine = engine
        
        # Clear graph should still succeed (exception is caught)
        graph.clear()
        
        # Verify nodes and periods are cleared
        assert len(graph.nodes) == 0
        assert len(graph._periods) == 0


class TestSetValue:
    """Test cases for set_value method with calculation engine."""

    def test_set_value_with_calculation_engine(self):
        """Test set_value with calculation engine."""
        graph = Graph(periods=["2022"])
        
        # Add a node
        node = FinancialStatementItemNode("node", {})
        graph.add_node(node)
        
        # Mock calculation engine
        engine = Mock(spec=CalculationEngine)
        graph._calculation_engine = engine
        
        # Set value
        graph.set_value("node", "2022", 100)
        
        # Verify engine cache cleared
        engine.clear_cache.assert_called_once()
        
    @patch('logging.getLogger')
    def test_set_value_with_failing_calculation_engine(self, mock_get_logger):
        """Test set_value with a calculation engine that raises an exception."""
        graph = Graph(periods=["2022"])
        
        # Mock logger
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        # Create and add a real node, not a mock
        node = FinancialStatementItemNode("node", {})
        graph.add_node(node)
        
        # Mock calculation engine with clear_cache that raises an exception
        engine = Mock(spec=CalculationEngine)
        engine.clear_cache.side_effect = Exception("Error clearing cache")
        graph._calculation_engine = engine
        
        # Set value should still succeed (exception is caught)
        graph.set_value("node", "2022", 100)
        
        # Verify the node value is set correctly
        # Since this is a real FinancialStatementItemNode, we can get the value directly
        assert node.values["2022"] == 100


class TestRemoveNode:
    """Test cases for remove_node method with calculation engine."""

    def test_remove_node_with_calculation_engine(self):
        """Test remove_node with calculation engine."""
        graph = Graph()
        
        # Add a node
        node = FinancialStatementItemNode("node", {})
        graph.add_node(node)
        
        # Mock calculation engine
        engine = Mock(spec=CalculationEngine)
        graph._calculation_engine = engine
        
        # Remove node
        graph.remove_node("node")
        
        # Verify engine cache cleared
        engine.clear_cache.assert_called_once()
        
    @patch('logging.getLogger')
    def test_remove_node_with_failing_calculation_engine(self, mock_get_logger):
        """Test remove_node with a calculation engine that raises an exception."""
        graph = Graph()
        
        # Mock logger
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        # Add a node
        node = FinancialStatementItemNode("node", {})
        graph.add_node(node)
        
        # Mock calculation engine with clear_cache that raises an exception
        engine = Mock(spec=CalculationEngine)
        engine.clear_cache.side_effect = Exception("Error clearing cache")
        graph._calculation_engine = engine
        
        # Remove node should still succeed (exception is caught)
        graph.remove_node("node")
        
        # Verify node was removed despite the engine exception
        assert "node" not in graph.nodes


class TestExceptionHandling:
    """Test cases for exception handling in get_dependency_graph."""
    
    def test_get_dependency_graph_with_node_error(self):
        """Test get_dependency_graph handling NodeError."""
        graph = Graph()
        
        # Create a node that raises NodeError during dependency check
        problematic_node = Mock(spec=CalculationNode)
        problematic_node.name = "problematic"
        # This will create a NodeError when hasattr checks for inputs
        type(problematic_node).__getattribute__ = Mock(side_effect=NodeError("Test error", "problematic"))
        
        normal_node = Mock(spec=Node)
        normal_node.name = "normal"
        normal_node.inputs = []
        
        # Add nodes to graph
        graph.nodes = {
            "problematic": problematic_node,
            "normal": normal_node
        }
        
        # Get dependency graph should handle the error
        dependencies = graph.get_dependency_graph()
        
        # Problematic node should have empty dependencies
        assert dependencies["problematic"] == []
        assert dependencies["normal"] == []


class TestValidate:
    """Test cases for validate method."""
    
    def test_validate_with_cycles(self):
        """Test validate with cycles detected."""
        graph = Graph()
        
        # Create nodes with cyclic dependencies
        a_node = Mock(spec=CalculationNode)
        a_node.name = "a"
        
        b_node = Mock(spec=CalculationNode)
        b_node.name = "b"
        
        # Create a cycle: a -> b -> a
        a_node.inputs = [b_node]
        b_node.inputs = [a_node]
        
        # Add nodes to graph
        graph.nodes = {"a": a_node, "b": b_node}
        
        # Mock detect_cycles to return a cycle
        with patch.object(graph, 'detect_cycles', return_value=[["a", "b", "a"]]):
            errors = graph.validate()
            
            # Verify errors include the cycle
            assert len(errors) == 1
            assert "Circular dependency detected: a -> b -> a" in errors[0] 