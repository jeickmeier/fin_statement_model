"""
Strategy Registry for the Financial Statement Model.

This module provides a registry for managing calculation strategies,
enabling new strategies to be registered and retrieved at runtime.
"""
import logging
from typing import Dict, Type, Any, Optional

from .calculation_strategy import (
    CalculationStrategy,
    AdditionStrategy,
    SubtractionStrategy,
    MultiplicationStrategy,
    DivisionStrategy,
    WeightedAverageStrategy,
    CustomFormulaStrategy
)

# Configure logging
logger = logging.getLogger(__name__)


class CalculationStrategyRegistry:
    """
    Registry for calculation strategies.
    
    This class maintains a registry of calculation strategies, allowing
    strategies to be registered, retrieved, and managed centrally.
    """
    
    # Registry of registered strategies
    _strategies: Dict[str, Type[CalculationStrategy]] = {}
    
    # Instance cache for strategy instances
    _instances: Dict[str, CalculationStrategy] = {}
    
    @classmethod
    def register_strategy(cls, name: str, strategy_class: Type[CalculationStrategy]) -> None:
        """
        Register a calculation strategy with the registry.
        
        Args:
            name: Name to register the strategy under
            strategy_class: The strategy class to register
            
        Raises:
            ValueError: If the name is already registered
            TypeError: If strategy_class is not a subclass of CalculationStrategy
        """
        if name in cls._strategies:
            raise ValueError(f"Strategy name '{name}' is already registered")
            
        if not issubclass(strategy_class, CalculationStrategy):
            raise TypeError(f"Strategy class must be a subclass of CalculationStrategy")
            
        cls._strategies[name] = strategy_class
        logger.info(f"Registered calculation strategy '{name}'")
    
    @classmethod
    def get_strategy(cls, name: str, **kwargs) -> CalculationStrategy:
        """
        Get a strategy instance by name.
        
        Args:
            name: Name of the registered strategy
            **kwargs: Parameters to pass to the strategy constructor
            
        Returns:
            CalculationStrategy: An instance of the requested strategy
            
        Raises:
            ValueError: If no strategy is registered with the given name
        """
        # Check if strategy is registered
        if name not in cls._strategies:
            raise ValueError(f"No strategy registered with name '{name}'")
        
        # Check if we have a cached instance with these parameters
        instance_key = f"{name}:{str(kwargs)}"
        if instance_key in cls._instances:
            return cls._instances[instance_key]
        
        # Create new instance
        strategy_class = cls._strategies[name]
        
        # Create the strategy instance
        strategy = strategy_class(**kwargs)
        
        # Cache the instance
        cls._instances[instance_key] = strategy
        
        logger.debug(f"Created strategy instance '{name}' with parameters {kwargs}")
        return strategy
    
    @classmethod
    def list_strategies(cls) -> Dict[str, str]:
        """
        List all registered strategies.
        
        Returns:
            Dict[str, str]: Dictionary mapping strategy names to their class names
        """
        return {name: strategy_class.__name__ for name, strategy_class in cls._strategies.items()}
    
    @classmethod
    def register_built_in_strategies(cls) -> None:
        """
        Register all built-in calculation strategies.
        
        This method should be called during module initialization to ensure
        all built-in strategies are registered by default.
        """
        cls.register_strategy('addition', AdditionStrategy)
        cls.register_strategy('subtraction', SubtractionStrategy)
        cls.register_strategy('multiplication', MultiplicationStrategy)
        cls.register_strategy('division', DivisionStrategy)
        cls.register_strategy('weighted_average', WeightedAverageStrategy)
        cls.register_strategy('custom_formula', CustomFormulaStrategy)
        logger.info("Registered built-in calculation strategies")

    @classmethod
    def has_strategy(cls, name: str) -> bool:
        """
        Check if a strategy is registered with the given name.
        
        Args:
            name: Name of the strategy to check
            
        Returns:
            bool: True if the strategy is registered, False otherwise
        """
        return name in cls._strategies


# Register built-in strategies at module load time
CalculationStrategyRegistry.register_built_in_strategies() 