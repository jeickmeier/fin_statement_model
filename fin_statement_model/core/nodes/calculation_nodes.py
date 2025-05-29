"""Provide node implementations for performing calculations in the financial statement model.

This module defines the different types of calculation nodes available in the system:
- FormulaCalculationNode: Evaluates a formula expression string (e.g., "a + b / 2")
- CalculationNode: Uses a calculation object for calculation logic
- CustomCalculationNode: Calculates using a Python callable/function
"""

from typing import Optional, Any
from collections.abc import Callable

from fin_statement_model.core.calculations.calculation import (
    Calculation,
    FormulaCalculation,
)
from fin_statement_model.core.errors import (
    CalculationError,
)
from fin_statement_model.core.nodes.base import Node


# === CalculationNode ===


class CalculationNode(Node):
    """Delegate calculation logic to a separate calculation object.

    Uses a calculation object. The actual calculation algorithm is
    encapsulated in a `calculation` object provided during initialization.
    This allows for flexible and interchangeable calculation logic.

    Attributes:
        name (str): Identifier for this node.
        inputs (List[Node]): A list of input nodes required by the calculation.
        calculation (Any): An object possessing a `calculate(inputs: List[Node], period: str) -> float` method.
        _values (Dict[str, float]): Internal cache for calculated results.

    Examples:
        >>> class SumCalculation:
        ...     def calculate(self, inputs: List[Node], period: str) -> float:
        ...         return sum(node.calculate(period) for node in inputs)
        >>> node_a = FinancialStatementItemNode("a", {"2023": 10})
        >>> node_b = FinancialStatementItemNode("b", {"2023": 20})
        >>> sum_node = CalculationNode(
        ...     "sum_ab",
        ...     inputs=[node_a, node_b],
        ...     calculation=SumCalculation()
        ... )
        >>> print(sum_node.calculate("2023"))
        30.0
    """

    def __init__(
        self, name: str, inputs: list[Node], calculation: Calculation, **kwargs: Any
    ):
        """Initialize the CalculationNode.

        Args:
            name (str): The unique identifier for this node.
            inputs (List[Node]): List of input nodes needed by the calculation.
            calculation (Any): The calculation object implementing the calculation.
                Must have a `calculate` method.
            **kwargs: Additional attributes to store on the node (e.g., metric_name, metric_description).

        Raises:
            TypeError: If `inputs` is not a list of Nodes, or if `calculation`
                does not have a callable `calculate` method.
        """
        super().__init__(name)
        if not isinstance(inputs, list) or not all(isinstance(n, Node) for n in inputs):
            raise TypeError("CalculationNode inputs must be a list of Node instances.")
        if not hasattr(calculation, "calculate") or not callable(
            getattr(calculation, "calculate")
        ):
            raise TypeError(
                "Calculation object must have a callable 'calculate' method."
            )

        self.inputs = inputs
        self.calculation = calculation
        self._values: dict[str, float] = {}  # Cache for calculated values

        # Store any additional attributes passed via kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)

    def calculate(self, period: str) -> float:
        """Calculate the value for a period using the assigned calculation.

        Checks the cache first. If not found, delegates to the calculation's
        `calculate` method and stores the result.

        Args:
            period (str): The time period for the calculation.

        Returns:
            float: The calculated value from the calculation.

        Raises:
            CalculationError: If the calculation fails or returns
                a non-numeric value.
        """
        if period in self._values:
            return self._values[period]

        try:
            # Delegate to the calculation object's calculate method
            result = self.calculation.calculate(self.inputs, period)
            if not isinstance(result, int | float):
                raise TypeError(
                    f"Calculation for node '{self.name}' did not return a numeric value (got {type(self.calculation).__name__})."
                )
            # Cache and return the result
            self._values[period] = float(result)
            return self._values[period]
        except Exception as e:
            # Wrap potential errors from the calculation
            raise CalculationError(
                message=f"Error during calculation for node '{self.name}'",
                node_id=self.name,
                period=period,
                details={
                    "calculation": type(self.calculation).__name__,
                    "error": str(e),
                },
            ) from e

    def set_calculation(self, calculation: Calculation) -> None:
        """Change the calculation object for the node.

        Args:
            calculation (Any): The new calculation object. Must have a callable
                `calculate` method.

        Raises:
            TypeError: If the new calculation is invalid.
        """
        if not hasattr(calculation, "calculate") or not callable(
            getattr(calculation, "calculate")
        ):
            raise TypeError(
                "New calculation object must have a callable 'calculate' method."
            )
        self.calculation = calculation
        self.clear_cache()  # Clear cache as logic has changed

    def clear_cache(self) -> None:
        """Clear the internal cache of calculated values.

        Returns:
            None
        """
        self._values.clear()

    def get_dependencies(self) -> list[str]:
        """Return the names of input nodes used by the calculation.

        Returns:
            A list of input node names.
        """
        return [node.name for node in self.inputs]

    def has_calculation(self) -> bool:
        """Indicate that this node performs calculation.

        Returns:
            True, as CalculationNode performs calculations.
        """
        return True


