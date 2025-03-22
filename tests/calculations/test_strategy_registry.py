"""Unit tests for the strategy_registry module.

This module contains tests for the CalculationStrategyRegistry class
that manages the registration and retrieval of calculation strategies.
"""
import pytest
from unittest.mock import patch, Mock

from fin_statement_model.calculations.strategy_registry import CalculationStrategyRegistry
from fin_statement_model.calculations.calculation_strategy import (
    CalculationStrategy,
    AdditionStrategy, 
    SubtractionStrategy,
    MultiplicationStrategy,
    DivisionStrategy,
    WeightedAverageStrategy,
    CustomFormulaStrategy
)


class TestCalculationStrategyRegistry:
    """Tests for the CalculationStrategyRegistry class."""
    
    def setup_method(self):
        """Reset the registry before each test to ensure isolation."""
        # Store original strategies and instances
        self._original_strategies = CalculationStrategyRegistry._strategies.copy()
        self._original_instances = CalculationStrategyRegistry._instances.copy()
        
        # Clear the registry
        CalculationStrategyRegistry._strategies.clear()
        CalculationStrategyRegistry._instances.clear()
        
    def teardown_method(self):
        """Restore the registry after each test."""
        # Restore original strategies and instances
        CalculationStrategyRegistry._strategies = self._original_strategies
        CalculationStrategyRegistry._instances = self._original_instances
    
    def test_register_strategy(self):
        """Test registering a strategy."""
        # Create a mock strategy class
        class TestStrategy(CalculationStrategy):
            def calculate(self, inputs, period):
                return 0.0
        
        # Register the strategy
        CalculationStrategyRegistry.register_strategy("test_strategy", TestStrategy)
        
        # Check if the strategy is registered
        assert "test_strategy" in CalculationStrategyRegistry._strategies
        assert CalculationStrategyRegistry._strategies["test_strategy"] is TestStrategy
    
    def test_register_existing_strategy(self):
        """Test that registering a strategy with an existing name raises ValueError."""
        # Create a mock strategy class
        class TestStrategy(CalculationStrategy):
            def calculate(self, inputs, period):
                return 0.0
        
        # Register the strategy once
        CalculationStrategyRegistry.register_strategy("test_strategy", TestStrategy)
        
        # Attempt to register with the same name again
        with pytest.raises(ValueError) as excinfo:
            CalculationStrategyRegistry.register_strategy("test_strategy", TestStrategy)
        
        assert "already registered" in str(excinfo.value)
    
    def test_register_non_strategy_class(self):
        """Test that registering a non-CalculationStrategy class raises TypeError."""
        # Create a class that is not a subclass of CalculationStrategy
        class NotAStrategy:
            pass
        
        # Attempt to register the non-strategy class
        with pytest.raises(TypeError) as excinfo:
            CalculationStrategyRegistry.register_strategy("not_a_strategy", NotAStrategy)
        
        assert "must be a subclass" in str(excinfo.value)
    
    def test_get_strategy(self):
        """Test getting a registered strategy."""
        # Register AdditionStrategy
        CalculationStrategyRegistry.register_strategy("addition", AdditionStrategy)
        
        # Get the strategy instance
        strategy = CalculationStrategyRegistry.get_strategy("addition")
        
        # Check if the instance is of the correct type
        assert isinstance(strategy, AdditionStrategy)
    
    def test_get_strategy_with_parameters(self):
        """Test getting a strategy with constructor parameters."""
        # Register WeightedAverageStrategy
        CalculationStrategyRegistry.register_strategy("weighted", WeightedAverageStrategy)
        
        # Get the strategy instance with parameters
        weights = [0.5, 0.3, 0.2]
        strategy = CalculationStrategyRegistry.get_strategy("weighted", weights=weights)
        
        # Check if the instance has the correct parameters
        assert isinstance(strategy, WeightedAverageStrategy)
        assert strategy.weights == weights
    
    def test_get_nonexistent_strategy(self):
        """Test that getting a non-existent strategy raises ValueError."""
        # Attempt to get a non-existent strategy
        with pytest.raises(ValueError) as excinfo:
            CalculationStrategyRegistry.get_strategy("nonexistent")
        
        assert "No strategy registered" in str(excinfo.value)
    
    def test_strategy_instance_caching(self):
        """Test that strategy instances are cached."""
        # Create a mock strategy class that counts instantiations
        instantiation_count = 0
        
        class CountingStrategy(CalculationStrategy):
            def __init__(self, param=None):
                nonlocal instantiation_count
                instantiation_count += 1
                self.param = param
                
            def calculate(self, inputs, period):
                return 0.0
        
        # Register the strategy
        CalculationStrategyRegistry.register_strategy("counting", CountingStrategy)
        
        # Get the strategy instance multiple times
        strategy1 = CalculationStrategyRegistry.get_strategy("counting")
        strategy2 = CalculationStrategyRegistry.get_strategy("counting")
        
        # Check that only one instance was created
        assert instantiation_count == 1
        assert strategy1 is strategy2
        
        # Get the strategy with different parameters
        strategy3 = CalculationStrategyRegistry.get_strategy("counting", param="value1")
        strategy4 = CalculationStrategyRegistry.get_strategy("counting", param="value1")
        strategy5 = CalculationStrategyRegistry.get_strategy("counting", param="value2")
        
        # Check that two more instances were created (for different parameters)
        assert instantiation_count == 3
        assert strategy3 is strategy4
        assert strategy3 is not strategy5
    
    def test_list_strategies(self):
        """Test listing all registered strategies."""
        # Register some strategies
        CalculationStrategyRegistry.register_strategy("addition", AdditionStrategy)
        CalculationStrategyRegistry.register_strategy("subtraction", SubtractionStrategy)
        
        # List the strategies
        strategies = CalculationStrategyRegistry.list_strategies()
        
        # Check if the list contains the registered strategies
        assert "addition" in strategies
        assert "subtraction" in strategies
        assert strategies["addition"] == "AdditionStrategy"
        assert strategies["subtraction"] == "SubtractionStrategy"
    
    def test_register_built_in_strategies(self):
        """Test that register_built_in_strategies registers all built-in strategies."""
        # Register built-in strategies
        CalculationStrategyRegistry.register_built_in_strategies()
        
        # Check if all built-in strategies are registered
        strategies = CalculationStrategyRegistry._strategies
        assert "addition" in strategies
        assert "subtraction" in strategies
        assert "multiplication" in strategies
        assert "division" in strategies
        assert "weighted_average" in strategies
        assert "custom_formula" in strategies
        
        # Check the actual classes
        assert strategies["addition"] is AdditionStrategy
        assert strategies["subtraction"] is SubtractionStrategy
        assert strategies["multiplication"] is MultiplicationStrategy
        assert strategies["division"] is DivisionStrategy
        assert strategies["weighted_average"] is WeightedAverageStrategy
        assert strategies["custom_formula"] is CustomFormulaStrategy
    
    def test_module_initialization(self):
        """Test that built-in strategies are registered at module initialization."""
        # Since the module has already been imported, the built-in strategies
        # should already be registered in the original strategies dictionary
        
        # Check if all built-in strategies are in the original registry
        assert "addition" in self._original_strategies
        assert "subtraction" in self._original_strategies
        assert "multiplication" in self._original_strategies
        assert "division" in self._original_strategies
        assert "weighted_average" in self._original_strategies
        assert "custom_formula" in self._original_strategies 