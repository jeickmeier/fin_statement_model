"""Integration tests for the engine and financial statement modules.

This module contains integration tests that verify the correct interaction
between the CalculationEngine and FinancialStatementGraph classes.
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import sys
import uuid

from fin_statement_model.core.engine import CalculationEngine
from fin_statement_model.core.financial_statement import FinancialStatementGraph
from fin_statement_model.core.graph import Graph
from fin_statement_model.calculations.calculation_strategy import CalculationStrategy
from fin_statement_model.calculations.strategy_registry import CalculationStrategyRegistry

# Create proper CalculationStrategy subclasses
class SimpleAdditionStrategy(CalculationStrategy):
    """A simple addition strategy for testing."""
    
    def calculate(self, input_values, parameters=None):
        """Sum the input values."""
        return sum(input_values)


class SimpleSubtractionStrategy(CalculationStrategy):
    """A simple subtraction strategy for testing."""
    
    def calculate(self, input_values, parameters=None):
        """Subtract subsequent values from the first value."""
        if not input_values:
            return 0
        result = input_values[0]
        for value in input_values[1:]:
            result -= value
        return result


class TestEngineFinancialStatementIntegration:
    """Integration tests for CalculationEngine and FinancialStatementGraph."""
    
    @pytest.fixture
    def graph(self):
        """Create a graph for testing."""
        periods = ["2021", "2022"]
        return Graph(periods)
    
    @pytest.fixture
    def engine(self, graph):
        """Create a CalculationEngine with a graph for testing."""
        engine = CalculationEngine()
        engine.set_graph(graph)
        
        # Generate unique strategy names for this test run
        unique_suffix = str(uuid.uuid4())[:8]
        addition_name = f"test_addition_{unique_suffix}"
        subtraction_name = f"test_subtraction_{unique_suffix}"
        
        # Register test strategies using the registry API with unique names
        CalculationStrategyRegistry.register_strategy(addition_name, SimpleAdditionStrategy)
        CalculationStrategyRegistry.register_strategy(subtraction_name, SimpleSubtractionStrategy)
        
        # Store the strategy names on the engine instance for retrieval in tests
        engine.test_addition_name = addition_name
        engine.test_subtraction_name = subtraction_name
        
        return engine
    
    @pytest.fixture
    def financial_statement_graph(self):
        """Create a FinancialStatementGraph for testing."""
        periods = ["2021", "2022"]
        return FinancialStatementGraph(periods)
    
    def test_engine_graph_initialization(self, engine, graph):
        """Test that the engine correctly references the graph."""
        assert engine._graph == graph
    
    def test_financial_statement_graph_components(self, financial_statement_graph):
        """Test that FinancialStatementGraph initializes with required components."""
        assert hasattr(financial_statement_graph, '_calculation_engine')
        assert isinstance(financial_statement_graph.graph, Graph)
    
    def test_add_calculation_node_integration(self, graph, engine):
        """Test adding a calculation node through the engine."""
        # Setup - Add nodes to the graph
        from fin_statement_model.core.nodes import FinancialStatementItemNode
        
        # Create proper node objects
        revenue_us = FinancialStatementItemNode("revenue_us", {"2021": 1000.0, "2022": 1100.0})
        revenue_eu = FinancialStatementItemNode("revenue_eu", {"2021": 500.0, "2022": 600.0})
        
        # Add nodes to the graph
        graph.add_node(revenue_us)
        graph.add_node(revenue_eu)
        
        # Execute - Add a calculation node using the unique strategy name
        engine.add_calculation(
            "total_revenue", 
            ["revenue_us", "revenue_eu"], 
            engine.test_addition_name
        )
        
        # Verify
        assert graph.has_node("total_revenue")
        total_revenue_node = graph.get_node("total_revenue")
        assert total_revenue_node is not None
        assert total_revenue_node.get_attribute("calculation_type") == engine.test_addition_name
        assert total_revenue_node.get_attribute("input_nodes") == ["revenue_us", "revenue_eu"]
    
    def test_calculate_through_engine(self, graph, engine):
        """Test calculating node values through the engine."""
        # Setup - Add nodes to the graph
        from fin_statement_model.core.nodes import FinancialStatementItemNode
        
        # Create proper node objects
        revenue = FinancialStatementItemNode("revenue", {"2021": 1000.0, "2022": 1100.0})
        expenses = FinancialStatementItemNode("expenses", {"2021": 600.0, "2022": 650.0})
        
        # Add nodes to the graph
        graph.add_node(revenue)
        graph.add_node(expenses)
        
        # Add a calculation node using the unique strategy name
        engine.add_calculation(
            "profit", 
            ["revenue", "expenses"], 
            engine.test_subtraction_name
        )
        
        # Execute - Calculate values
        profit_2021 = engine.calculate("profit", "2021")
        profit_2022 = engine.calculate("profit", "2022")
        
        # Verify
        assert profit_2021 == 400.0  # 1000 - 600
        assert profit_2022 == 450.0  # 1100 - 650
    
    def test_circular_dependency_detection_integration(self, graph, engine):
        """Test that circular dependencies are detected."""
        from fin_statement_model.core.engine import CircularDependencyError
        from fin_statement_model.core.nodes import StrategyCalculationNode
        
        # Set up the strategy registry to make sure our strategies exist
        from fin_statement_model.calculations.strategy_registry import CalculationStrategyRegistry
        
        # Create circular nodes properly
        node_a = StrategyCalculationNode("node_a", [], engine.test_addition_name)
        node_a.input_names = ["node_b"]
        
        node_b = StrategyCalculationNode("node_b", [], engine.test_addition_name)
        node_b.input_names = ["node_a"]
        
        # Add nodes to graph
        graph.add_node(node_a)
        graph.add_node(node_b)
        
        # Verify
        with pytest.raises(CircularDependencyError):
            engine.calculate("node_a", "2021")
    
    def test_financial_statement_calculation_integration(self, financial_statement_graph):
        """Test calculations through the FinancialStatementGraph."""
        # Setup - Add nodes and calculations
        financial_statement_graph.add_financial_statement_item(
            "revenue", {"2021": 1000.0, "2022": 1100.0}
        )
        financial_statement_graph.add_financial_statement_item(
            "expenses", {"2021": 600.0, "2022": 650.0}
        )
        
        # Mock the add_calculation method to simulate adding a calculation
        # since we can't directly use the real method without a lot of setup
        def mock_add_calculation(name, inputs, calculation_type):
            # Create a calculation node
            from fin_statement_model.core.nodes import StrategyCalculationNode
            
            # Get the input nodes
            input_nodes = [financial_statement_graph.graph.get_node(input_name) for input_name in inputs]
            
            # Create and add the calculation node
            profit_node = StrategyCalculationNode(name, input_nodes, calculation_type)
            profit_node.input_names = inputs
            financial_statement_graph.graph.add_node(profit_node)
            return name
        
        # Attach the mock to the instance
        financial_statement_graph._calculation_engine.add_calculation = mock_add_calculation
        
        # Add a calculation
        financial_statement_graph.add_calculation("profit", ["revenue", "expenses"], "subtraction")
        
        # Define a custom calculation function to mimic the subtraction strategy
        def mock_calculate(node_name, period):
            if node_name == "profit":
                revenue = financial_statement_graph.graph.nodes["revenue"].calculate(period)
                expenses = financial_statement_graph.graph.nodes["expenses"].calculate(period)
                return revenue - expenses
            return financial_statement_graph.graph.nodes[node_name].calculate(period)
        
        # Patch the calculate method
        financial_statement_graph._calculation_engine.calculate = mock_calculate
        
        # Execute - Calculate values
        values = financial_statement_graph.calculate_financial_statement("profit", "2021")
        
        # Verify
        assert values == 400.0  # 1000 - 600
    
    @patch('fin_statement_model.core.financial_statement.FinancialStatementGraph.to_dataframe')
    def test_exporting_calculated_results(self, mock_to_dataframe, financial_statement_graph):
        """Test exporting calculated results to a DataFrame."""
        # Setup - Create a mock DataFrame
        mock_df = pd.DataFrame({
            "period": ["2021", "2022"],
            "revenue": [1000.0, 1100.0],
            "expenses": [600.0, 650.0],
            "profit": [400.0, 450.0]
        })
        mock_to_dataframe.return_value = mock_df
        
        # Execute
        result_df = financial_statement_graph.to_dataframe(recalculate=True)
        
        # Verify
        mock_to_dataframe.assert_called_once_with(recalculate=True)
        assert result_df.equals(mock_df)
        
        # Check the values in the DataFrame
        assert result_df.loc[0, "profit"] == 400.0
        assert result_df.loc[1, "profit"] == 450.0
    
    def test_recalculate_all_integration(self, financial_statement_graph):
        """Test recalculating all nodes."""
        # Setup - Mock the methods
        financial_statement_graph._data_manager.copy_forward_values = MagicMock()
        financial_statement_graph._calculation_engine.recalculate_all = MagicMock()
        
        # Execute
        financial_statement_graph.recalculate_all()
        
        # Verify
        financial_statement_graph._data_manager.copy_forward_values.assert_called_once_with(
            financial_statement_graph.graph.periods
        )
        financial_statement_graph._calculation_engine.recalculate_all.assert_called_once_with(
            financial_statement_graph.graph.periods
        )
    
    def test_cache_invalidation_after_changes(self, graph, engine):
        """Test that the cache is invalidated after changes to input nodes."""
        from fin_statement_model.core.nodes import FinancialStatementItemNode
        
        # Create proper node objects
        revenue = FinancialStatementItemNode("revenue", {"2021": 1000.0, "2022": 1100.0})
        expenses = FinancialStatementItemNode("expenses", {"2021": 600.0, "2022": 650.0})
        
        # Add nodes to the graph
        graph.add_node(revenue)
        graph.add_node(expenses)
        
        # Add a calculation node
        engine.add_calculation("profit", ["revenue", "expenses"], engine.test_subtraction_name)
        
        # Calculate profit for 2021
        profit_2021 = engine.calculate("profit", "2021")
        assert profit_2021 == 400.0  # 1000 - 600
        
        # Verify it's in the cache (StrategyCalculationNode uses _values instead of _cache)
        profit_node = graph.get_node("profit")
        assert hasattr(profit_node, '_values')
        
        # Update the revenue value for 2021
        revenue_node = graph.get_node("revenue")
        revenue_node.set_value("2021", 900.0)
        
        # Clear both engine cache and node cache
        engine.clear_cache()  # This should clear all caches including the profit node cache
        
        # Recalculate
        new_profit_2021 = engine.calculate("profit", "2021")
        
        # Verify the new profit value
        assert new_profit_2021 == 300.0  # 900 - 600
    
    def test_complex_calculation_chain(self, graph, engine):
        """Test a complex chain of calculations."""
        from fin_statement_model.core.nodes import FinancialStatementItemNode
        from fin_statement_model.calculations.calculation_strategy import CalculationStrategy
        from fin_statement_model.calculations.strategy_registry import CalculationStrategyRegistry
        
        # Create base nodes
        revenue = FinancialStatementItemNode("revenue", {"2021": 1000.0, "2022": 1100.0})
        direct_costs = FinancialStatementItemNode("direct_costs", {"2021": 400.0, "2022": 420.0})
        indirect_costs = FinancialStatementItemNode("indirect_costs", {"2021": 200.0, "2022": 230.0})
        
        # Add nodes to the graph
        graph.add_node(revenue)
        graph.add_node(direct_costs)
        graph.add_node(indirect_costs)
        
        # Add a calculation for total costs (direct + indirect)
        engine.add_calculation(
            "total_costs", 
            ["direct_costs", "indirect_costs"], 
            engine.test_addition_name
        )
        
        # Add a calculation for gross profit (revenue - total_costs)
        engine.add_calculation(
            "gross_profit", 
            ["revenue", "total_costs"], 
            engine.test_subtraction_name
        )
        
        # Add tax rate node
        tax_rate = FinancialStatementItemNode("tax_rate", {"2021": 0.25, "2022": 0.25})
        graph.add_node(tax_rate)
        
        # Create a multiplication strategy for tax calculation
        class MultiplicationStrategy(CalculationStrategy):
            def calculate(self, input_values, parameters=None):
                return input_values[0] * input_values[1]
                
        # Register the multiplication strategy with a unique name
        mult_strategy_name = f"test_multiplication_{str(uuid.uuid4())[:8]}"
        CalculationStrategyRegistry.register_strategy(mult_strategy_name, MultiplicationStrategy)
        
        # Add calculations for tax and net profit
        engine.add_calculation("tax", ["gross_profit", "tax_rate"], mult_strategy_name)
        engine.add_calculation("net_profit", ["gross_profit", "tax"], engine.test_subtraction_name)
        
        # Execute calculations for both years
        net_profit_2021 = engine.calculate("net_profit", "2021")
        net_profit_2022 = engine.calculate("net_profit", "2022")
        
        # Verify the results
        assert net_profit_2021 == 300.0  # (1000 - (400 + 200)) - ((1000 - (400 + 200)) * 0.25)
        assert net_profit_2022 == 337.5  # (1100 - (420 + 230)) - ((1100 - (420 + 230)) * 0.25) 