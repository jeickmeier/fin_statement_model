"""Provide node implementations for performing calculations in the financial statement model.

This module defines the different types of calculation nodes available in the system:
- FormulaCalculationNode: Evaluates a formula expression string (e.g., "a + b / 2")
- CalculationNode: Uses a calculation object for calculation logic
- CustomCalculationNode: Calculates using a Python callable/function

Features:
    - CalculationNode delegates logic to a Calculation object (strategy pattern).
    - FormulaCalculationNode evaluates mathematical expressions with named inputs.
    - CustomCalculationNode allows arbitrary Python callables for custom logic.
    - All nodes support serialization to and from dictionary representations.
    - All nodes provide dependency inspection and cache clearing where appropriate.

Example:
    >>> from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode
    >>> from fin_statement_model.core.nodes.calculation_nodes import CalculationNode, FormulaCalculationNode, CustomCalculationNode
    >>> class SumCalculation:
    ...     def calculate(self, inputs, period):
    ...         return sum(node.calculate(period) for node in inputs)
    >>> node_a = FinancialStatementItemNode("a", {"2023": 10})
    >>> node_b = FinancialStatementItemNode("b", {"2023": 20})
    >>> sum_node = CalculationNode("sum_ab", inputs=[node_a, node_b], calculation=SumCalculation())
    >>> sum_node.calculate("2023")
    30.0
    >>> formula_node = FormulaCalculationNode("gp", inputs={"rev": node_a, "cost": node_b}, formula="rev - cost")
    >>> formula_node.calculate("2023")
    -10.0
    >>> def add(a, b): return a + b
    >>> custom_node = CustomCalculationNode("add_node", inputs=[node_a, node_b], formula_func=add)
    >>> custom_node.calculate("2023")
    30.0
"""

from typing import Optional, Any, Callable, cast

from fin_statement_model.core.calculations.calculation import (
    Calculation,
    FormulaCalculation,
)
from fin_statement_model.core.errors import (
    CalculationError,
)
from fin_statement_model.core.nodes.base import Node
from fin_statement_model.core.node_factory.registries import node_type


# === CalculationNode ===


