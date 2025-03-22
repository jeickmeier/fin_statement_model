"""Unit tests for the graph module.

This module contains test cases for the Graph class and its methods.
Each test class focuses on testing specific functionality of the graph.
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
from fin_statement_model.core.errors import NodeError, GraphError, CalculationError
from fin_statement_model.core.engine import CalculationEngine

class TestGraphInitialization:
    """Test cases for Graph initialization and basic operations."""

    def test_initialization(self):
        """Test basic graph initialization."""
        graph = Graph()
        assert isinstance(graph.nodes, dict)
        assert len(graph.nodes) == 0
        assert graph._periods == []

    def test_initialization_with_periods(self):
        """Test graph initialization with periods."""
        periods = ["2021", "2022", "2023"]
        graph = Graph(periods)
        assert graph._periods == periods

    @patch('fin_statement_model.core.engine.CalculationEngine')
    def test_set_calculation_engine(self, mock_engine_class):
        """Test setting calculation engine."""
        graph = Graph()
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        graph.set_calculation_engine(mock_engine)
        assert graph._calculation_engine == mock_engine
        mock_engine.set_graph.assert_called_once_with(graph)

    def test_set_calculation_engine_invalid(self):
        """Test setting invalid calculation engine."""
        graph = Graph()
        with pytest.raises(TypeError, match="Expected CalculationEngine instance"):
            graph.set_calculation_engine("not_an_engine")

    def test_initialization_with_invalid_periods(self):
        """Test graph initialization with invalid periods."""
        with pytest.raises(TypeError):
            Graph(periods="not_a_list")
        with pytest.raises(ValueError):
            Graph(periods=["2022", "2021"])  # Unsorted periods

class TestGraphNodeOperations:
    """Test cases for node operations in the graph."""

    def setup_method(self):
        """Setup test environment before each test."""
        self.graph = Graph()
        self.revenue_node = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        self.expenses_node = FinancialStatementItemNode("expenses", {"2022": 600.0})

    def test_add_node(self):
        """Test adding nodes to the graph."""
        self.graph.add_node(self.revenue_node)
        assert self.revenue_node.name in self.graph.nodes
        assert self.graph.nodes[self.revenue_node.name] == self.revenue_node

    def test_add_duplicate_node(self):
        """Test adding a node with duplicate name."""
        self.graph.add_node(self.revenue_node)
        new_revenue = FinancialStatementItemNode("revenue", {"2022": 2000.0})
        self.graph.add_node(new_revenue)
        assert self.graph.nodes["revenue"] == new_revenue

    def test_get_node(self):
        """Test retrieving nodes from the graph."""
        self.graph.add_node(self.revenue_node)
        node = self.graph.get_node("revenue")
        assert node == self.revenue_node
        assert self.graph.get_node("nonexistent") is None

    def test_remove_node(self):
        """Test removing nodes from the graph."""
        self.graph.add_node(self.revenue_node)
        self.graph.remove_node("revenue")
        assert "revenue" not in self.graph.nodes

    def test_remove_nonexistent_node(self):
        """Test removing a nonexistent node."""
        with pytest.raises(NodeError):
            self.graph.remove_node("nonexistent")

    def test_clear(self):
        """Test clearing all nodes from the graph."""
        self.graph.add_node(self.revenue_node)
        self.graph.add_node(self.expenses_node)
        self.graph.clear()
        assert len(self.graph.nodes) == 0
        assert self.graph._periods == []

class TestGraphCalculations:
    """Test cases for graph calculations and dependencies."""

    def setup_method(self):
        """Setup test environment before each test."""
        self.graph = Graph()
        self.revenue_node = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        self.expenses_node = FinancialStatementItemNode("expenses", {"2022": 600.0})
        self.graph.add_node(self.revenue_node)
        self.graph.add_node(self.expenses_node)

    def test_calculate(self):
        """Test calculating node values."""
        assert self.graph.calculate("revenue", "2022") == 1000.0
        assert self.graph.calculate("expenses", "2022") == 600.0

    def test_calculate_nonexistent_node(self):
        """Test calculating value for nonexistent node."""
        with pytest.raises(ValueError, match="Node 'nonexistent' not found"):
            self.graph.calculate("nonexistent", "2022")

    def test_calculate_invalid_period(self):
        """Test calculating value for invalid period."""
        # Should return 0.0 for missing periods
        assert self.graph.calculate("revenue", "2023") == 0.0

    @patch('fin_statement_model.core.engine.CalculationEngine')
    def test_calculate_with_calculation_engine(self, mock_engine_class):
        """Test calculating values with calculation engine."""
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.calculate.return_value = 500.0
        self.graph.set_calculation_engine(mock_engine)
        
        result = self.graph.calculate("revenue", "2022")
        assert result == 500.0
        mock_engine.calculate.assert_called_once_with("revenue", "2022")

    def test_topological_sort(self):
        """Test topological sorting of nodes."""
        # Create calculation nodes
        profit_node = SubtractionCalculationNode("profit", [self.revenue_node, self.expenses_node])
        margin_node = DivisionCalculationNode("margin", [profit_node, self.revenue_node])
        
        self.graph.add_node(profit_node)
        self.graph.add_node(margin_node)
        
        sorted_nodes = self.graph.topological_sort()
        assert "revenue" in sorted_nodes
        assert "expenses" in sorted_nodes
        assert "profit" in sorted_nodes
        assert "margin" in sorted_nodes
        assert sorted_nodes.index("revenue") < sorted_nodes.index("profit")
        assert sorted_nodes.index("expenses") < sorted_nodes.index("profit")
        assert sorted_nodes.index("profit") < sorted_nodes.index("margin")

    def test_detect_cycles(self):
        """Test cycle detection in the graph."""
        # Create a cycle: revenue -> profit -> margin -> revenue
        profit_node = SubtractionCalculationNode("profit", [self.revenue_node, self.expenses_node])
        margin_node = DivisionCalculationNode("margin", [profit_node, self.revenue_node])
        
        # Add nodes to graph
        self.graph.add_node(profit_node)
        self.graph.add_node(margin_node)
        
        # Create cycle by making revenue depend on margin
        self.revenue_node.inputs = [margin_node]
        
        # Detect cycles
        cycles = self.graph.detect_cycles()
        assert len(cycles) > 0
        assert any("revenue" in cycle and "profit" in cycle and "margin" in cycle for cycle in cycles)

    def test_validate(self):
        """Test graph validation."""
        # Create a valid graph
        profit_node = SubtractionCalculationNode("profit", [self.revenue_node, self.expenses_node])
        self.graph.add_node(profit_node)
        errors = self.graph.validate()
        assert len(errors) == 0

        # Create an invalid graph with missing dependency
        invalid_node = SubtractionCalculationNode("invalid", [self.revenue_node, FinancialStatementItemNode("missing", {})])
        self.graph.add_node(invalid_node)
        errors = self.graph.validate()
        assert len(errors) > 0
        assert any("depends on non-existent node" in error for error in errors)

class TestGraphDataOperations:
    """Test cases for graph data operations."""

    def setup_method(self):
        """Setup test environment before each test."""
        self.graph = Graph(periods=["2022", "2023"])
        self.test_data = {
            "revenue": {"2022": 1000.0, "2023": 1100.0},
            "expenses": {"2022": 600.0, "2023": 650.0}
        }

    def test_import_data(self):
        """Test importing data into the graph."""
        self.graph.import_data(self.test_data)
        assert "revenue" in self.graph.nodes
        assert "expenses" in self.graph.nodes
        assert self.graph.calculate("revenue", "2022") == 1000.0
        assert self.graph.calculate("expenses", "2023") == 650.0

    def test_import_data_invalid(self):
        """Test importing invalid data."""
        invalid_data = {
            "revenue": "not_a_dict",
            "expenses": {"2022": "not_a_number"}
        }
        with pytest.raises(ValueError):
            self.graph.import_data(invalid_data)

    def test_export_data(self):
        """Test exporting data from the graph."""
        self.graph.import_data(self.test_data)
        exported_data = self.graph.export_data()
        assert exported_data == self.test_data

    def test_to_dataframe(self):
        """Test converting graph data to DataFrame."""
        self.graph.import_data(self.test_data)
        df = self.graph.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert "revenue" in df.index
        assert "expenses" in df.index
        assert "2022" in df.columns
        assert "2023" in df.columns
        assert df.loc["revenue", "2022"] == 1000.0
        assert df.loc["expenses", "2023"] == 650.0

    def test_to_dataframe_empty_graph(self):
        """Test converting empty graph to DataFrame."""
        df = self.graph.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert len(df.columns) == 0

class TestGraphPeriodOperations:
    """Test cases for period-related operations."""

    def setup_method(self):
        """Setup test environment before each test."""
        self.periods = ["2021", "2022", "2023"]
        self.graph = Graph(self.periods)

    def test_periods_property(self):
        """Test accessing periods property."""
        assert self.graph.periods == sorted(self.periods)

    def test_set_value(self):
        """Test setting node values for specific periods."""
        self.graph.add_node(FinancialStatementItemNode("revenue", {}))
        self.graph.set_value("revenue", "2022", 1000.0)
        assert self.graph.calculate("revenue", "2022") == 1000.0

    def test_set_value_nonexistent_node(self):
        """Test setting value for nonexistent node."""
        with pytest.raises(NodeError, match="Node 'nonexistent' does not exist"):
            self.graph.set_value("nonexistent", "2022", 1000.0)

    def test_set_value_invalid_period(self):
        """Test setting value for invalid period."""
        self.graph.add_node(FinancialStatementItemNode("revenue", {}))
        with pytest.raises(ValueError, match="Period '2024' not in graph periods"):
            self.graph.set_value("revenue", "2024", 1000.0)

    def test_recalculate_all(self):
        """Test recalculating all nodes for a period."""
        revenue_node = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        expenses_node = FinancialStatementItemNode("expenses", {"2022": 600.0})
        profit_node = SubtractionCalculationNode("profit", [revenue_node, expenses_node])
        
        self.graph.add_node(revenue_node)
        self.graph.add_node(expenses_node)
        self.graph.add_node(profit_node)
        
        self.graph.recalculate_all("2022")
        assert self.graph.calculate("profit", "2022") == 400.0

    def test_recalculate_all_invalid_period(self):
        """Test recalculating all nodes for invalid period."""
        with pytest.raises(ValueError, match="Period '2024' not in graph periods"):
            self.graph.recalculate_all("2024")

class TestGraphDependencyOperations:
    """Test cases for dependency-related operations."""

    def setup_method(self):
        """Setup test environment before each test."""
        self.graph = Graph()
        self.revenue_node = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        self.expenses_node = FinancialStatementItemNode("expenses", {"2022": 600.0})
        self.profit_node = SubtractionCalculationNode("profit", [self.revenue_node, self.expenses_node])
        
        self.graph.add_node(self.revenue_node)
        self.graph.add_node(self.expenses_node)
        self.graph.add_node(self.profit_node)

    def test_get_dependencies(self):
        """Test getting node dependencies."""
        deps = self.graph.get_dependencies("profit")
        assert "revenue" in deps
        assert "expenses" in deps
        assert len(deps) == 2

    def test_get_dependencies_nonexistent_node(self):
        """Test getting dependencies for nonexistent node."""
        with pytest.raises(NodeError):
            self.graph.get_dependencies("nonexistent")

    def test_get_dependency_graph(self):
        """Test getting the full dependency graph."""
        deps = self.graph.get_dependency_graph()
        assert "profit" in deps
        assert "revenue" in deps
        assert "expenses" in deps
        assert len(deps["profit"]) == 2
        assert len(deps["revenue"]) == 0
        assert len(deps["expenses"]) == 0 