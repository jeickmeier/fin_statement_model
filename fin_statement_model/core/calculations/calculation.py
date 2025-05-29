"""Calculation for the Financial Statement Model.

This module provides the Calculation Pattern implementation for calculations,
allowing different calculation types to be encapsulated in calculation classes.
"""

from abc import ABC, abstractmethod
import ast
import logging
import operator
from typing import Optional, ClassVar
from collections.abc import Callable

from fin_statement_model.core.nodes.base import Node  # Absolute

# Configure logging
logger = logging.getLogger(__name__)


class Calculation(ABC):
    """Abstract base class for all calculations.

    This class defines the interface that all concrete calculation classes must
    implement. It employs a calculation pattern, allowing the algorithm
    used by a CalculationNode to be selected at runtime.

    Each concrete calculation encapsulates a specific method for computing a
    financial value based on a list of input nodes and a given time period.
    """

    @abstractmethod
    def calculate(self, inputs: list[Node], period: str) -> float:
        """Calculate a value based on input nodes for a specific period.

        This abstract method must be implemented by all concrete calculation classes.
        It defines the core logic for the calculation.

        Args:
            inputs: A list of input Node objects whose values will be used in
                the calculation.
            period: The time period string (e.g., "2023Q1") for which the
                calculation should be performed.

        Returns:
            The calculated numerical value as a float.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
            ValueError: If the inputs are invalid for the specific calculation
                (e.g., wrong number of inputs, incompatible types).
            ZeroDivisionError: If the calculation involves division and a divisor
                is zero.
            Exception: Other exceptions depending on the calculation logic.
        """
        # pragma: no cover

    @property
    def description(self) -> str:
        """Provides a human-readable description of the calculation.

        This is useful for documentation, debugging, and for user interfaces
        that need to explain how a value is derived.

        Returns:
            A string describing the calculation.
        """
        # Default implementation returns the class name. Subclasses should override
        # for more specific descriptions.
        class_name = self.__class__.__name__  # pragma: no cover
        return class_name


class AdditionCalculation(Calculation):
    """Implements an addition calculation, summing values from multiple input nodes.

    This calculation sums the values obtained from calling
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
            >>> strategy = AdditionCalculation()
            >>> nodes = [MockNode(10), MockNode(20), MockNode(5)]
            >>> strategy.calculate(nodes, "2023")
            35.0
            >>> strategy.calculate([], "2023")
            0.0
        """
        logger.debug(f"Applying addition calculation for period {period}")
        # Using a generator expression for potentially better memory efficiency
        return sum(input_node.calculate(period) for input_node in inputs)

    @property
    def description(self) -> str:
        """Returns a description of the addition calculation."""
        return "Addition (sum of all inputs)"


class SubtractionCalculation(Calculation):
    """Implements a subtraction calculation: first input minus the sum of the rest.

    This calculation takes the calculated value of the first node in the input list
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
            >>> strategy = SubtractionCalculation()
            >>> nodes = [MockNode(100), MockNode(20), MockNode(30)]
            >>> strategy.calculate(nodes, "2023")
            50.0
            >>> nodes_single = [MockNode(100)]
            >>> strategy.calculate(nodes_single, "2023")
            100.0
        """
        if not inputs:
            raise ValueError("Subtraction calculation requires at least one input node")

        logger.debug(f"Applying subtraction calculation for period {period}")
        # Calculate values first to avoid multiple calls if nodes are complex
        values = [node.calculate(period) for node in inputs]
        return values[0] - sum(values[1:])

    @property
    def description(self) -> str:
        """Returns a description of the subtraction calculation."""
        return "Subtraction (first input minus sum of subsequent inputs)"


class MultiplicationCalculation(Calculation):
    """Implements a multiplication calculation, calculating the product of input values.

    This calculation multiplies the calculated values of all provided input nodes
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
            >>> strategy = MultiplicationCalculation()
            >>> nodes = [MockNode(2), MockNode(3), MockNode(4)]
            >>> strategy.calculate(nodes, "2023")
            24.0
            >>> strategy.calculate([], "2023")
            1.0
        """
        # Multiplication calculation should ideally return 1.0 for empty inputs.
        # Raising error if empty seems less conventional for multiplication.
        if not inputs:
            logger.warning("Multiplication calculation called with empty inputs, returning 1.0")
            return 1.0

        logger.debug(f"Applying multiplication calculation for period {period}")
        result = 1.0
        for input_node in inputs:
            result *= input_node.calculate(period)
        return result

    @property
    def description(self) -> str:
        """Returns a description of the multiplication calculation."""
        return "Multiplication (product of all inputs)"