@node_type("calculation")
class CalculationNode(Node):
    """Delegate calculation logic to a calculation object.

    Use a calculation object to encapsulate the algorithm for computing node values.

    Serialization contract:
        - `to_dict(self) -> dict`: Serialize the node to a dictionary.
        - `from_dict(cls, data: dict, context: dict[str, Node] | None = None) -> CalculationNode`:
            Classmethod to deserialize a node from a dictionary. `context` is required to resolve input nodes.

    Attributes:
        name (str): Identifier for this node.
        inputs (List[Node]): A list of input nodes required by the calculation.
        calculation (Any): An object possessing a `calculate(inputs: List[Node], period: str) -> float` method.
        _values (Dict[str, float]): Internal cache for calculated results.

    Example:
        >>> from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode
        >>> class SumCalculation:
        ...     def calculate(self, inputs, period):
        ...         return sum(node.calculate(period) for node in inputs)
        >>> node_a = FinancialStatementItemNode("a", {"2023": 10})
        >>> node_b = FinancialStatementItemNode("b", {"2023": 20})
        >>> sum_node = CalculationNode("sum_ab", inputs=[node_a, node_b], calculation=SumCalculation())
        >>> d = sum_node.to_dict()
        >>> sum_node2 = CalculationNode.from_dict(d, {"a": node_a, "b": node_b})
        >>> sum_node2.calculate("2023")
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

        Example:
            >>> from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode
            >>> class SumCalculation:
            ...     def calculate(self, inputs, period):
            ...         return sum(node.calculate(period) for node in inputs)
            >>> node_a = FinancialStatementItemNode("a", {"2023": 10})
            >>> node_b = FinancialStatementItemNode("b", {"2023": 20})
            >>> sum_node = CalculationNode("sum_ab", inputs=[node_a, node_b], calculation=SumCalculation())
            >>> sum_node.calculate("2023")
            30.0
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
        """Calculate the node's value for a given period.

        Check the cache; on a miss, delegate to `calculation.calculate` and cache the result.

        Args:
            period (str): Identifier for the time period.

        Returns:
            float: Calculated value for the period.

        Raises:
            CalculationError: If calculation fails or returns a non-numeric value.

        Example:
            >>> from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode
            >>> class SumCalculation:
            ...     def calculate(self, inputs, period):
            ...         return sum(node.calculate(period) for node in inputs)
            >>> node_a = FinancialStatementItemNode("a", {"2023": 10})
            >>> node_b = FinancialStatementItemNode("b", {"2023": 20})
            >>> sum_node = CalculationNode("sum_ab", inputs=[node_a, node_b], calculation=SumCalculation())
            >>> sum_node.calculate("2023")
            30.0
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

        Example:
            >>> from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode
            >>> class SumCalculation:
            ...     def calculate(self, inputs, period):
            ...         return sum(node.calculate(period) for node in inputs)
            >>> node_a = FinancialStatementItemNode("a", {"2023": 10})
            >>> node_b = FinancialStatementItemNode("b", {"2023": 20})
            >>> sum_node = CalculationNode("sum_ab", inputs=[node_a, node_b], calculation=SumCalculation())
            >>> sum_node.set_calculation(SumCalculation())
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

        Example:
            >>> from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode
            >>> class SumCalculation:
            ...     def calculate(self, inputs, period):
            ...         return sum(node.calculate(period) for node in inputs)
            >>> node_a = FinancialStatementItemNode("a", {"2023": 10})
            >>> node_b = FinancialStatementItemNode("b", {"2023": 20})
            >>> sum_node = CalculationNode("sum_ab", inputs=[node_a, node_b], calculation=SumCalculation())
            >>> sum_node.clear_cache()
        """
        self._values.clear()

    def get_dependencies(self) -> list[str]:
        """Return the names of input nodes used by the calculation.

        Returns:
            A list of input node names.

        Example:
            >>> from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode
            >>> class SumCalculation:
            ...     def calculate(self, inputs, period):
            ...         return sum(node.calculate(period) for node in inputs)
            >>> node_a = FinancialStatementItemNode("a", {"2023": 10})
            >>> node_b = FinancialStatementItemNode("b", {"2023": 20})
            >>> sum_node = CalculationNode("sum_ab", inputs=[node_a, node_b], calculation=SumCalculation())
            >>> sum_node.get_dependencies()
            ['a', 'b']
        """
        return [node.name for node in self.inputs]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the node to a dictionary representation.

        Returns:
            Dictionary containing the node's type, name, inputs, and calculation info.

        Note:
            This method requires access to NodeFactory's calculation registry
            to properly serialize the calculation type. Some calculation types
            with non-serializable parameters may include warnings.

        Example:
            >>> # See CalculationNode usage in main module docstring
        """
        # Import here to avoid circular imports
        from fin_statement_model.core.node_factory import NodeFactory

        node_dict: dict[str, Any] = {
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
                    node_dict["formula_variable_names"] = (
                        self.calculation.input_variable_names
                    )
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

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        context: dict[str, Node] | None = None,
    ) -> "CalculationNode":
        """Create a CalculationNode from a dictionary with node context.

        Args:
            data: Dictionary containing the node's serialized data.
            context: Dictionary of existing nodes to resolve dependencies.

        Returns:
            A new CalculationNode instance.

        Raises:
            ValueError: If the data is invalid or missing required fields.

        Example:
            >>> # See CalculationNode usage in main module docstring
        """
        # Import here to avoid circular imports
        from fin_statement_model.core.node_factory import NodeFactory

        if data.get("type") != "calculation":
            raise ValueError(f"Invalid type for CalculationNode: {data.get('type')}")

        name = data.get("name")
        if not name:
            raise ValueError("Missing 'name' field in CalculationNode data")

        if context is None:
            raise ValueError(
                "'context' must be provided to deserialize CalculationNode"
            )

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
        return cast(
            "CalculationNode",
            NodeFactory.create_calculation_node(
                name=name,
                inputs=input_nodes,
                calculation_type=calculation_type,
                formula_variable_names=formula_variable_names,
                metric_name=metric_name,
                metric_description=metric_description,
                **calculation_args,
            ),
        )


# === FormulaCalculationNode ===


