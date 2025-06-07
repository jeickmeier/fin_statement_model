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

    def __init__(self, name: str, inputs: list[Node], calculation: Calculation, **kwargs: Any):
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
        if not hasattr(calculation, "calculate") or not callable(getattr(calculation, "calculate")):
            raise TypeError("Calculation object must have a callable 'calculate' method.")

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

    def to_dict(self) -> dict[str, Any]:
        """Serialize the node to a dictionary representation.

        Returns:
            Dictionary containing the node's type, name, inputs, and calculation info.

        Note:
            This method requires access to NodeFactory's calculation registry
            to properly serialize the calculation type. Some calculation types
            with non-serializable parameters may include warnings.
        """
        # Import here to avoid circular imports
        from fin_statement_model.core.node_factory import NodeFactory

        node_dict = {
            "type": "calculation",
            "name": self.name,
            "inputs": self.get_dependencies(),
        }

        # Add calculation type information
        calc_class_name = type(self.calculation).__name__
        node_dict["calculation_type_class"] = calc_class_name

        # Find the calculation type key from NodeFactory registry
        inv_map = {v: k for k, v in NodeFactory._calculation_methods.items()}
        type_key = inv_map.get(calc_class_name)
        if type_key:
            node_dict["calculation_type"] = type_key

            # Extract calculation-specific arguments
            calculation_args = {}

            # Handle specific calculation types
            if type_key == "weighted_average" and hasattr(self.calculation, "weights"):
                calculation_args["weights"] = self.calculation.weights
            elif type_key == "formula" and hasattr(self.calculation, "formula"):
                calculation_args["formula"] = self.calculation.formula
                if hasattr(self.calculation, "input_variable_names"):
                    node_dict["formula_variable_names"] = self.calculation.input_variable_names
            elif type_key == "custom_formula":
                node_dict["serialization_warning"] = (
                    "CustomFormulaCalculation uses a Python function which cannot be serialized. "
                    "Manual reconstruction required."
                )

            if calculation_args:
                node_dict["calculation_args"] = calculation_args

        # Add any additional attributes (like metric info)
        if hasattr(self, "metric_name") and self.metric_name:
            node_dict["metric_name"] = self.metric_name
        if hasattr(self, "metric_description") and self.metric_description:
            node_dict["metric_description"] = self.metric_description

        return node_dict

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "CalculationNode":
        """Create a CalculationNode from a dictionary representation.

        Args:
            data: Dictionary containing the node's serialized data.

        Returns:
            A new CalculationNode instance.

        Raises:
            ValueError: If the data is invalid or missing required fields.
            NotImplementedError: This method requires context (existing nodes) to resolve
                input dependencies. Use from_dict_with_context instead.

        Note:
            This method cannot resolve input node dependencies without context.
            Use NodeFactory.create_from_dict() or from_dict_with_context() instead.
        """
        raise NotImplementedError(
            "CalculationNode.from_dict() requires context to resolve input dependencies. "
            "Use NodeFactory.create_from_dict() or from_dict_with_context() instead."
        )

    @staticmethod
    def from_dict_with_context(data: dict[str, Any], context: dict[str, Node]) -> "CalculationNode":
        """Create a CalculationNode from a dictionary with node context.

        Args:
            data: Dictionary containing the node's serialized data.
            context: Dictionary of existing nodes to resolve dependencies.

        Returns:
            A new CalculationNode instance.

        Raises:
            ValueError: If the data is invalid or missing required fields.
        """
        # Import here to avoid circular imports
        from fin_statement_model.core.node_factory import NodeFactory

        if data.get("type") != "calculation":
            raise ValueError(f"Invalid type for CalculationNode: {data.get('type')}")

        name = data.get("name")
        if not name:
            raise ValueError("Missing 'name' field in CalculationNode data")

        input_names = data.get("inputs", [])
        if not isinstance(input_names, list):
            raise TypeError("'inputs' field must be a list")

        # Resolve input nodes from context
        input_nodes = []
        for input_name in input_names:
            if input_name not in context:
                raise ValueError(f"Input node '{input_name}' not found in context")
            input_nodes.append(context[input_name])

        calculation_type = data.get("calculation_type")
        if not calculation_type:
            raise ValueError("Missing 'calculation_type' field in CalculationNode data")

        # Get calculation arguments
        calculation_args = data.get("calculation_args", {})

        # Handle formula variable names for formula calculations
        formula_variable_names = data.get("formula_variable_names")

        # Extract metric information
        metric_name = data.get("metric_name")
        metric_description = data.get("metric_description")

        # Create the node using NodeFactory
        return NodeFactory.create_calculation_node(
            name=name,
            inputs=input_nodes,
            calculation_type=calculation_type,
            formula_variable_names=formula_variable_names,
            metric_name=metric_name,
            metric_description=metric_description,
            **calculation_args,
        )


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
        if not isinstance(inputs, dict) or not all(isinstance(n, Node) for n in inputs.values()):
            raise TypeError("FormulaCalculationNode inputs must be a dict of Node instances.")

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

    def to_dict(self) -> dict[str, Any]:
        """Serialize the node to a dictionary representation.

        Returns:
            Dictionary containing the node's type, name, inputs, and formula info.
        """
        return {
            "type": "formula_calculation",
            "name": self.name,
            "inputs": self.get_dependencies(),
            "formula_variable_names": list(self.inputs_dict.keys()),
            "formula": self.formula,
            "calculation_type": "formula",
            "metric_name": self.metric_name,
            "metric_description": self.metric_description,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "FormulaCalculationNode":
        """Create a FormulaCalculationNode from a dictionary representation.

        Args:
            data: Dictionary containing the node's serialized data.

        Returns:
            A new FormulaCalculationNode instance.

        Raises:
            ValueError: If the data is invalid or missing required fields.
            NotImplementedError: This method requires context (existing nodes) to resolve
                input dependencies. Use from_dict_with_context instead.
        """
        raise NotImplementedError(
            "FormulaCalculationNode.from_dict() requires context to resolve input dependencies. "
            "Use NodeFactory.create_from_dict() or from_dict_with_context() instead."
        )

    @staticmethod
    def from_dict_with_context(
        data: dict[str, Any], context: dict[str, Node]
    ) -> "FormulaCalculationNode":
        """Create a FormulaCalculationNode from a dictionary with node context.

        Args:
            data: Dictionary containing the node's serialized data.
            context: Dictionary of existing nodes to resolve dependencies.

        Returns:
            A new FormulaCalculationNode instance.

        Raises:
            ValueError: If the data is invalid or missing required fields.
        """
        if data.get("type") != "formula_calculation":
            raise ValueError(f"Invalid type for FormulaCalculationNode: {data.get('type')}")

        name = data.get("name")
        if not name:
            raise ValueError("Missing 'name' field in FormulaCalculationNode data")

        formula = data.get("formula")
        if not formula:
            raise ValueError("Missing 'formula' field in FormulaCalculationNode data")

        input_names = data.get("inputs", [])
        formula_variable_names = data.get("formula_variable_names", [])

        if len(input_names) != len(formula_variable_names):
            raise ValueError(
                "Mismatch between inputs and formula_variable_names in FormulaCalculationNode data"
            )

        # Resolve input nodes from context and create inputs dict
        inputs_dict = {}
        for var_name, input_name in zip(formula_variable_names, input_names):
            if input_name not in context:
                raise ValueError(f"Input node '{input_name}' not found in context")
            inputs_dict[var_name] = context[input_name]

        # Extract metric information
        metric_name = data.get("metric_name")
        metric_description = data.get("metric_description")

        return FormulaCalculationNode(
            name=name,
            inputs=inputs_dict,
            formula=formula,
            metric_name=metric_name,
            metric_description=metric_description,
        )


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

    def to_dict(self) -> dict[str, Any]:
        """Serialize the node to a dictionary representation.

        Returns:
            Dictionary containing the node's type, name, inputs, and description.

        Note:
            The formula_func cannot be serialized, so a warning is included.
        """
        return {
            "type": "custom_calculation",
            "name": self.name,
            "inputs": self.get_dependencies(),
            "description": self.description,
            "serialization_warning": (
                "CustomCalculationNode uses a Python function which cannot be serialized. "
                "Manual reconstruction required."
            ),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "CustomCalculationNode":
        """Create a CustomCalculationNode from a dictionary representation.

        Args:
            data: Dictionary containing the node's serialized data.

        Returns:
            A new CustomCalculationNode instance.

        Raises:
            ValueError: If the data is invalid or missing required fields.
            NotImplementedError: CustomCalculationNode cannot be fully deserialized
                because the formula_func cannot be serialized.
        """
        raise NotImplementedError(
            "CustomCalculationNode cannot be fully deserialized because the formula_func "
            "cannot be serialized. Manual reconstruction required."
        )