class DivisionCalculation(Calculation):
    """Implements a division calculation: first input divided by the product of the rest.

    This calculation takes the calculated value of the first node (numerator) and
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
            >>> strategy = DivisionCalculation()
            >>> nodes = [MockNode(100), MockNode(5), MockNode(2)]
            >>> strategy.calculate(nodes, "2023")
            10.0
            >>> nodes_zero_denom = [MockNode(100), MockNode(5), MockNode(0)]
            >>> try:
            ...     strategy.calculate(nodes_zero_denom, "2023")
            ... except ZeroDivisionError as e:
            ...     # Example: logging the error instead of printing
            ...     logger.error(e)
            Division by zero: Denominator product is zero
        """
        if len(inputs) < 2:
            raise ValueError("Division calculation requires at least two input nodes")

        logger.debug(f"Applying division calculation for period {period}")

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
        """Returns a description of the division calculation."""
        return "Division (first input / product of subsequent inputs)"


class WeightedAverageCalculation(Calculation):
    """Calculates the weighted average of input node values.

    This calculation computes the average of the values from input nodes, where each
    node's contribution is weighted. If no weights are provided during
    initialization, it defaults to an equal weighting (simple average).
    """

    def __init__(self, weights: Optional[list[float]] = None):
        """Initializes the WeightedAverageCalculation.

        Args:
            weights: An optional list of floats representing the weight for each
                corresponding input node. The length of this list must match the
                number of input nodes provided to the `calculate` method. If None,
                equal weights are assumed.
        """
        # Validate weights if provided immediately? No, validation happens in calculate
        # as the number of inputs isn't known here.
        self.weights = weights
        logger.info(f"Initialized WeightedAverageCalculation with weights: {weights}")

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
            >>> strategy_equal = WeightedAverageCalculation()
            >>> nodes = [MockNode(10), MockNode(20), MockNode(30)]
            >>> strategy_equal.calculate(nodes, "2023")
            20.0
            >>> # Custom weights
            >>> strategy_custom = WeightedAverageCalculation(weights=[0.5, 0.3, 0.2])
            >>> strategy_custom.calculate(nodes, "2023")
            17.0
            >>> # Mismatched weights
            >>> strategy_mismatch = WeightedAverageCalculation(weights=[0.5, 0.5])
            >>> try:
            ...     strategy_mismatch.calculate(nodes, "2023")
            ... except ValueError as e:
            ...     # Example: logging the error instead of printing
            ...     logger.error(e)
            Number of weights (2) must match number of inputs (3)
        """
        if not inputs:
            raise ValueError("Weighted average calculation requires at least one input node")

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

        logger.debug(f"Applying weighted average calculation for period {period}")
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
        """Returns a description of the weighted average calculation."""
        if self.weights:
            return f"Weighted Average (using provided weights: {self.weights})"
        else:
            return "Weighted Average (using equal weights)"


# Type alias for the custom formula function
FormulaFunc = Callable[[dict[str, float]], float]


class CustomFormulaCalculation(Calculation):
    """Executes a user-defined Python function to calculate a value.

    This calculation provides maximum flexibility by allowing any custom Python
    function to be used for calculation. The function receives a dictionary
    mapping input node names (or fallback names) to their calculated values
    for the period and should return a single float result.
    """

    def __init__(self, formula_function: FormulaFunc):
        """Initializes the CustomFormulaCalculation with a calculation function.

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
        logger.info(
            f"Initialized CustomFormulaCalculation with function: {formula_function.__name__}"
        )

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
            >>> strategy = CustomFormulaCalculation(my_formula)
            >>> nodes = [MockNode('revenue', 1000), MockNode('cogs', 600)]
            >>> strategy.calculate(nodes, "2023")
            40.0
            >>> # Example with unnamed nodes
            >>> def simple_sum(data):
            ...     return data['input_0'] + data['input_1']
            >>> strategy_unnamed = CustomFormulaCalculation(simple_sum)
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
            f"Applying custom formula calculation for period {period} with inputs: {input_values}"
        )
        try:
            # Execute the user-provided function
            result = self.formula_function(input_values)
            if not isinstance(result, int | float):
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
        """Returns a description of the custom formula calculation."""
        func_name = getattr(self.formula_function, "__name__", "[anonymous function]")
        return f"Custom Formula (using function: {func_name})"


