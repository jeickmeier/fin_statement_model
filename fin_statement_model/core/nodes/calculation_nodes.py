"""Provide node implementations for performing calculations in the financial statement model.

This module defines the different types of calculation nodes available in the system:
- FormulaCalculationNode: Evaluates a formula expression string (e.g., "a + b / 2")
- CalculationNode: Uses a calculation object for calculation logic
- MetricCalculationNode: Calculates a registered financial metric
- CustomCalculationNode: Calculates using a Python callable/function
"""

import ast
import operator
from typing import Callable, Optional, ClassVar

from fin_statement_model.core.calculations.calculation import Calculation
from fin_statement_model.core.errors import (
    CalculationError,
    ConfigurationError,
    MetricError,
)
from fin_statement_model.core.metrics import metric_registry
from fin_statement_model.core.nodes.base import Node

# === FormulaCalculationNode ===


class FormulaCalculationNode(Node):
    """Calculate a value based on a mathematical formula string.

    Parses and evaluates simple mathematical expressions involving input nodes.
    Supports basic arithmetic operators (+, -, *, /) and unary negation.

    Attributes:
        name (str): Identifier for this node.
        inputs (Dict[str, Node]): Mapping of variable names used in the formula
            to their corresponding input Node instances.
        formula (str): The mathematical expression string to evaluate (e.g., "a + b").
        _ast (ast.Expression): The parsed Abstract Syntax Tree of the formula.

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

    # Supported AST operators mapping to Python operator functions
    OPERATORS: ClassVar[dict[type, Callable]] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.USub: operator.neg,
    }

    def __init__(self, name: str, inputs: dict[str, Node], formula: str):
        """Initialize the FormulaCalculationNode.

        Args:
            name (str): The unique identifier for this node.
            inputs (Dict[str, Node]): Dictionary mapping variable names in the
                formula to the corresponding input nodes.
            formula (str): The mathematical formula string.

        Raises:
            ValueError: If the formula string has invalid syntax.
            TypeError: If any value in `inputs` is not a Node instance.
        """
        super().__init__(name)
        if not isinstance(inputs, dict) or not all(isinstance(n, Node) for n in inputs.values()):
            raise TypeError("FormulaCalculationNode inputs must be a dict of Node instances.")
        self.inputs = inputs
        self.formula = formula
        try:
            # Parse the formula string into an AST expression
            self._ast = ast.parse(formula, mode="eval").body
        except SyntaxError as e:
            raise ValueError(f"Invalid formula syntax for node '{name}': {formula}") from e

    def calculate(self, period: str) -> float:
        """Calculate the node's value for a period by evaluating the formula.

        Args:
            period (str): The time period for which to perform the calculation.

        Returns:
            float: The result of the formula evaluation.

        Raises:
            CalculationError: If an error occurs during evaluation, such as
                an unknown variable, unsupported operator, or if an input node
                fails to provide a numeric value for the period.
        """
        try:
            return self._evaluate(self._ast, period)
        except (ValueError, TypeError, KeyError, ZeroDivisionError) as e:
            raise CalculationError(
                message=f"Error evaluating formula for node '{self.name}'",
                node_id=self.name,
                period=period,
                details={"formula": self.formula, "error": str(e)},
            ) from e

    def _evaluate(self, node: ast.AST, period: str) -> float:
        """Recursively evaluate the parsed AST node for the formula.

        Args:
            node (ast.AST): The current AST node to evaluate.
            period (str): The time period context for the evaluation.

        Returns:
            float: The result of evaluating the AST node.

        Raises:
            TypeError: If a non-numeric constant or input node value is encountered.
            ValueError: If an unknown variable or unsupported operator/syntax is found.
            ZeroDivisionError: If division by zero occurs.
        """
        # Numeric literal (Constant in Python 3.8+, Num in earlier versions)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return float(node.value)
            else:
                raise TypeError(
                    f"Unsupported constant type '{type(node.value).__name__}' in formula for node '{self.name}'"
                )

        # Variable reference
        elif isinstance(node, ast.Name):
            var_name = node.id
            if var_name not in self.inputs:
                raise ValueError(
                    f"Unknown variable '{var_name}' in formula for node '{self.name}'. Available: {list(self.inputs.keys())}"
                )
            input_node = self.inputs[var_name]
            # Recursively calculate the value of the input node
            value = input_node.calculate(period)
            if not isinstance(value, (int, float)):
                raise TypeError(
                    f"Input node '{input_node.name}' (variable '{var_name}') did not return a numeric value for period '{period}'"
                )
            return float(value)

        # Binary operation (e.g., a + b)
        elif isinstance(node, ast.BinOp):
            left_val = self._evaluate(node.left, period)
            right_val = self._evaluate(node.right, period)
            op_type = type(node.op)
            if op_type not in self.OPERATORS:
                raise ValueError(
                    f"Unsupported binary operator '{op_type.__name__}' in formula for node '{self.name}'"
                )
            # Perform the operation
            return float(self.OPERATORS[op_type](left_val, right_val))

        # Unary operation (e.g., -a)
        elif isinstance(node, ast.UnaryOp):
            operand_val = self._evaluate(node.operand, period)
            op_type = type(node.op)
            if op_type not in self.OPERATORS:
                raise ValueError(
                    f"Unsupported unary operator '{op_type.__name__}' in formula for node '{self.name}'"
                )
            # Perform the operation
            return float(self.OPERATORS[op_type](operand_val))

        # If the node type is unsupported
        else:
            raise TypeError(
                f"Unsupported syntax node type '{type(node).__name__}' in formula for node '{self.name}': {ast.dump(node)}"
            )

    def get_dependencies(self) -> list[str]:
        """Return the names of input nodes used in the formula.

        Returns:
            A list of variable names corresponding to the formula inputs.
        """
        return [node.name for node in self.inputs.values()]

    def has_calculation(self) -> bool:
        """Indicate that this node performs calculation.

        Returns:
            True, as FormulaCalculationNode performs calculations.
        """
        return True


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

    def __init__(self, name: str, inputs: list[Node], calculation: Calculation):
        """Initialize the CalculationNode.

        Args:
            name (str): The unique identifier for this node.
            inputs (List[Node]): List of input nodes needed by the calculation.
            calculation (Any): The calculation object implementing the calculation.
                Must have a `calculate` method.

        Raises:
            TypeError: If `inputs` is not a list of Nodes, or if `calculation`
                does not have a callable `calculate` method.
        """
        super().__init__(name)
        if not isinstance(inputs, list) or not all(isinstance(n, Node) for n in inputs):
            raise TypeError("CalculationNode inputs must be a list of Node instances.")
        if not hasattr(calculation, "calculate") or not callable(getattr(calculation, "calculate")):
            raise TypeError("Calculation object must have a callable 'calculate' method.")

        self.inputs = inputs
        self.calculation = calculation
        self._values: dict[str, float] = {}  # Cache for calculated values

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
            if not isinstance(result, (int, float)):
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
                details={"calculation": type(self.calculation).__name__, "error": str(e)},
            ) from e

    def set_calculation(self, calculation: Calculation) -> None:
        """Change the calculation object for the node.

        Args:
            calculation (Any): The new calculation object. Must have a callable
                `calculate` method.

        Raises:
            TypeError: If the new calculation is invalid.
        """
        if not hasattr(calculation, "calculate") or not callable(getattr(calculation, "calculate")):
            raise TypeError("New calculation object must have a callable 'calculate' method.")
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


# === MetricCalculationNode (Already documented in metric_node.py, refined here) ===
# Note: This class seems to duplicate metric_node.py. Assuming this is the consolidated version.


class MetricCalculationNode(Node):
    """Calculate a value based on a predefined metric definition from the registry.

    Looks up a metric in `metric_registry`, resolves input nodes, and uses an
    appropriate calculation method based on the metric definition.

    Attributes:
        name (str): Identifier for this node.
        metric_name (str): The identifier for the metric in the registry.
        input_nodes (Dict[str, Node]): Mapping of input variable names to Node instances.
        _values (Dict[str, float]): Internal cache for calculated results.

    Examples:
        >>> # Assuming gross_margin metric is registered with formula "revenue - cogs"
        >>> revenue = FinancialStatementItemNode("revenue", {"2023": 100})
        >>> cogs = FinancialStatementItemNode("cogs", {"2023": 60})
        >>> gross_margin = MetricCalculationNode(
        ...     "gross_margin_calc",
        ...     metric_name="gross_margin",
        ...     input_nodes={"revenue": revenue, "cogs": cogs}
        ... )
        >>> print(gross_margin.calculate("2023"))
        40.0
    """

    def __init__(self, name: str, metric_name: str, input_nodes: dict[str, Node]):
        """Initialize the MetricCalculationNode.

        Args:
            name (str): The unique identifier for this node.
            metric_name (str): The identifier for the metric in the registry.
            input_nodes (Dict[str, Node]): Dictionary mapping variable names in the
                metric definition to the corresponding input nodes.

        Raises:
            ConfigurationError: If the metric_name is not registered in `metric_registry`.
            MetricError: If the metric definition is invalid or there's a mismatch between
                input_nodes and required inputs from the metric definition.
            TypeError: If any value in `input_nodes` is not a Node instance.
        """
        super().__init__(name)

        # Validate input_nodes type
        if not isinstance(input_nodes, dict):
            raise TypeError("MetricCalculationNode input_nodes must be a dict of Node instances")

        if not all(isinstance(node, Node) for node in input_nodes.values()):
            raise TypeError("MetricCalculationNode input_nodes must be a dict of Node instances")

        self.metric_name = metric_name
        self.input_nodes = input_nodes
        self._values: dict[str, float] = {}  # Cache for calculated results

        # Load the metric definition (Pydantic model) from the registry
        try:
            self.definition = metric_registry.get(metric_name)
        except KeyError:
            raise ConfigurationError(f"Metric definition '{metric_name}' not found")

        # Determine required inputs from the MetricDefinition model
        required_inputs = set(self.definition.inputs)
        provided_inputs = set(input_nodes.keys())

        missing_inputs = required_inputs - provided_inputs
        if missing_inputs:
            raise MetricError(
                f"Input nodes mismatch for metric '{metric_name}': missing required inputs: {missing_inputs}"
            )

        extra_inputs = provided_inputs - required_inputs
        if extra_inputs:
            raise MetricError(
                f"Input nodes mismatch for metric '{metric_name}': unexpected inputs provided: {extra_inputs}"
            )

        # Create internal formula calculation node using the formula from the MetricDefinition
        self.calc_node = FormulaCalculationNode(
            name=f"_{name}_formula_calc",
            inputs=input_nodes,
            formula=self.definition.formula,
        )

    def calculate(self, period: str) -> float:
        """Calculate the node's value for a period using the metric definition.

        Looks up the metric in `metric_registry`, resolves input nodes, and uses an
        appropriate calculation method based on the metric definition.

        Args:
            period (str): The time period for which to perform the calculation.

        Returns:
            float: The calculated value from the metric.

        Raises:
            CalculationError: If an error occurs during calculation, such as
                an unknown variable, unsupported operator, or if an input node
                fails to provide a numeric value for the period.
        """
        if period in self._values:
            return self._values[period]

        try:
            # Delegate calculation to the internal formula node
            result = self.calc_node.calculate(period)

            # Cache and return the result
            self._values[period] = float(result)
            return self._values[period]
        except Exception as e:
            # Wrap potential errors from the formula node
            raise CalculationError(
                message=f"Error calculating metric '{self.metric_name}' for node '{self.name}' and period '{period}'",
                node_id=self.name,
                period=period,
                details={"metric_name": self.metric_name, "original_error": str(e)},
            ) from e

    def get_dependencies(self) -> list[str]:
        """Return the names of input nodes used in the metric definition.

        Returns:
            A list of metric input node names.
        """
        return list(self.input_nodes.keys())

    def has_calculation(self) -> bool:
        """Indicate that this node performs calculation.

        Returns:
            True, as MetricCalculationNode performs calculations.
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
            raise TypeError("CustomCalculationNode inputs must be a list of Node instances")
        if not callable(formula_func):
            raise TypeError("CustomCalculationNode formula_func must be a callable function")

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
                if not isinstance(value, (int, float)):
                    raise TypeError(
                        f"Input node '{node.name}' did not return a numeric value for period '{period}'. Got {type(value).__name__}."
                    )
                input_values.append(value)

            # Calculate the value using the provided function
            result = self.formula_func(*input_values)
            if not isinstance(result, (int, float)):
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
