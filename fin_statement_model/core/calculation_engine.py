"""
Calculation engine functionality for the Financial Statement Model.

This module provides the CalculationEngine class which is responsible for managing
calculation nodes and performing calculations on the financial data graph.
"""
from typing import Dict, List, Union, Any, Optional
import logging

from .graph import Graph
from .nodes import (Node, CalculationNode, AdditionCalculationNode,
                    SubtractionCalculationNode, MultiplicationCalculationNode,
                    DivisionCalculationNode, MetricCalculationNode, StrategyCalculationNode)
from .metrics import METRIC_DEFINITIONS
from ..calculations import CalculationStrategyRegistry
from .node_factory import NodeFactory

# Configure logging
logger = logging.getLogger(__name__)


class CalculationEngine:
    """
    Manages calculations in the financial statement graph.
    
    The CalculationEngine is responsible for:
    - Adding calculation nodes to the graph
    - Computing financial metrics and ratios
    - Managing the calculation execution order
    - Handling calculation errors and edge cases
    
    It ensures proper calculation dependency management and execution.
    
    Attributes:
        graph (Graph): The graph to perform calculations on
    """
    
    def __init__(self, graph: Graph):
        """
        Initialize a CalculationEngine with a reference to the graph.
        
        Args:
            graph (Graph): The graph to perform calculations on
        """
        self.graph = graph
    
    def add_calculation(self, name: str, input_names: List[str], operation_type: str, **kwargs) -> Node:
        """
        Add a calculation node to the graph that performs arithmetic operations between input nodes.

        Args:
            name: The name/identifier for the calculation node (e.g. "gross_profit", "operating_margin")
            input_names: List of input node names that will be used in the calculation. Must be existing nodes.
            operation_type: Type of arithmetic operation to perform. Valid values are:
                - 'addition': Adds all input values together
                - 'subtraction': Subtracts subsequent values from the first input
                - 'multiplication': Multiplies all input values together  
                - 'division': Divides first input by second input
                - 'weighted_average': Calculates weighted average of inputs
                - 'custom_formula': Uses a custom formula function
            **kwargs: Additional parameters for the calculation strategy

        Returns:
            Node: The newly created calculation node

        Raises:
            ValueError: If any input nodes don't exist in the graph
            ValueError: If an invalid operation_type is provided

        Example:
            # Calculate gross profit as revenue - cost_of_goods_sold
            engine.add_calculation("gross_profit", ["revenue", "cost_of_goods_sold"], "subtraction")
            
            # Calculate weighted average with custom weights
            engine.add_calculation("weighted_score", ["score1", "score2", "score3"], 
                                  "weighted_average", weights=[0.5, 0.3, 0.2])
        """
        # Get input nodes
        input_nodes = []
        for input_name in input_names:
            node = self.graph.get_node(input_name)
            if node is None:
                raise ValueError(f"Input node '{input_name}' not found in graph.")
            input_nodes.append(node)
        
        # Use NodeFactory to create the appropriate calculation node
        node = NodeFactory.create_calculation_node(name, input_nodes, operation_type, **kwargs)
        
        # Store input names for reference
        node.input_names = input_names
        
        # Add node to graph
        self.graph.add_node(node)
        logger.debug(f"Added calculation node '{name}' with operation '{operation_type}' to the graph")
        return node
    
    def add_metric(self, metric_name: str, node_name: str = None) -> Node:
        """
        Add a financial metric calculation node to the graph.
        
        Args:
            metric_name: The name of the metric from the METRIC_DEFINITIONS
            node_name: Optional custom name for the node (defaults to metric_name)
            
        Returns:
            Node: The created metric node
            
        Raises:
            ValueError: If the metric_name is not found in METRIC_DEFINITIONS
            ValueError: If any required input nodes are missing from the graph
        """
        # Check if metric definition exists
        if metric_name not in METRIC_DEFINITIONS:
            raise ValueError(f"Metric '{metric_name}' not found in metric definitions.")
        
        metric_def = METRIC_DEFINITIONS[metric_name]
        target_node_name = node_name if node_name else metric_name
        
        # Check if metric is a direct calculation
        if "formula" in metric_def:
            # Process the formula and add to graph
            if "inputs" in metric_def:
                inputs = metric_def["inputs"]
                for input_name in inputs:
                    if self.graph.get_node(input_name) is None:
                        raise ValueError(f"Required input '{input_name}' for metric '{metric_name}' not found in graph.")
                
                # Get the input nodes
                input_nodes = [self.graph.get_node(input_name) for input_name in inputs]
                
                # Convert string formula to callable function
                formula_str = metric_def["formula"]
                
                # Create a callable function from the formula string
                def formula_func(*args):
                    # Create a dictionary mapping input names to their values
                    values_dict = {input_name: value for input_name, value in zip(inputs, args)}
                    
                    # Evaluate the formula string using the values
                    # Replace input names with their values in the formula
                    eval_formula = formula_str
                    for input_name, value in values_dict.items():
                        eval_formula = eval_formula.replace(input_name, str(value))
                    
                    try:
                        return eval(eval_formula)
                    except Exception as e:
                        raise ValueError(f"Error evaluating formula '{formula_str}': {e}")
                
                # Use NodeFactory to create the metric calculation node
                node = NodeFactory.create_metric_node(
                    target_node_name,
                    input_nodes,
                    formula_func,
                    metric_def.get("description", None)
                )
                self.graph.add_node(node)
                logger.debug(f"Added metric node '{target_node_name}' to the graph")
                return node
                
        # If it's a derived metric that needs its own function
        elif "function" in metric_def:
            # Custom metric implementation would go here
            raise NotImplementedError(f"Custom metric function for '{metric_name}' not yet implemented.")
        
        else:
            raise ValueError(f"Metric '{metric_name}' definition is invalid - missing formula or function.")
    
    def calculate(self, node_name: str = None, period: str = None) -> Dict:
        """
        Calculate the value of a node for a specific time period.

        Args:
            node_name: The name/identifier of the node to calculate, or None for all nodes
            period: The time period to calculate the value for (e.g. "FY2022"), or None for all periods

        Returns:
            Dict: Dictionary of calculated values, mapping node names to values (if node_name is None)
                 or periods to values (if period is None) or a single value (if both are provided)

        Raises:
            ValueError: If the node does not exist in the graph
            ValueError: If there is an error performing the calculation

        Example:
            # Calculate gross profit for FY2022
            gross_profit = engine.calculate("gross_profit", "FY2022")
            
            # Calculate all nodes for FY2022
            all_values = engine.calculate(period="FY2022")
            
            # Calculate gross profit for all periods
            gross_profit_by_period = engine.calculate("gross_profit")
        """
        return self.graph.calculate(node_name, period)
    
    def recalculate_all(self, periods: List[str] = None) -> None:
        """
        Recalculate all nodes in the graph for all specified periods.
        
        Args:
            periods: List of periods to recalculate for. If None, uses graph.periods.
            
        Raises:
            ValueError: If a cycle is detected in the calculation dependencies
        """
        if periods is None:
            periods = self.graph.periods
            
        # Clear all caches
        self.graph.clear_all_caches()
        
        # Get topologically sorted order to ensure proper calculation order
        order = self.graph.topological_sort()
        
        # Recalculate each node for all periods
        for period in periods:
            for node_name in order:
                node = self.graph.get_node(node_name)
                try:
                    node.calculate(period)
                except ValueError:
                    # Skip if period not valid for this node
                    continue
                except Exception as e:
                    # Handle other calculation errors
                    logger.error(f"Error calculating {node_name} for {period}: {e}")
                    # Continue with other calculations
    
    def get_available_operations(self) -> Dict[str, str]:
        """
        Get a dictionary of available calculation operations.
        
        Returns:
            Dict[str, str]: Dictionary mapping operation names to descriptions
        """
        return CalculationStrategyRegistry.list_strategies()
    
    def change_calculation_strategy(self, node_name: str, new_strategy_name: str, **kwargs) -> None:
        """
        Change the calculation strategy for an existing node.
        
        This method allows dynamically changing how a calculation is performed
        without creating a new node.
        
        Args:
            node_name: Name of the existing calculation node
            new_strategy_name: Name of the new strategy to use
            **kwargs: Additional parameters for the strategy
            
        Raises:
            ValueError: If the node does not exist
            ValueError: If the node is not a StrategyCalculationNode
            ValueError: If the strategy name is invalid
        """
        node = self.graph.get_node(node_name)
        if node is None:
            raise ValueError(f"Node '{node_name}' not found in graph.")
            
        if not isinstance(node, StrategyCalculationNode):
            raise ValueError(f"Node '{node_name}' is not a StrategyCalculationNode.")
            
        # Get the new strategy
        new_strategy = CalculationStrategyRegistry.get_strategy(new_strategy_name, **kwargs)
        
        # Change the strategy
        node.set_strategy(new_strategy)
        logger.debug(f"Changed calculation strategy for node '{node_name}' to '{new_strategy_name}'")
        
        # Clear cache to ensure recalculation
        node.clear_cache() 