class FormulaCalculation(Calculation):
    """Evaluates a mathematical formula string as a calculation strategy.

    This calculation parses and evaluates simple mathematical expressions
    involving input nodes. Supports basic arithmetic operators (+, -, *, /)
    and unary negation.

    Attributes:
        formula: The mathematical expression string to evaluate.
        input_variable_names: List of variable names used in the formula,
            corresponding to the order of input nodes.
        _ast: The parsed Abstract Syntax Tree of the formula.
    """

    # Supported AST operators mapping to Python operator functions
    OPERATORS: ClassVar[dict[type, Callable[[float, float], float]]] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.USub: operator.neg,  # type: ignore[dict-item]
    }

    def __init__(self, formula: str, input_variable_names: list[str]):
        """Initialize the FormulaCalculation.

        Args:
            formula: The mathematical formula string (e.g., "a + b / 2").
            input_variable_names: List of variable names used in the formula,
                in the same order as the input nodes that will be provided
                to the calculate method.

        Raises:
            ValueError: If the formula string has invalid syntax.
        """
        self.formula = formula
        self.input_variable_names = input_variable_names
        try:
            # Parse the formula string into an AST expression
            self._ast = ast.parse(formula, mode="eval").body
        except SyntaxError as e:
            raise ValueError(f"Invalid formula syntax: {formula}") from e
        logger.info(
            f"Initialized FormulaCalculation with formula: {formula} and variables: {input_variable_names}"
        )

    def calculate(self, inputs: list[Node], period: str) -> float:
        """Calculate the value by evaluating the formula with input node values.

        Args:
            inputs: A list of Node objects, in the same order as input_variable_names.
            period: The time period string for the calculation.

        Returns:
            The result of the formula evaluation.

        Raises:
            ValueError: If the number of inputs doesn't match input_variable_names,
                or if an error occurs during evaluation.
        """
        if len(inputs) != len(self.input_variable_names):
            raise ValueError(
                f"Number of inputs ({len(inputs)}) must match number of variable names "
                f"({len(self.input_variable_names)})"
            )

        # Create mapping of variable names to nodes
        variable_map = dict(zip(self.input_variable_names, inputs))

        logger.debug(f"Applying formula calculation for period {period}")
        try:
            return self._evaluate(self._ast, period, variable_map)
        except (ValueError, TypeError, KeyError, ZeroDivisionError) as e:
            raise ValueError(f"Error evaluating formula: {self.formula}. Error: {e!s}") from e

    def _evaluate(self, node: ast.AST, period: str, variable_map: dict[str, Node]) -> float:
        """Recursively evaluate the parsed AST node for the formula.

        Args:
            node: The current AST node to evaluate.
            period: The time period context for the evaluation.
            variable_map: Mapping of variable names to Node objects.

        Returns:
            The result of evaluating the AST node.

        Raises:
            TypeError: If a non-numeric constant or input node value is encountered.
            ValueError: If an unknown variable or unsupported operator/syntax is found.
            ZeroDivisionError: If division by zero occurs.
        """
        # Numeric literal (Constant in Python 3.8+)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, int | float):
                return float(node.value)
            else:
                raise TypeError(
                    f"Unsupported constant type '{type(node.value).__name__}' in formula"
                )

        # Variable reference
        elif isinstance(node, ast.Name):
            var_name = node.id
            if var_name not in variable_map:
                raise ValueError(
                    f"Unknown variable '{var_name}' in formula. Available: {list(variable_map.keys())}"
                )
            input_node = variable_map[var_name]
            # Recursively calculate the value of the input node
            value = input_node.calculate(period)
            if not isinstance(value, int | float):
                raise TypeError(
                    f"Input node '{input_node.name}' (variable '{var_name}') did not return a numeric value for period '{period}'"
                )
            return float(value)

        # Binary operation (e.g., a + b)
        elif isinstance(node, ast.BinOp):
            left_val = self._evaluate(node.left, period, variable_map)
            right_val = self._evaluate(node.right, period, variable_map)
            op_type = type(node.op)
            if op_type not in self.OPERATORS:
                raise ValueError(f"Unsupported binary operator '{op_type.__name__}' in formula")
            # Perform the operation
            return float(self.OPERATORS[op_type](left_val, right_val))

        # Unary operation (e.g., -a)
        elif isinstance(node, ast.UnaryOp):
            operand_val = self._evaluate(node.operand, period, variable_map)
            op_type = type(node.op)
            if op_type not in self.OPERATORS:
                raise ValueError(f"Unsupported unary operator '{op_type.__name__}' in formula")
            # Perform the operation
            return float(self.OPERATORS[op_type](operand_val))

        # If the node type is unsupported
        else:
            raise TypeError(
                f"Unsupported syntax node type '{type(node).__name__}' in formula: {ast.dump(node)}"
            )

    @property
    def description(self) -> str:
        """Returns a description of the formula calculation."""
        return f"Formula: {self.formula}"