# === FormulaCalculationNode ===


class FormulaCalculationNode(CalculationNode):
    """Calculate a value based on a mathematical formula string.

    This node extends CalculationNode and uses a FormulaCalculation strategy
    internally to parse and evaluate mathematical expressions.

    Attributes:
        name (str): Identifier for this node.
        inputs (Dict[str, Node]): Mapping of variable names used in the formula
            to their corresponding input Node instances.
        formula (str): The mathematical expression string to evaluate (e.g., "a + b").
        metric_name (Optional[str]): The original metric identifier from the registry, if applicable.
        metric_description (Optional[str]): The description from the metric definition, if applicable.

    Examples:
        >>> # Assume revenue and cogs are Node instances
        >>> revenue = FinancialStatementItemNode("revenue", {"2023": 100})
        >>> cogs = FinancialStatementItemNode("cogs", {"2023": 60})
        >>> gross_profit = FormulaCalculationNode(
        ...     "gross_profit",
        ...     inputs={"rev": revenue, "cost": cogs},
        ...     formula="rev - cost"
        ... )
        >>> print(gross_profit.calculate("2023"))
        40.0
    """

    def __init__(
        self,
        name: str,
        inputs: dict[str, Node],
        formula: str,
        metric_name: Optional[str] = None,
        metric_description: Optional[str] = None,
    ):
        """Initialize the FormulaCalculationNode.

        Args:
            name (str): The unique identifier for this node.
            inputs (Dict[str, Node]): Dictionary mapping variable names in the
                formula to the corresponding input nodes.
            formula (str): The mathematical formula string.
            metric_name (Optional[str]): The original metric identifier from the
                registry, if this node represents a defined metric. Defaults to None.
            metric_description (Optional[str]): The description from the metric
                definition, if applicable. Defaults to None.

        Raises:
            ValueError: If the formula string has invalid syntax.
            TypeError: If any value in `inputs` is not a Node instance.
        """
        if not isinstance(inputs, dict) or not all(
            isinstance(n, Node) for n in inputs.values()
        ):
            raise TypeError(
                "FormulaCalculationNode inputs must be a dict of Node instances."
            )

        # Store the formula and metric attributes
        self.formula = formula
        self.metric_name = metric_name
        self.metric_description = metric_description

        # Extract variable names and input nodes in consistent order
        input_variable_names = list(inputs.keys())
        input_nodes = list(inputs.values())

        # Create FormulaCalculation strategy
        formula_calculation = FormulaCalculation(formula, input_variable_names)

        # Initialize parent CalculationNode with the strategy
        super().__init__(name, input_nodes, formula_calculation)

        # Store the inputs dict for compatibility (separate from parent's inputs list)
        self.inputs_dict = inputs

    def get_dependencies(self) -> list[str]:
        """Return the names of input nodes used in the formula.

        Returns:
            A list of variable names corresponding to the formula inputs.
        """
        return [node.name for node in self.inputs_dict.values()]

    def has_calculation(self) -> bool:
        """Indicate that this node performs calculation.

        Returns:
            True, as FormulaCalculationNode performs calculations.
        """
        return True


