"""
Calculation engine for Financial Statement Model.

This module provides the core calculation engine for the Financial Statement Model,
responsible for executing calculations on graph nodes.
"""
import logging
from typing import Dict, List, Any, Optional, Union, Callable, TYPE_CHECKING

from .errors import (
    CalculationError, 
    NodeError, 
    CircularDependencyError,
    StrategyError
)
from ..calculations import (
    CalculationStrategy, 
    CalculationStrategyRegistry
)

# Use TYPE_CHECKING for circular imports
if TYPE_CHECKING:
    from .graph import Graph  # pragma: no cover

# Configure logging
logger = logging.getLogger(__name__)


class CalculationEngine:
    """
    Core calculation engine for the Financial Statement Model.
    
    The calculation engine is responsible for performing calculations on nodes
    in the graph. It supports various calculation types and handles dependencies
    between calculations.
    """
    
    def __init__(self):
        """Initialize a calculation engine."""
        self._graph = None
        self._strategy_registry = CalculationStrategyRegistry()
        self._calculation_cache = {}
        
    def set_graph(self, graph):
        """
        Set the graph for this calculation engine.
        
        Args:
            graph: The graph instance
        """
        # We don't import Graph for type checking here to avoid circular imports
        self._graph = graph
        
    def clear_cache(self):
        """
        Clear the calculation cache.
        
        This forces all future calculations to be recomputed.
        """
        if hasattr(self, '_calculation_cache'):
            self._calculation_cache = {}
            
        # Also clear any node-level caches
        if self._graph:
            for node_id, node in self._graph.nodes.items():
                if hasattr(node, 'clear_cache'):
                    node.clear_cache()
        
    def reset(self):
        """Reset the calculation engine."""
        self.clear_cache()
        
    def add_calculation(self, node_id: str, input_nodes: List[str], 
                        calc_type: str, **params) -> str:
        """
        Add a calculation to the graph.
        
        Args:
            node_id: ID of the node to create
            input_nodes: List of input node IDs
            calc_type: Type of calculation to perform
            **params: Additional parameters for the calculation
            
        Raises:
            StrategyError: If the calculation type is not supported
            NodeError: If input nodes don't exist
        """
        if not self._graph:
            raise CalculationError(
                message="No graph assigned to calculation engine"
            )
            
        # Check if calculation type is supported
        if not self._strategy_registry.has_strategy(calc_type):
            raise StrategyError(
                message=f"Unsupported calculation type: {calc_type}",
                strategy_type=calc_type,
                node_id=node_id
            )
            
        # Verify that input nodes exist
        missing_nodes = []
        for input_id in input_nodes:
            if not self._graph.has_node(input_id):
                missing_nodes.append(input_id)
                
        if missing_nodes:
            raise NodeError(
                message=f"Input nodes not found for calculation '{node_id}'",
                node_id=node_id
            )
            
        # Create the calculation node
        try:
            from ..core.nodes import StrategyCalculationNode
            
            # Get the strategy from the registry
            strategy = self._strategy_registry.get_strategy(calc_type)
            
            # Get the input node objects
            input_node_objects = [self._graph.get_node(input_id) for input_id in input_nodes]
            
            # Create the calculation node
            calc_node = StrategyCalculationNode(node_id, input_node_objects, strategy)
            calc_node.input_names = input_nodes
            calc_node.calculation_type = calc_type  # Store the calculation type
            
            # Add additional parameters if provided
            for key, value in params.items():
                setattr(calc_node, key, value)
                
            # Add the node to the graph
            self._graph.add_node(calc_node)
            
            logger.info(f"Added calculation node '{node_id}' of type '{calc_type}'")
            return node_id
        except Exception as e:
            logger.error(f"Failed to add calculation '{node_id}': {e}")
            if isinstance(e, (StrategyError, NodeError)):
                # Re-raise specific errors
                raise
            else:
                raise CalculationError(
                    message=f"Failed to add calculation node",
                    node_id=node_id,
                    details={"calculation_type": calc_type, "error": str(e)}
                ) from e
                
    def calculate(self, node_id: str, period: str) -> float:
        """
        Calculate the value for a node in a specific period.
        
        Args:
            node_id: ID of the node to calculate
            period: Period to calculate for
            
        Returns:
            float: Calculated value
            
        Raises:
            NodeError: If the node doesn't exist
            CalculationError: If calculation fails
            CircularDependencyError: If a circular dependency is detected
        """
        if not self._graph:
            raise CalculationError(
                message="No graph assigned to calculation engine"
            )
            
        # Check if node exists
        node = self._graph.get_node(node_id)
        if not node:
            raise NodeError(
                message=f"Node not found: {node_id}",
                node_id=node_id
            )
            
        # Check cache
        cache_key = (node_id, period)
        if cache_key in self._calculation_cache:
            return self._calculation_cache[cache_key]
            
        # Add to calculation stack to detect circular dependencies
        if not hasattr(self, '_calculation_stack'):
            self._calculation_stack = []
            
        if node_id in self._calculation_stack:
            # Circular dependency detected
            cycle = self._calculation_stack[self._calculation_stack.index(node_id):]
            cycle.append(node_id)
            raise CircularDependencyError(
                message=f"Circular dependency detected when calculating {node_id}",
                cycle=cycle
            )
            
        # Track calculation depth
        self._calculation_stack.append(node_id)
        
        try:
            # If node has a value for this period, return it
            if node.has_value(period):
                value = node.get_value(period)
                self._calculation_cache[cache_key] = value
                return value
                
            # If node has a calculation, compute it
            if node.has_calculation():
                value = self._execute_calculation(node, period)
                self._calculation_cache[cache_key] = value
                return value
                
            # If neither value nor calculation, raise error
            raise CalculationError(
                message=f"Node has no value or calculation for period {period}",
                node_id=node_id,
                period=period
            )
            
        finally:
            # Remove from calculation stack regardless of success/failure
            self._calculation_stack.pop()
                
    def _execute_calculation(self, node, period: str) -> float:
        """
        Execute a calculation for a node.
        
        Args:
            node: The node to calculate
            period: The period to calculate for
            
        Returns:
            float: Calculated value
            
        Raises:
            CalculationError: If calculation fails
        """
        try:
            # Get calculation details
            calc_type = node.get_attribute('calculation_type')
            input_nodes = node.get_attribute('input_nodes', [])
            parameters = node.get_attribute('parameters', {})
            strategy = node.get_attribute('strategy')
            
            if not strategy:
                # Try to get strategy from registry
                if calc_type:
                    strategy = self._strategy_registry.get_strategy(calc_type)
                else:
                    raise StrategyError(
                        message="No calculation strategy specified for node",
                        node_id=node.name
                    )
                    
            # Calculate input values
            input_values = []
            for input_id in input_nodes:
                input_value = self.calculate(input_id, period)
                input_values.append(input_value)
                
            # Execute calculation
            result = strategy.calculate(input_values, parameters)
            
            # Store result in node
            node.set_value(period, result)
            
            return result
            
        except Exception as e:
            if isinstance(e, (CalculationError, NodeError, CircularDependencyError, StrategyError)):
                # Re-raise specific errors
                raise
            else:
                # Wrap other exceptions
                logger.error(f"Calculation error for node {node.name}: {e}")
                raise CalculationError(
                    message=f"Failed to calculate node '{node.name}' for period {period}",
                    node_id=node.name,
                    period=period,
                    details={"error": str(e)}
                ) from e
                
    def register_strategy(self, strategy_type: str, strategy: CalculationStrategy) -> None:
        """
        Register a calculation strategy.
        
        Args:
            strategy_type: The type name for this strategy
            strategy: The strategy implementation
            
        Raises:
            StrategyError: If the strategy is invalid
        """
        try:
            self._strategy_registry.register_strategy(strategy_type, strategy)
        except Exception as e:
            logger.error(f"Failed to register strategy '{strategy_type}': {e}")
            raise StrategyError(
                message=f"Failed to register calculation strategy",
                strategy_type=strategy_type
            ) from e
            
    def get_strategy(self, strategy_type: str) -> Optional[CalculationStrategy]:
        """
        Get a registered calculation strategy.
        
        Args:
            strategy_type: The type name of the strategy
            
        Returns:
            Optional[CalculationStrategy]: The strategy implementation or None if not found
            
        Raises:
            StrategyError: If the strategy type is not registered
        """
        try:
            return self._strategy_registry.get_strategy(strategy_type)
        except Exception as e:
            logger.error(f"Failed to get strategy '{strategy_type}': {e}")
            raise StrategyError(
                message=f"Failed to get calculation strategy",
                strategy_type=strategy_type
            ) from e 