@node_type("formula_calculation")
class FormulaCalculationNode(CalculationNode):
    """Calculate values based on a formula string.

    Use a formula expression and mapped input nodes to evaluate a calculation.

    Serialization contract:
        - `to_dict(self) -> dict`: Serialize the node to a dictionary.
        - `from_dict(cls, data: dict, context: dict[str, Node] | None = None) -> FormulaCalculationNode`:
            Classmethod to deserialize a node from a dictionary. `context` is required to resolve input nodes.

    Attributes:
        inputs_dict (dict[str, Node]): Mapping of variable names to input nodes.
        formula (str): Mathematical expression to evaluate.
        metric_name (Optional[str]): Metric identifier from the registry, if any.
        metric_description (Optional[str]): Description from the metric definition, if any.

    Example:
        >>> from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode
        >>> revenue = FinancialStatementItemNode("revenue", {"2023": 100})
        >>> cogs = FinancialStatementItemNode("cogs", {"2023": 60})
        >>> formula_node = FormulaCalculationNode(
        ...     "gross_profit", inputs={"rev": revenue, "cost": cogs}, formula="rev - cost"
        ... )
        >>> d = formula_node.to_dict()
        >>> formula_node2 = FormulaCalculationNode.from_dict(d, {"revenue": revenue, "cogs": cogs})
        >>> formula_node2.calculate("2023")
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
        """Create a FormulaCalculationNode.

        Args:
            name (str): Unique identifier for the node.
            inputs (dict[str, Node]): Mapping of variable names to input nodes.
            formula (str): Mathematical formula string to evaluate.
            metric_name (Optional[str]): Original metric key from registry.
            metric_description (Optional[str]): Description from the metric definition.

        Raises:
            ValueError: If `formula` syntax is invalid.
            TypeError: If any entry in `inputs` is not a Node.

        Example:
            >>> from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode
            >>> revenue = FinancialStatementItemNode("revenue", {"2023": 100})
            >>> cogs = FinancialStatementItemNode("cogs", {"2023": 60})
            >>> formula_node = FormulaCalculationNode(
            ...     "gross_profit", inputs={"rev": revenue, "cost": cogs}, formula="rev - cost"
            ... )
            >>> formula_node.calculate("2023")
            40.0
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
        """Get names of nodes used in the formula.

        Returns:
            list[str]: Names of input nodes.

        Example:
            >>> from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode
            >>> revenue = FinancialStatementItemNode("revenue", {"2023": 100})
            >>> cogs = FinancialStatementItemNode("cogs", {"2023": 60})
            >>> formula_node = FormulaCalculationNode(
            ...     "gross_profit", inputs={"rev": revenue, "cost": cogs}, formula="rev - cost"
            ... )
            >>> formula_node.get_dependencies()
            ['revenue', 'cogs']
        """
        return [node.name for node in self.inputs_dict.values()]

    def to_dict(self) -> dict[str, Any]:
        """Serialize this node to a dictionary.

        Returns:
            dict[str, Any]: Serialized node data.

        Example:
            >>> # See FormulaCalculationNode usage in main module docstring
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

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        context: dict[str, Node] | None = None,
    ) -> "FormulaCalculationNode":
        """Create a FormulaCalculationNode from a dictionary with node context.

        Args:
            data: Dictionary containing the node's serialized data.
            context: Dictionary of existing nodes to resolve dependencies.

        Returns:
            A new FormulaCalculationNode instance.

        Raises:
            ValueError: If the data is invalid or missing required fields.

        Example:
            >>> # See FormulaCalculationNode usage in main module docstring
        """
        if data.get("type") != "formula_calculation":
            raise ValueError(
                f"Invalid type for FormulaCalculationNode: {data.get('type')}"
            )

        name = data.get("name")
        if not name:
            raise ValueError("Missing 'name' field in FormulaCalculationNode data")

        if context is None:
            raise ValueError(
                "'context' must be provided to deserialize FormulaCalculationNode"
            )

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

        return cls(
            name=name,
            inputs=inputs_dict,
            formula=formula,
            metric_name=metric_name,
            metric_description=metric_description,
        )


# === CustomCalculationNode ===


@node_type("custom_calculation")
class CustomCalculationNode(Node):
    """Calculate values using a custom Python function.

    Use a provided callable to compute node values from input nodes.

    Serialization contract:
        - `to_dict(self) -> dict`: Serialize the node to a dictionary (includes a warning).
        - `from_dict(cls, data: dict, context: dict[str, Node] | None = None) -> CustomCalculationNode`:
            Not supported; always raises NotImplementedError because the function cannot be serialized.

    Attributes:
        inputs (list[Node]): Nodes supplying inputs to the function.
        formula_func (Callable[..., float]): Function to compute values.
        description (Optional[str]): Description of the calculation.
        _values (dict[str, float]): Cache of computed results.

    Example:
        >>> from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode
        >>> def add(a, b): return a + b
        >>> a = FinancialStatementItemNode("A", {"2023": 10})
        >>> b = FinancialStatementItemNode("B", {"2023": 5})
        >>> node = CustomCalculationNode("add_node", inputs=[a, b], formula_func=add)
        >>> node.calculate("2023")
        15.0
    """

    def __init__(
        self,
        name: str,
        inputs: list[Node],
        formula_func: Callable[..., float],
        description: Optional[str] = None,
    ) -> None:
        """Create a CustomCalculationNode.

        Args:
            name (str): Unique identifier for the node.
            inputs (list[Node]): Nodes providing input values.
            formula_func (Callable[..., float]): Function to compute values.
            description (str, optional): Description of the calculation.

        Raises:
            TypeError: If `inputs` is not a list of Node or `formula_func` is not callable.

        Example:
            >>> from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode
            >>> def add(a, b): return a + b
            >>> a = FinancialStatementItemNode("A", {"2023": 10})
            >>> b = FinancialStatementItemNode("B", {"2023": 5})
            >>> node = CustomCalculationNode("add_node", inputs=[a, b], formula_func=add)
            >>> node.calculate("2023")
            15.0
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
        """Compute the node's value for a given period.

        Evaluate `formula_func` with inputs from `inputs` and cache the result.

        Args:
            period (str): The time period for which to perform the calculation.

        Returns:
            float: Computed value for the period.

        Raises:
            CalculationError: On errors retrieving inputs or computing the function.

        Example:
            >>> from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode
            >>> def add(a, b): return a + b
            >>> a = FinancialStatementItemNode("A", {"2023": 10})
            >>> b = FinancialStatementItemNode("B", {"2023": 5})
            >>> node = CustomCalculationNode("add_node", inputs=[a, b], formula_func=add)
            >>> node.calculate("2023")
            15.0
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

    def clear_cache(self) -> None:
        """Clear cached calculation results for this node.

        Example:
            >>> from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode
            >>> def add(a, b): return a + b
            >>> a = FinancialStatementItemNode("A", {"2023": 10})
            >>> b = FinancialStatementItemNode("B", {"2023": 5})
            >>> node = CustomCalculationNode("add_node", inputs=[a, b], formula_func=add)
            >>> node.clear_cache()
        """
        self._values.clear()

    def get_dependencies(self) -> list[str]:
        """Get names of nodes used by the function.

        Returns:
            list[str]: Names of input nodes.

        Example:
            >>> from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode
            >>> def add(a, b): return a + b
            >>> a = FinancialStatementItemNode("A", {"2023": 10})
            >>> b = FinancialStatementItemNode("B", {"2023": 5})
            >>> node = CustomCalculationNode("add_node", inputs=[a, b], formula_func=add)
            >>> node.get_dependencies()
            ['A', 'B']
        """
        return [node.name for node in self.inputs]

    def to_dict(self) -> dict[str, Any]:
        """Serialize this node to a dictionary.

        Returns:
            dict[str, Any]: Serialized node data with non-serializable function warning.

        Example:
            >>> # See CustomCalculationNode usage in main module docstring
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

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        context: dict[str, Node] | None = None,
    ) -> "CustomCalculationNode":
        """CustomCalculationNode deserialization is not supported.

        This method is present only to satisfy the Node interface. Attempting to call it will always raise NotImplementedError,
        because the Python function used for calculation cannot be serialized or reconstructed automatically.

        Raises:
            NotImplementedError: Always.

        Example:
            >>> # Not supported:
            >>> from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode
            >>> def add(a, b): return a + b
            >>> a = FinancialStatementItemNode("A", {"2023": 10})
            >>> b = FinancialStatementItemNode("B", {"2023": 5})
            >>> node = CustomCalculationNode("add_node", inputs=[a, b], formula_func=add)
            >>> d = node.to_dict()
            >>> CustomCalculationNode.from_dict(d, {"A": a, "B": b})  # doctest: +SKIP
            Traceback (most recent call last):
            ...
            NotImplementedError: CustomCalculationNode cannot be deserialized automatically because it relies on a Python callable.
        """
        raise NotImplementedError(
            "CustomCalculationNode cannot be deserialized automatically because it relies on a Python callable."
        )