# === CustomCalculationNode ===


class CustomCalculationNode(Node):
    """Calculate a value using a Python callable/function.

    Uses a Python callable/function to calculate the value for a node.
    The function is provided during initialization.

    Attributes:
        name (str): Identifier for this node.
        inputs (List[Node]): List of input nodes needed for calculation.
        formula_func (Callable): The Python callable function to use for calculation.
        description (str, optional): Description of what this calculation does.
        _values (Dict[str, float]): Internal cache for calculated results.

    Examples:
        >>> def custom_calculation(a, b):
        ...     return a + b
        >>> node_a = FinancialStatementItemNode("NodeA", values={"2023": 10.0})
        >>> node_b = FinancialStatementItemNode("NodeB", values={"2023": 5.0})
        >>> node = CustomCalculationNode(
        ...     "custom_calc",
        ...     inputs=[node_a, node_b],
        ...     formula_func=custom_calculation
        ... )
        >>> print(node.calculate("2023"))
        15.0
    """

    def __init__(
        self,
        name: str,
        inputs: list[Node],
        formula_func: Callable,
        description: Optional[str] = None,
    ):
        """Initialize the CustomCalculationNode.

        Args:
            name (str): The unique identifier for this node.
            inputs (List[Node]): The input nodes whose values will be passed to formula_func.
            formula_func (Callable): The Python callable function to use for calculation.
            description (str, optional): Description of what this calculation does.

        Raises:
            TypeError: If `inputs` is not a list of Nodes or `formula_func` is not a callable.
        """
        super().__init__(name)
        if not isinstance(inputs, list) or not all(isinstance(n, Node) for n in inputs):
            raise TypeError(
                "CustomCalculationNode inputs must be a list of Node instances"
            )
        if not callable(formula_func):
            raise TypeError(
                "CustomCalculationNode formula_func must be a callable function"
            )

        self.inputs = inputs
        self.formula_func = formula_func
        self.description = description
        self._values: dict[str, float] = {}  # Cache for calculated results

    def calculate(self, period: str) -> float:
        """Calculate the node's value for a period using the provided function.

        Args:
            period (str): The time period for which to perform the calculation.

        Returns:
            float: The calculated value from the function.

        Raises:
            CalculationError: If an error occurs during calculation, such as
                if an input node fails to provide a numeric value for the period.
        """
        if period in self._values:
            return self._values[period]

        try:
            # Get input values
            input_values = []
            for node in self.inputs:
                value = node.calculate(period)
                if not isinstance(value, int | float):
                    raise TypeError(
                        f"Input node '{node.name}' did not return a numeric value for period '{period}'. Got {type(value).__name__}."
                    )
                input_values.append(value)

            # Calculate the value using the provided function
            result = self.formula_func(*input_values)
            if not isinstance(result, int | float):
                raise TypeError(
                    f"Formula did not return a numeric value. Got {type(result).__name__}."
                )

            # Cache and return the result
            self._values[period] = float(result)
            return self._values[period]
        except Exception as e:
            # Wrap potential errors from the function
            raise CalculationError(
                message=f"Error during custom calculation for node '{self.name}'",
                node_id=self.name,
                period=period,
                details={"function": self.formula_func.__name__, "error": str(e)},
            ) from e

    def get_dependencies(self) -> list[str]:
        """Return the names of input nodes used in the function.

        Returns:
            A list of input node names.
        """
        return [node.name for node in self.inputs]

    def has_calculation(self) -> bool:
        """Indicate that this node performs calculation.

        Returns:
            True, as CustomCalculationNode performs calculations.
        """
        return True
