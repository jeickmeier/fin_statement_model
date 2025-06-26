"""Calculation for the Financial Statement Model.

This module provides the Calculation Pattern implementation for calculations,
allowing different calculation types to be encapsulated in calculation classes.

Features:
    - Abstract base class for all calculation strategies.
    - Built-in strategies: Addition, Subtraction, Multiplication, Division, Weighted Average,
      Custom Python function, and Formula string evaluation.
    - All calculations operate on lists of Node objects and a period string.
    - Designed for extensibility: users can add custom calculation types.
    - All exceptions are raised as CalculationError or StrategyError for consistency.

Example:
    >>> from fin_statement_model.core.calculations import AdditionCalculation
    >>> class MockNode:
    ...     def __init__(self, value):
    ...         self._value = value
    ...
    ...     def calculate(self, period):
    ...         return self._value
    >>> nodes = [MockNode(10), MockNode(20)]
    >>> calc = AdditionCalculation()
    >>> calc.calculate(nodes, "2023Q4")
    30.0
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
import logging

from fin_statement_model.core.errors import CalculationError, StrategyError
from fin_statement_model.core.nodes.base import Node  # Absolute

# Configure logging
logger = logging.getLogger(__name__)

# Minimum number of input nodes required for division calculations
MIN_REQUIRED_INPUTS: int = 2


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
            ...     def __init__(self, value):
            ...         self._value = value
            ...
            ...     def calculate(self, period):
            ...         return self._value
            >>> strategy = AdditionCalculation()
            >>> nodes = [MockNode(10), MockNode(20), MockNode(5)]
            >>> strategy.calculate(nodes, "2023")
            35.0
            >>> strategy.calculate([], "2023")
            0.0
        """
        logger.debug("Applying addition calculation for period %s", period)
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
            CalculationError: If the `inputs` list is empty.

        Examples:
            >>> class MockNode:
            ...     def __init__(self, value):
            ...         self._value = value
            ...
            ...     def calculate(self, period):
            ...         return self._value
            >>> strategy = SubtractionCalculation()
            >>> nodes = [MockNode(100), MockNode(20), MockNode(30)]
            >>> strategy.calculate(nodes, "2023")
            50.0
            >>> nodes_single = [MockNode(100)]
            >>> strategy.calculate(nodes_single, "2023")
            100.0
        """
        if not inputs:
            raise CalculationError(
                "Subtraction calculation requires at least one input node",
                details={"strategy": "SubtractionCalculation"},
            )

        logger.debug("Applying subtraction calculation for period %s", period)
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
            ...     def __init__(self, value):
            ...         self._value = value
            ...
            ...     def calculate(self, period):
            ...         return self._value
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

        logger.debug("Applying multiplication calculation for period %s", period)
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
            CalculationError: If the `inputs` list contains fewer than two nodes or if the denominator product is zero.

        Examples:
            >>> class MockNode:
            ...     def __init__(self, value):
            ...         self._value = value
            ...
            ...     def calculate(self, period):
            ...         return self._value
            >>> strategy = DivisionCalculation()
            >>> nodes = [MockNode(100), MockNode(5), MockNode(2)]
            >>> strategy.calculate(nodes, "2023")
            10.0
            >>> nodes_zero_denom = [MockNode(100), MockNode(5), MockNode(0)]
            >>> try:
            ...     strategy.calculate(nodes_zero_denom, "2023")
            ... except CalculationError as e:
            ...     # Example: logging the error instead of printing
            ...     logger.error(e)
            Division by zero: Denominator product is zero
        """
        if len(inputs) < MIN_REQUIRED_INPUTS:
            raise CalculationError(
                "Division calculation requires at least two input nodes",
                details={"strategy": "DivisionCalculation", "input_count": len(inputs)},
            )

        logger.debug("Applying division calculation for period %s", period)

        values = [node.calculate(period) for node in inputs]
        numerator = values[0]

        denominator = 1.0
        for val in values[1:]:
            denominator *= val

        if denominator == 0.0:
            raise CalculationError(
                "Division by zero: Denominator product is zero",
                period=period,
                details={"numerator": numerator, "denominator": denominator},
            )

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

    def __init__(self, weights: list[float] | None = None):
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
        logger.info("Initialized WeightedAverageCalculation with weights: %s", weights)

    def calculate(self, inputs: list[Node], period: str) -> float:
        """Computes the weighted average of the input node values for the period.

        Args:
            inputs: A list of Node objects.
            period: The time period string (e.g., "2023H1") for the calculation.

        Returns:
            The calculated weighted average as a float.

        Raises:
            CalculationError: If the `inputs` list is empty or if the sum of weights is zero.
            StrategyError: If `weights` were provided and length does not match number of inputs.

        Examples:
            >>> class MockNode:
            ...     def __init__(self, value):
            ...         self._value = value
            ...
            ...     def calculate(self, period):
            ...         return self._value
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
            ... except StrategyError as e:
            ...     # Example: logging the error instead of printing
            ...     logger.error(e)
            Number of weights (2) must match number of inputs (3)
        """
        if not inputs:
            raise CalculationError(
                "Weighted average calculation requires at least one input node",
                details={"strategy": "WeightedAverageCalculation"},
            )

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
            logger.debug("Using provided weights: %s", effective_weights)
        else:
            raise StrategyError(
                f"Number of weights ({len(self.weights)}) must match number of inputs ({num_inputs})",
                strategy_type="WeightedAverageCalculation",
            )

        logger.debug("Applying weighted average calculation for period %s", period)
        weighted_sum = 0.0
        total_weight = sum(effective_weights)
        input_values = [node.calculate(period) for node in inputs]

        if total_weight == 0.0:
            # Avoid division by zero. If weights are all zero, the concept is ill-defined.
            # Returning 0 might be a reasonable default, or raising an error.
            # Let's raise ValueError for clarity.
            raise CalculationError(
                "Total weight for weighted average cannot be zero.",
                period=period,
                details={"weights": effective_weights},
            )

        for value, weight in zip(input_values, effective_weights, strict=False):
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
            raise StrategyError(
                "formula_function must be callable",
                strategy_type="CustomFormulaCalculation",
            )
        self.formula_function = formula_function
        logger.info("Initialized CustomFormulaCalculation with function: %s", formula_function.__name__)

    def calculate(self, inputs: list[Node], period: str) -> float:
        """Applies the custom formula function to the calculated input values.

        Args:
            inputs: A list of Node objects.
            period: The time period string (e.g., "2025M1") for the calculation.

        Returns:
            The float result returned by the `formula_function`.

        Raises:
            CalculationError: If the `formula_function` encounters an error during execution
                (e.g., incorrect input keys, calculation errors). Wraps the original exception.

        Examples:
            >>> class MockNode:
            ...     def __init__(self, name, value):
            ...         self.name = name
            ...         self._value = value
            ...
            ...     def calculate(self, period):
            ...         return self._value
            >>> def my_formula(data):
            ...     # Example: Gross Profit Margin
            ...     return (data["revenue"] - data["cogs"]) / data["revenue"] * 100
            >>> strategy = CustomFormulaCalculation(my_formula)
            >>> nodes = [MockNode("revenue", 1000), MockNode("cogs", 600)]
            >>> strategy.calculate(nodes, "2023")
            40.0
            >>> # Example with unnamed nodes
            >>> def simple_sum(data):
            ...     return data["input_0"] + data["input_1"]
            >>> strategy_unnamed = CustomFormulaCalculation(simple_sum)
            >>> nodes_unnamed = [MockNode(None, 10), MockNode(None, 20)]  # No names
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

        logger.debug("Applying custom formula calculation for period %s with inputs: %s", period, input_values)
        try:
            # Execute the user-provided function
            result = self.formula_function(input_values)
            if not isinstance(result, int | float):
                logger.warning(
                    "Custom formula function %s returned non-numeric type: %s. Attempting cast.",
                    self.formula_function.__name__,
                    type(result),
                )
                # Attempt conversion, but be aware this might fail or be lossy
                try:
                    return float(result)
                except (ValueError, TypeError) as cast_err:
                    raise CalculationError(
                        f"Custom formula {self.formula_function.__name__} result "
                        f"({result!r}) could not be cast to float.",
                        period=period,
                        details={
                            "result": result,
                            "result_type": type(result).__name__,
                        },
                    ) from cast_err
            return float(result)  # Ensure result is float
        except Exception as e:
            # Catch any exception from the custom function and wrap it
            logger.exception(
                "Error executing custom formula '%s'",
                self.formula_function.__name__,
            )
            raise CalculationError(
                f"Error in custom formula '{self.formula_function.__name__}': {e}",
                period=period,
                details={"original_error": str(e)},
            ) from e

    @property
    def description(self) -> str:
        """Returns a description of the custom formula calculation."""
        func_name = getattr(self.formula_function, "__name__", "[anonymous function]")
        return f"Custom Formula (using function: {func_name})"


class FormulaCalculation(Calculation):
    """Evaluates a mathematical formula string using *asteval* for safety.

    The class evaluates arithmetic expressions that reference input nodes by the
    variable names supplied in *input_variable_names*. Evaluation is delegated
    to the ``asteval`` interpreter which executes a restricted subset of
    Python's syntax with no access to built-ins or the filesystem, providing a
    safer and more maintainable alternative to a hand-rolled AST walker.

    Attributes:
        formula: The expression string (e.g. ``"a + b / 2"``).
        input_variable_names: Ordered list of variable names corresponding to
            the order of *inputs* passed to :py:meth:`calculate`.
    """

    def __init__(self, formula: str, input_variable_names: list[str]):
        """Initialise the :class:`FormulaCalculation`.

        Args:
            formula: Mathematical expression to evaluate.
            input_variable_names: Names that will map to the provided input
                nodes in the same order.

        Raises:
            StrategyError: If *asteval* is not installed.
        """
        try:
            from asteval import (
                Interpreter,
            )  # local import to avoid hard dep at import time
        except ImportError as exc:  # pragma: no cover - caught by tests if missing
            raise StrategyError(
                "Package 'asteval' is required for FormulaCalculation. Install it via 'pip install asteval'.",
                strategy_type="FormulaCalculation",
            ) from exc

        self.formula = formula
        self.input_variable_names = input_variable_names
        # Prepare a locked-down interpreter: minimal built-ins, no numpy, no print
        self._interpreter_cls = Interpreter  # store class; instance created per calculation
        logger.info(
            "Initialised FormulaCalculation using asteval with formula '%s' and variables %s",
            formula,
            input_variable_names,
        )

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def calculate(self, inputs: list[Node], period: str) -> float:
        """Evaluate *formula* for *period* using values from *inputs*.

        Args:
            inputs: Nodes supplying variable values.
            period: The current period label (e.g. ``"2024Q1"``).

        Returns:
            Evaluated numeric result.

        Raises:
            StrategyError: If the number of *inputs* does not match
                *input_variable_names*.
            CalculationError: If evaluation fails or returns a non-numeric
                result.
        """
        if len(inputs) != len(self.input_variable_names):
            raise StrategyError(
                f"Number of inputs ({len(inputs)}) must match number of variable names "
                f"({len(self.input_variable_names)})",
                strategy_type="FormulaCalculation",
            )

        # Map variable names -> calculated values for the given period
        local_vars: dict[str, float] = {
            name: node.calculate(period) for name, node in zip(self.input_variable_names, inputs, strict=False)
        }

        # Create a fresh interpreter each call to avoid symbol leakage between periods
        from asteval import Interpreter

        ae = Interpreter(symtable={}, minimal=True, no_print=True, use_numpy=False)
        ae.symtable.update(local_vars)

        logger.debug(
            "Evaluating formula '%s' for period %s with variables %s",
            self.formula,
            period,
            local_vars,
        )
        try:
            result = ae(self.formula)
        except Exception as exc:  # pragma: no cover - generic catch to wrap
            logger.exception(
                "Error evaluating formula '%s'",
                self.formula,
            )
            raise CalculationError(
                f"Error evaluating formula: {self.formula}. Error: {exc}",
                period=period,
                details={"formula": self.formula, "original_error": str(exc)},
            ) from exc

        if not isinstance(result, int | float):
            raise CalculationError(
                "Formula result is not numeric.",
                period=period,
                details={"formula": self.formula, "result_type": type(result).__name__},
            )

        return float(result)

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------
    @property
    def description(self) -> str:
        """Return a human-readable description of the calculation."""
        return f"Formula (evaluated via asteval): {self.formula}"


class MetricCalculation(Calculation):
    """Calculation strategy that defers to a formula from metric_registry.

    The constructor accepts *metric_name* (snake_case).  On first use it looks
    up the corresponding :class:`MetricDefinition` from the global
    ``metric_registry`` and internally compiles a :class:`FormulaCalculation`.
    Subsequent calls delegate directly for speed.
    """

    def __init__(self, metric_name: str):
        """Create a MetricCalculation for *metric_name*.

        The metric definition is fetched from the global ``metric_registry`` and
        translated into an internal :class:`FormulaCalculation` so that further
        calls are as fast as any regular formula node.

        Args:
            metric_name: Registry key (snake_case) of the metric to evaluate.
        """
        # Runtime import to avoid heavy dependency when module is first imported.
        from fin_statement_model.core.calculations.calculation import FormulaCalculation
        from fin_statement_model.core.metrics.registry import metric_registry

        self._metric_name = metric_name
        try:
            metric_def = metric_registry.get(metric_name)
        except KeyError as exc:  # pragma: no cover - surfaced at builder time in tests
            raise ValueError(f"Unknown metric '{metric_name}' - ensure metric_registry is loaded.") from exc

        # Build internal FormulaCalculation using metric formula & variable names
        self._formula_calc = FormulaCalculation(metric_def.formula, metric_def.inputs)

    def calculate(self, inputs: list[Node], period: str) -> float:
        """Delegate to internal FormulaCalculation instance."""
        return self._formula_calc.calculate(inputs, period)

    @property
    def description(self) -> str:
        """Short human-readable description used by to_dict()."""
        return f"Metric calculation for '{self._metric_name}'"


# ---------------------------------------------------------------------
# Register aliases with CalculationAliasRegistry (done at import time)
# ---------------------------------------------------------------------
from fin_statement_model.core.node_factory.registries import CalculationAliasRegistry  # noqa: E402  import at end

CalculationAliasRegistry.register("metric", MetricCalculation, overwrite=True)
