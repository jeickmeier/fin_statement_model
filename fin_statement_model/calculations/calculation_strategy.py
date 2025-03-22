"""
Calculation Strategy for the Financial Statement Model.

This module provides the Strategy Pattern implementation for calculation strategies,
allowing different calculation types to be encapsulated in strategy classes.
"""
from abc import ABC, abstractmethod
from typing import List
import logging

from ..core.nodes import Node

# Configure logging
logger = logging.getLogger(__name__)


class CalculationStrategy(ABC):
    """
    Abstract base class for calculation strategies.
    
    This class defines the interface for all calculation strategies.
    Each concrete strategy implements a specific way to calculate values
    from a set of input nodes.
    """
    
    @abstractmethod
    def calculate(self, inputs: List[Node], period: str) -> float:
        """
        Calculate a value based on the input nodes for a specific period.
        
        Args:
            inputs: List of input nodes to use in the calculation
            period: The time period to calculate for
            
        Returns:
            float: The calculated value
            
        Raises:
            ValueError: If the calculation cannot be performed
        """
        pass # pragma: no cover
    
    @property
    def description(self) -> str:
        """
        Get a human-readable description of the calculation strategy.
        
        Returns:
            str: Description of the calculation strategy
        """
        # Split into two statements for better testability
        class_name = self.__class__.__name__  # pragma: no cover
        return class_name


class AdditionStrategy(CalculationStrategy):
    """
    Strategy for adding values from multiple input nodes.
    
    This strategy sums the values of all input nodes for a given period.
    """
    
    def calculate(self, inputs: List[Node], period: str) -> float:
        """
        Sum values from all input nodes for the specified period.
        
        Args:
            inputs: List of input nodes
            period: The time period to calculate for
            
        Returns:
            float: Sum of all input values
        """
        logger.debug(f"Applying addition strategy for period {period}")
        return sum(input_node.calculate(period) for input_node in inputs)
    
    @property
    def description(self) -> str:
        return "Addition (sum of all inputs)"


class SubtractionStrategy(CalculationStrategy):
    """
    Strategy for subtracting subsequent values from the first input.
    
    This strategy takes the first input node's value and subtracts
    all subsequent input node values from it.
    """
    
    def calculate(self, inputs: List[Node], period: str) -> float:
        """
        Subtract subsequent input values from the first input.
        
        Args:
            inputs: List of input nodes
            period: The time period to calculate for
            
        Returns:
            float: Result of the subtraction
            
        Raises:
            ValueError: If inputs list is empty
        """
        if not inputs:
            raise ValueError("Subtraction strategy requires at least one input node")
            
        logger.debug(f"Applying subtraction strategy for period {period}")
        result = inputs[0].calculate(period)
        for input_node in inputs[1:]:
            result -= input_node.calculate(period)
        return result
    
    @property
    def description(self) -> str:
        return "Subtraction (first input minus subsequent inputs)"


class MultiplicationStrategy(CalculationStrategy):
    """
    Strategy for multiplying values from multiple input nodes.
    
    This strategy multiplies the values of all input nodes for a given period.
    """
    
    def calculate(self, inputs: List[Node], period: str) -> float:
        """
        Multiply values from all input nodes for the specified period.
        
        Args:
            inputs: List of input nodes
            period: The time period to calculate for
            
        Returns:
            float: Product of all input values
            
        Raises:
            ValueError: If inputs list is empty
        """
        if not inputs:
            raise ValueError("Multiplication strategy requires at least one input node")
            
        logger.debug(f"Applying multiplication strategy for period {period}")
        result = 1.0  # Start with multiplicative identity
        for input_node in inputs:
            result *= input_node.calculate(period)
        return result
    
    @property
    def description(self) -> str:
        return "Multiplication (product of all inputs)"


class DivisionStrategy(CalculationStrategy):
    """
    Strategy for dividing the first input by subsequent inputs.
    
    This strategy takes the first input node's value and divides it
    by each subsequent input node value in sequence.
    """
    
    def calculate(self, inputs: List[Node], period: str) -> float:
        """
        Divide the first input value by subsequent input values.
        
        Args:
            inputs: List of input nodes
            period: The time period to calculate for
            
        Returns:
            float: Result of the division
            
        Raises:
            ValueError: If inputs list is empty or has only one element
            ZeroDivisionError: If any divisor equals zero
        """
        if len(inputs) < 2:
            raise ValueError("Division strategy requires at least two input nodes")
            
        logger.debug(f"Applying division strategy for period {period}")
        result = inputs[0].calculate(period)
        for input_node in inputs[1:]:
            divisor = input_node.calculate(period)
            if divisor == 0:
                raise ZeroDivisionError("Division by zero in calculation")
            result /= divisor
        return result
    
    @property
    def description(self) -> str:
        return "Division (first input divided by subsequent inputs)"


class WeightedAverageStrategy(CalculationStrategy):
    """
    Strategy for calculating weighted average of input values.
    
    This strategy calculates the weighted average of input node values,
    where each input has an associated weight.
    """
    
    def __init__(self, weights: List[float] = None):
        """
        Initialize the weighted average strategy.
        
        Args:
            weights: Optional list of weights corresponding to each input node.
                    If None, equal weights will be used.
        """
        self.weights = weights
    
    def calculate(self, inputs: List[Node], period: str) -> float:
        """
        Calculate weighted average of input node values.
        
        Args:
            inputs: List of input nodes
            period: The time period to calculate for
            
        Returns:
            float: Weighted average of input values
            
        Raises:
            ValueError: If inputs list is empty
            ValueError: If weights are provided but don't match inputs length
        """
        if not inputs:
            raise ValueError("Weighted average strategy requires at least one input node")
            
        # Use provided weights or equal weights
        weights = self.weights
        if weights is None:
            # Use equal weights
            weights = [1.0 / len(inputs)] * len(inputs)
        elif len(weights) != len(inputs):
            raise ValueError("Number of weights must match number of inputs")
            
        logger.debug(f"Applying weighted average strategy for period {period}")
        weighted_sum = 0.0
        for input_node, weight in zip(inputs, weights):
            weighted_sum += input_node.calculate(period) * weight
            
        return weighted_sum
    
    @property
    def description(self) -> str:
        return "Weighted Average (weighted sum of inputs)"


class CustomFormulaStrategy(CalculationStrategy):
    """
    Strategy for calculating values based on a custom formula.
    
    This strategy allows defining a custom formula as a function that takes
    input node values and calculates a result.
    """
    
    def __init__(self, formula_function):
        """
        Initialize with a custom formula function.
        
        Args:
            formula_function: Function that takes a dictionary mapping input node names
                             to their values and returns a calculated result
        """
        self.formula_function = formula_function
    
    def calculate(self, inputs: List[Node], period: str) -> float:
        """
        Apply custom formula to input node values.
        
        Args:
            inputs: List of input nodes
            period: The time period to calculate for
            
        Returns:
            float: Result of the custom formula
            
        Raises:
            ValueError: If the formula function raises an error
        """
        # Prepare input values as a dictionary
        input_values = {}
        for i, node in enumerate(inputs):
            if hasattr(node, 'name'):
                input_values[node.name] = node.calculate(period)
            else:
                # Fallback if node has no name
                input_values[f"input_{i}"] = node.calculate(period)
        
        logger.debug(f"Applying custom formula strategy for period {period}")
        try:
            return self.formula_function(input_values)
        except Exception as e:
            logger.error(f"Error applying custom formula: {e}")
            raise ValueError(f"Error in custom formula calculation: {e}")
    
    @property
    def description(self) -> str:
        return "Custom Formula (user-defined calculation)" 