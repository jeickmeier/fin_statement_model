"""Strategy for the Financial Statement Model.

This module provides the Strategy Pattern implementation for strategies,
allowing different calculation types to be encapsulated in strategy classes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from fin_statement_model.core.nodes.base import Node  # Absolute

# Configure logging
logger = logging.getLogger(__name__)


class Strategy(ABC):
    """Abstract base class for all calculation strategies.

    This class defines the interface that all concrete calculation strategies must
    implement. It employs the Strategy design pattern, allowing the algorithm
    used by a CalculationNode to be selected at runtime.

    Each concrete strategy encapsulates a specific method for calculating a
    financial value based on a list of input nodes and a given time period.
    """

    @abstractmethod
    def calculate(self, inputs: list[Node], period: str) -> float:
        """Calculate a value based on the input nodes for a specific period.

        This abstract method must be implemented by all concrete strategy classes.
        It defines the core calculation logic for the strategy.

        Args:
            inputs: A list of input Node objects whose values will be used in
                the calculation.
            period: The time period string (e.g., "2023Q1") for which the
                calculation should be performed.

        Returns:
            The calculated numerical value as a float.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
            ValueError: If the inputs are invalid for the specific strategy
                (e.g., wrong number of inputs, incompatible types).
            ZeroDivisionError: If the strategy involves division and a divisor is zero.
            Exception: Potentially other exceptions depending on the specific
                calculation logic.
        """
        # pragma: no cover

    @property
    def description(self) -> str:
        """Provides a human-readable description of the calculation strategy.

        This is useful for documentation, debugging, and potentially for user
        interfaces that need to explain how a value is derived.

        Returns:
            A string describing the strategy.
        """
        # Default implementation returns the class name. Subclasses should override
        # for more specific descriptions.
        class_name = self.__class__.__name__  # pragma: no cover
        return class_name


class AdditionStrategy(Strategy):
    """Implements an addition strategy, summing values from multiple input nodes.

    This strategy calculates the total sum of the values obtained from calling
    the `calculate` method on each of the provided input nodes for a given period.
    """

    def calculate(self, inputs: list[Node], period: str) -> float:
        """Sums the calculated values from all input nodes for the specified period.

        Args:
            inputs: A list of Node objects.
            period: The time period string (e.g., "2023Q4") for the calculation.

        Returns:
            The total sum of the values calculated from the input nodes. Returns
            0.0 if the input list is empty.

        Examples:
            >>> class MockNode:
            ...     def __init__(self, value): self._value = value
            ...     def calculate(self, period): return self._value
            >>> strategy = AdditionStrategy()
            >>> nodes = [MockNode(10), MockNode(20), MockNode(5)]
            >>> strategy.calculate(nodes, "2023")
            35.0
            >>> strategy.calculate([], "2023")
            0.0
        """
        logger.debug(f"Applying addition strategy for period {period}")
        # Using a generator expression for potentially better memory efficiency
        return sum(input_node.calculate(period) for input_node in inputs)

    @property
    def description(self) -> str:
        """Returns a description of the addition strategy."""
        return "Addition (sum of all inputs)"


class SubtractionStrategy(Strategy):
    """Implements a subtraction strategy: first input minus the sum of the rest.

    This strategy takes the calculated value of the first node in the input list
    and subtracts the sum of the calculated values of all subsequent nodes for
    a specific period.
    """

    def calculate(self, inputs: list[Node], period: str) -> float:
        """Calculates the difference: value of the first input minus the sum of others.

        Args:
            inputs: A list of Node objects. Must contain at least one node.
            period: The time period string (e.g., "2024Q1") for the calculation.

        Returns:
            The result of the subtraction. If only one input node is provided,
            its value is returned.

        Raises:
            ValueError: If the `inputs` list is empty.

        Examples:
            >>> class MockNode:
            ...     def __init__(self, value): self._value = value
            ...     def calculate(self, period): return self._value
            >>> strategy = SubtractionStrategy()
            >>> nodes = [MockNode(100), MockNode(20), MockNode(30)]
            >>> strategy.calculate(nodes, "2023")
            50.0
            >>> nodes_single = [MockNode(100)]
            >>> strategy.calculate(nodes_single, "2023")
            100.0
        """
        if not inputs:
            raise ValueError("Subtraction strategy requires at least one input node")

        logger.debug(f"Applying subtraction strategy for period {period}")
        # Calculate values first to avoid multiple calls if nodes are complex
        values = [node.calculate(period) for node in inputs]
        return values[0] - sum(values[1:])

    @property
    def description(self) -> str:
        """Returns a description of the subtraction strategy."""
        return "Subtraction (first input minus sum of subsequent inputs)"


class MultiplicationStrategy(Strategy):
    """Implements a multiplication strategy, calculating the product of input values.

    This strategy multiplies the calculated values of all provided input nodes
    for a given period.
    """

    def calculate(self, inputs: list[Node], period: str) -> float:
        """Calculates the product of the values from all input nodes.

        Args:
            inputs: A list of Node objects.
            period: The time period string (e.g., "2023FY") for the calculation.

        Returns:
            The product of all input values. Returns 1.0 (multiplicative identity)
            if the input list is empty.

        Examples:
            >>> class MockNode:
            ...     def __init__(self, value): self._value = value
            ...     def calculate(self, period): return self._value
            >>> strategy = MultiplicationStrategy()
            >>> nodes = [MockNode(2), MockNode(3), MockNode(4)]
            >>> strategy.calculate(nodes, "2023")
            24.0
            >>> strategy.calculate([], "2023")
            1.0
        """
        # Multiplication strategy should ideally return 1.0 for empty inputs.
        # Raising error if empty seems less conventional for multiplication.
        if not inputs:
            logger.warning("Multiplication strategy called with empty inputs, returning 1.0")
            return 1.0

        logger.debug(f"Applying multiplication strategy for period {period}")
        result = 1.0
        for input_node in inputs:
            result *= input_node.calculate(period)
        return result

    @property
    def description(self) -> str:
        """Returns a description of the multiplication strategy."""
        return "Multiplication (product of all inputs)"


class DivisionStrategy(Strategy):
    """Implements a division strategy: first input divided by the product of the rest.

    This strategy takes the calculated value of the first node (numerator) and
    divides it by the product of the calculated values of all subsequent nodes
    (denominator) for a specific period.
    """

    def calculate(self, inputs: list[Node], period: str) -> float:
        """Calculates the division: first input / (product of subsequent inputs).

        Args:
            inputs: A list of Node objects. Must contain at least two nodes.
            period: The time period string (e.g., "2024Q2") for the calculation.

        Returns:
            The result of the division.

        Raises:
            ValueError: If `inputs` list contains fewer than two nodes.
            ZeroDivisionError: If the calculated product of the subsequent nodes
                (denominator) is zero.

        Examples:
            >>> class MockNode:
            ...     def __init__(self, value): self._value = value
            ...     def calculate(self, period): return self._value
            >>> strategy = DivisionStrategy()
            >>> nodes = [MockNode(100), MockNode(5), MockNode(2)]
            >>> strategy.calculate(nodes, "2023")
            10.0
            >>> nodes_zero_denom = [MockNode(100), MockNode(5), MockNode(0)]
            >>> try:
            ...     strategy.calculate(nodes_zero_denom, "2023")
            ... except ZeroDivisionError as e:
            ...     print(e)
            Division by zero: Denominator product is zero
        """
        if len(inputs) < 2:
            raise ValueError("Division strategy requires at least two input nodes")

        logger.debug(f"Applying division strategy for period {period}")

        values = [node.calculate(period) for node in inputs]
        numerator = values[0]

        denominator = 1.0
        for val in values[1:]:
            denominator *= val

        if denominator == 0.0:
            raise ZeroDivisionError("Division by zero: Denominator product is zero")

        return numerator / denominator

    @property
    def description(self) -> str:
        """Returns a description of the division strategy."""
        return "Division (first input / product of subsequent inputs)"


class WeightedAverageStrategy(Strategy):
    """Calculates the weighted average of input node values.

    This strategy computes the average of the values from input nodes, where each
    node's contribution is weighted. If no weights are provided during
    initialization, it defaults to an equal weighting (simple average).
    """

    def __init__(self, weights: Optional[list[float]] = None):
        """Initializes the WeightedAverageStrategy.

        Args:
            weights: An optional list of floats representing the weight for each
                corresponding input node. The length of this list must match the
                number of input nodes provided to the `calculate` method. If None,
                equal weights are assumed.
        """
        # Validate weights if provided immediately? No, validation happens in calculate
        # as the number of inputs isn't known here.
        self.weights = weights
        logger.info(f"Initialized WeightedAverageStrategy with weights: {weights}")

    def calculate(self, inputs: list[Node], period: str) -> float:
        """Computes the weighted average of the input node values for the period.

        Args:
            inputs: A list of Node objects.
            period: The time period string (e.g., "2023H1") for the calculation.

        Returns:
            The calculated weighted average as a float.

        Raises:
            ValueError: If the `inputs` list is empty.
            ValueError: If `weights` were provided during initialization and their
                count does not match the number of `inputs`.
            ValueError: If the sum of weights is zero (to prevent division by zero
                if normalization were implemented differently).

        Examples:
            >>> class MockNode:
            ...     def __init__(self, value): self._value = value
            ...     def calculate(self, period): return self._value
            >>> # Equal weights (simple average)
            >>> strategy_equal = WeightedAverageStrategy()
            >>> nodes = [MockNode(10), MockNode(20), MockNode(30)]
            >>> strategy_equal.calculate(nodes, "2023")
            20.0
            >>> # Custom weights
            >>> strategy_custom = WeightedAverageStrategy(weights=[0.5, 0.3, 0.2])
            >>> strategy_custom.calculate(nodes, "2023")
            17.0
            >>> # Mismatched weights
            >>> strategy_mismatch = WeightedAverageStrategy(weights=[0.5, 0.5])
            >>> try:
            ...     strategy_mismatch.calculate(nodes, "2023")
            ... except ValueError as e:
            ...     print(e)
            Number of weights (2) must match number of inputs (3)
        """
        if not inputs:
            raise ValueError("Weighted average strategy requires at least one input node")

        num_inputs = len(inputs)
        effective_weights: list[float]

        if self.weights is None:
            # Use equal weights if none provided
            if num_inputs == 0:  # Should be caught by the check above, but defensive
                return 0.0
            equal_weight = 1.0 / num_inputs
            effective_weights = [equal_weight] * num_inputs
            logger.debug("Using equal weights for weighted average.")
        elif len(self.weights) == num_inputs:
            effective_weights = self.weights
            logger.debug(f"Using provided weights: {effective_weights}")
        else:
            raise ValueError(
                f"Number of weights ({len(self.weights)}) must match "
                f"number of inputs ({num_inputs})"
            )

        logger.debug(f"Applying weighted average strategy for period {period}")
        weighted_sum = 0.0
        total_weight = sum(effective_weights)
        input_values = [node.calculate(period) for node in inputs]

        if total_weight == 0.0:
            # Avoid division by zero. If weights are all zero, the concept is ill-defined.
            # Returning 0 might be a reasonable default, or raising an error.
            # Let's raise ValueError for clarity.
            raise ValueError("Total weight for weighted average cannot be zero.")

        for value, weight in zip(input_values, effective_weights):
            weighted_sum += value * weight

        # If weights don't sum to 1, this isn't a standard weighted average.
        # Decide whether to normalize or return the weighted sum directly.
        # Normalize by total weight for a true weighted average.
        return weighted_sum / total_weight

    @property
    def description(self) -> str:
        """Returns a description of the weighted average strategy."""
        if self.weights:
            return f"Weighted Average (using provided weights: {self.weights})"
        else:
            return "Weighted Average (using equal weights)"


# Type alias for the custom formula function
FormulaFunc = Callable[[dict[str, float]], float]


class CustomFormulaStrategy(Strategy):
    """Executes a user-defined Python function to calculate a value.

    This strategy provides maximum flexibility by allowing any custom Python
    function to be used for calculation. The function receives a dictionary
    mapping input node names (or fallback names) to their calculated values
    for the period and should return a single float result.
    """

    def __init__(self, formula_function: FormulaFunc):
        """Initializes the CustomFormulaStrategy with a calculation function.

        Args:
            formula_function: A callable (function, lambda, etc.) that accepts
                a single argument: a dictionary mapping string keys (input node
                names or `input_<i>`) to their float values for the period.
                It must return a float.

        Raises:
            TypeError: If `formula_function` is not callable.
        """
        if not callable(formula_function):
            raise TypeError("formula_function must be callable")
        self.formula_function = formula_function
        logger.info(f"Initialized CustomFormulaStrategy with function: {formula_function.__name__}")

    def calculate(self, inputs: list[Node], period: str) -> float:
        """Applies the custom formula function to the calculated input values.

        Args:
            inputs: A list of Node objects.
            period: The time period string (e.g., "2025M1") for the calculation.

        Returns:
            The float result returned by the `formula_function`.

        Raises:
            ValueError: If the `formula_function` encounters an error during execution
                (e.g., incorrect input keys, calculation errors). Wraps the original
                exception.

        Examples:
            >>> class MockNode:
            ...     def __init__(self, name, value): self.name = name; self._value = value
            ...     def calculate(self, period): return self._value
            >>> def my_formula(data):
            ...     # Example: Gross Profit Margin
            ...     return (data['revenue'] - data['cogs']) / data['revenue'] * 100
            >>> strategy = CustomFormulaStrategy(my_formula)
            >>> nodes = [MockNode('revenue', 1000), MockNode('cogs', 600)]
            >>> strategy.calculate(nodes, "2023")
            40.0
            >>> # Example with unnamed nodes
            >>> def simple_sum(data):
            ...     return data['input_0'] + data['input_1']
            >>> strategy_unnamed = CustomFormulaStrategy(simple_sum)
            >>> nodes_unnamed = [MockNode(None, 10), MockNode(None, 20)] # No names
            >>> strategy_unnamed.calculate(nodes_unnamed, "2023")
            30.0
        """
        # Prepare input values dictionary, using names if available
        input_values: dict[str, float] = {}
        for i, node in enumerate(inputs):
            # Prefer node.name if it exists and is a non-empty string
            key = getattr(node, "name", None)
            if not isinstance(key, str) or not key:
                key = f"input_{i}"
            input_values[key] = node.calculate(period)

        logger.debug(
            f"Applying custom formula strategy for period {period} with inputs: {input_values}"
        )
        try:
            # Execute the user-provided function
            result = self.formula_function(input_values)
            if not isinstance(result, (int, float)):
                logger.warning(
                    f"Custom formula function {self.formula_function.__name__} "
                    f"returned non-numeric type: {type(result)}. Attempting cast."
                )
                # Attempt conversion, but be aware this might fail or be lossy
                try:
                    return float(result)
                except (ValueError, TypeError) as cast_err:
                    raise ValueError(
                        f"Custom formula {self.formula_function.__name__} result "
                        f"({result!r}) could not be cast to float."
                    ) from cast_err
            return float(result)  # Ensure result is float
        except Exception as e:
            # Catch any exception from the custom function and wrap it
            logger.error(
                f"Error executing custom formula '{self.formula_function.__name__}': {e}",
                exc_info=True,
            )
            raise ValueError(
                f"Error in custom formula '{self.formula_function.__name__}': {e}"
            ) from e

    @property
    def description(self) -> str:
        """Returns a description of the custom formula strategy."""
        func_name = getattr(self.formula_function, "__name__", "[anonymous function]")
        return f"Custom Formula (using function: {func_name})"
