"""
Node Factory for the Financial Statement Model.

This module provides a factory for creating different types of nodes used in the financial statement model.
It centralizes node creation logic and ensures consistent node initialization.
"""
import logging
from typing import Dict, List, Any, Union, Callable

from .nodes import (
    Node, 
    FinancialStatementItemNode, 
    CalculationNode,
    AdditionCalculationNode, 
    SubtractionCalculationNode,
    MultiplicationCalculationNode, 
    DivisionCalculationNode,
    StrategyCalculationNode,
    MetricCalculationNode,
)
from ..forecasts import (
    ForecastNode,
    FixedGrowthForecastNode,
    CurveGrowthForecastNode,
    StatisticalGrowthForecastNode,
    CustomGrowthForecastNode,
    AverageValueForecastNode,
    AverageHistoricalGrowthForecastNode
)
from ..calculations import CalculationStrategyRegistry

# Configure logging
logger = logging.getLogger(__name__)


class NodeFactory:
    """
    Factory class for creating nodes in the financial statement model.
    
    This class centralizes the creation of all types of nodes, ensuring consistent
    initialization and simplifying the creation process. It provides methods
    for creating financial statement items, calculation nodes, forecast nodes,
    and metric nodes.
    """
    
    # Mapping of calculation types to strategy names
    _calculation_strategies = {
        'addition': 'addition',
        'subtraction': 'subtraction',
        'multiplication': 'multiplication',
        'division': 'division',
        'weighted_average': 'weighted_average',
        'custom_formula': 'custom_formula',
    }
    
    # Mapping of legacy calculation types to node classes (for backward compatibility)
    _calculation_node_types = {
        'addition': AdditionCalculationNode,
        'subtraction': SubtractionCalculationNode,
        'multiplication': MultiplicationCalculationNode,
        'division': DivisionCalculationNode,
    }
    
    # Mapping of forecast types to node classes
    _forecast_node_types = {
        'fixed': FixedGrowthForecastNode,
        'curve': CurveGrowthForecastNode,
        'statistical': StatisticalGrowthForecastNode,
        'custom': CustomGrowthForecastNode,
        'average': AverageValueForecastNode,
        'historical_growth': AverageHistoricalGrowthForecastNode,
    }
    
    @classmethod
    def create_financial_statement_item(cls, name: str, values: Dict[str, float]) -> FinancialStatementItemNode:
        """
        Create a financial statement item node.
        
        Args:
            name: Name of the node
            values: Dictionary mapping periods to values
            
        Returns:
            FinancialStatementItemNode: The created node
            
        Raises:
            ValueError: If the name is invalid
        """
        if not name or not isinstance(name, str):
            raise ValueError("Node name must be a non-empty string")
            
        logger.debug(f"Creating financial statement item node: {name}")
        return FinancialStatementItemNode(name, values)
    
    @classmethod
    def create_calculation_node(cls, name: str, inputs: List[Node], 
                               calculation_type: str, **kwargs) -> CalculationNode:
        """
        Create a calculation node of the specified type.
        
        This method uses the Strategy Pattern to create a calculation node with the appropriate
        calculation strategy. It supports all built-in calculation types as well as custom
        strategies.
        
        Args:
            name: Name of the node
            inputs: List of input nodes
            calculation_type: Type of calculation strategy to use ('addition', 'subtraction', etc.)
            **kwargs: Additional parameters for the strategy
            
        Returns:
            CalculationNode: The created calculation node
            
        Raises:
            ValueError: If the calculation type is invalid
            ValueError: If the name is invalid
            ValueError: If inputs is empty
        """
        # Validate inputs
        if not name or not isinstance(name, str):
            raise ValueError("Node name must be a non-empty string")
            
        if not inputs:
            raise ValueError("Calculation node must have at least one input")
        
        # Check if we should use legacy node types (for backward compatibility)
        use_legacy = kwargs.pop('use_legacy', False)
        
        if use_legacy and calculation_type in cls._calculation_node_types:
            # Create a legacy calculation node
            node_class = cls._calculation_node_types[calculation_type]
            logger.debug(f"Creating legacy calculation node of type '{calculation_type}': {name}")
            return node_class(name, inputs)
        
        # Check if the calculation type is valid for the strategy pattern
        if calculation_type not in cls._calculation_strategies:
            valid_types = list(cls._calculation_strategies.keys())
            raise ValueError(f"Invalid calculation type: {calculation_type}. Valid types are: {valid_types}")
        
        # Get the appropriate strategy
        strategy_name = cls._calculation_strategies[calculation_type]
        strategy = CalculationStrategyRegistry.get_strategy(strategy_name, **kwargs)
        
        # Create and return a strategy calculation node
        logger.debug(f"Creating strategy calculation node with '{strategy_name}' strategy: {name}")
        return StrategyCalculationNode(name, inputs, strategy)
    
    @classmethod
    def create_forecast_node(cls, name: str, base_node: Node, base_period: str,
                           forecast_periods: List[str], forecast_type: str,
                           growth_params: Union[float, List[float], Callable]) -> ForecastNode:
        """
        Create a forecast node of the specified type.
        
        Args:
            name: Name of the node (ignored as forecast nodes take their name from the base_node)
            base_node: Node to use as the basis for the forecast
            base_period: Last historical period to use as basis
            forecast_periods: List of future periods to generate forecasts for
            forecast_type: Type of forecast ('fixed', 'curve', 'statistical', 'custom')
            growth_params: Growth parameters for the forecast
                          - For 'fixed': float representing constant growth rate
                          - For 'curve': List[float] representing growth rates for each period
                          - For 'statistical': Callable that returns random growth rates
                          - For 'custom': Callable that takes (period, prev_period, prev_value)
            
        Returns:
            ForecastNode: The created forecast node
            
        Raises:
            ValueError: If the forecast type is invalid
            ValueError: If growth parameters don't match the forecast type
        """
        # Validate inputs
        if not base_node:
            raise ValueError("Base node is required for forecast")
            
        if not base_period or not isinstance(base_period, str):
            raise ValueError("Base period must be a non-empty string")
            
        if not forecast_periods:
            raise ValueError("Forecast periods must not be empty")
            
        # Get the appropriate node class
        if forecast_type not in cls._forecast_node_types:
            valid_types = list(cls._forecast_node_types.keys())
            raise ValueError(f"Invalid forecast type: {forecast_type}. Valid types are: {valid_types}")
            
        # Validate growth parameters based on forecast type
        cls._validate_growth_params(forecast_type, growth_params, forecast_periods)
        
        node_class = cls._forecast_node_types[forecast_type]
        
        logger.debug(f"Creating forecast node of type '{forecast_type}' for base node: {base_node.name}")
        
        # Create and return the forecast node with the appropriate parameters
        return node_class(base_node, base_period, forecast_periods, growth_params)
    
    @classmethod
    def create_metric_node(cls, name: str, inputs: List[Node], 
                         formula: Callable, description: str = None) -> MetricCalculationNode:
        """
        Create a metric calculation node.
        
        Args:
            name: Name for the node
            inputs: List of input nodes
            formula: Formula for calculation (a callable function)
            description: Optional description
            
        Returns:
            MetricCalculationNode: The created metric node
            
        Raises:
            ValueError: If inputs are invalid
        """
        # Validate inputs
        if not name or not isinstance(name, str):
            raise ValueError("Node name must be a non-empty string")
            
        if not inputs:
            raise ValueError("Metric node must have at least one input")
            
        if not callable(formula):
            raise ValueError("Formula must be a callable function")
            
        # Create a custom CalculationNode directly
        class CustomCalculationNode(CalculationNode):
            def __init__(self, name, inputs, formula_func, description):
                super().__init__(name, inputs)
                self.formula_func = formula_func
                self.description = description
                
            def calculate(self, period: str) -> float:
                input_values = [node.calculate(period) for node in self.inputs]
                return self.formula_func(*input_values)
                
        logger.debug(f"Creating metric node: {name}")
        return CustomCalculationNode(name, inputs, formula, description)
    
    @classmethod
    def _validate_growth_params(cls, forecast_type: str, growth_params: Any, 
                              forecast_periods: List[str]) -> None:
        """
        Validate that growth parameters match the requirements of the forecast type.
        
        Args:
            forecast_type: Type of forecast
            growth_params: Growth parameters to validate
            forecast_periods: List of forecast periods (needed for some validations)
            
        Raises:
            ValueError: If growth parameters don't match the forecast type requirements
        """
        if forecast_type == 'fixed':
            if not isinstance(growth_params, (int, float)):
                raise ValueError("For fixed growth forecast, growth_params must be a number")
                
        elif forecast_type == 'curve':
            if not isinstance(growth_params, list) or len(growth_params) != len(forecast_periods):
                raise ValueError("For curve growth forecast, growth_params must be a list with one value per forecast period")
                
        elif forecast_type == 'statistical' or forecast_type == 'custom':
            if not callable(growth_params):
                raise ValueError(f"For {forecast_type} growth forecast, growth_params must be callable") # pragma: no cover
                
        # If we get here, validation passed
        return 