"""Factory helpers for creating nodes in the financial statement model.

This module centralizes node-creation logic to ensure consistent initialization
for all node types (financial statement items, calculations, forecasts, stats).
"""

import logging
from typing import Any, Callable, ClassVar, Optional, Union, cast

# Force import of calculations package to ensure registration happens
from fin_statement_model.core.calculations import Calculation, Registry
from fin_statement_model.core.errors import ConfigurationError

# Force import of strategies package to ensure registration happens
from .nodes import (
    CalculationNode,
    CustomCalculationNode,
    FinancialStatementItemNode,
    Node,
)
from .nodes.calculation_nodes import FormulaCalculationNode
from .nodes.forecast_nodes import (
    AverageHistoricalGrowthForecastNode,
    AverageValueForecastNode,
    CurveGrowthForecastNode,
    CustomGrowthForecastNode,
    FixedGrowthForecastNode,
    ForecastNode,
    StatisticalGrowthForecastNode,
)
from .nodes.stats_nodes import (
    MultiPeriodStatNode,
    TwoPeriodAverageNode,
    YoYGrowthNode,
)

# Configure logging
logger = logging.getLogger(__name__)


class NodeFactory:
    """Factory for creating nodes in the financial statement model.

    The class exposes convenience helpers that hide the underlying registry
    and deserialization logic, so client code can create nodes declaratively
    (e.g., via YAML configs or simple Python calls) without importing every
    concrete node class.

    Attributes:
        _calculation_methods: Mapping of calculation type keys (e.g., ``"addition"``)
            to calculation class names registered in :class:`fin_statement_model.core.calculations.Registry`.
        _node_type_registry: Mapping of node-type strings to concrete :class:`Node`
            subclasses used when deserializing from dictionaries.
    """

    # Mapping of calculation type strings to Calculation class names (keys in the Registry)
    _calculation_methods: ClassVar[dict[str, str]] = {
        "addition": "AdditionCalculation",
        "subtraction": "SubtractionCalculation",
        "formula": "FormulaCalculation",
        "division": "DivisionCalculation",
        "weighted_average": "WeightedAverageCalculation",
        "custom_formula": "CustomFormulaCalculation",
    }

    # Mapping from node type names to Node classes for deserialization
    _node_type_registry: ClassVar[dict[str, type[Node]]] = {
        "financial_statement_item": FinancialStatementItemNode,
        "calculation": CalculationNode,
        "formula_calculation": FormulaCalculationNode,
        "custom_calculation": CustomCalculationNode,
        "forecast": ForecastNode,
        # Specific forecast types
        "fixed_growth_forecast": FixedGrowthForecastNode,
        "curve_growth_forecast": CurveGrowthForecastNode,
        "statistical_growth_forecast": StatisticalGrowthForecastNode,
        "average_value_forecast": AverageValueForecastNode,
        "average_historical_growth_forecast": AverageHistoricalGrowthForecastNode,
        "custom_growth_forecast": CustomGrowthForecastNode,
        # Stats node types
        "yoy_growth": YoYGrowthNode,
        "multi_period_stat": MultiPeriodStatNode,
        "two_period_average": TwoPeriodAverageNode,
    }

    # Mapping from forecast type strings to specific forecast node classes
    _forecast_type_registry: ClassVar[dict[str, type[ForecastNode]]] = {
        "simple": FixedGrowthForecastNode,
        "curve": CurveGrowthForecastNode,
        "statistical": StatisticalGrowthForecastNode,
        "average": AverageValueForecastNode,
        "historical_growth": AverageHistoricalGrowthForecastNode,
        "custom": CustomGrowthForecastNode,
    }

    @classmethod
    def create_financial_statement_item(
        cls, name: str, values: dict[str, float]
    ) -> FinancialStatementItemNode:
        """Create a FinancialStatementItemNode representing a base financial item.

        This node holds historical or projected values for a specific
        line item (e.g., Revenue, COGS) over different periods.

        Args:
            name: Identifier for the node (e.g., "Revenue").
            values: Mapping of period identifiers to numerical values.

        Returns:
            A FinancialStatementItemNode initialized with the provided values.

        Raises:
            ValueError: If the provided name is empty or not a string.

        Examples:
            >>> revenue_node = NodeFactory.create_financial_statement_item(
            ...     name="Revenue",
            ...     values={"2023": 1000.0, "2024": 1100.0}
            ... )
            >>> revenue_node.calculate("2023")
            1000.0
        """
        if not name or not isinstance(name, str):
            raise ValueError("Node name must be a non-empty string")

        logger.debug(f"Creating financial statement item node: {name}")
        return FinancialStatementItemNode(name, values)

    @classmethod
    def create_calculation_node(
        cls,
        name: str,
        inputs: list[Node],
        calculation_type: str,
        formula_variable_names: Optional[list[str]] = None,
        **calculation_kwargs: Any,
    ) -> CalculationNode:
        """Create a CalculationNode using a pre-defined calculation.

        This method resolves a calculation class from a calculation_type key,
        instantiates it with optional parameters, and wraps it in
        a CalculationNode.

        Args:
            name: Identifier for the calculation node instance.
            inputs: List of Node instances serving as inputs to the calculation.
            calculation_type: Key for the desired calculation in the registry.
            formula_variable_names: Optional list of variable names used in the formula
                string. Required & used only if creating a FormulaCalculationNode
                via the 'custom_formula' type with a 'formula' kwarg.
            **calculation_kwargs: Additional parameters for the calculation constructor.

        Returns:
            A CalculationNode configured with the selected calculation.

        Raises:
            ValueError: If name is invalid, inputs list is empty, or the
                calculation_type is unrecognized.
            TypeError: If the calculation cannot be instantiated with given kwargs.

        Examples:
            >>> gross_profit = NodeFactory.create_calculation_node(
            ...     name="GrossProfit",
            ...     inputs=[revenue, cogs],
            ...     calculation_type="subtraction"
            ... )
        """
        # Validate inputs
        if not name or not isinstance(name, str):
            raise ValueError("Node name must be a non-empty string")

        if not inputs:
            raise ValueError("Calculation node must have at least one input")

        # Check if the calculation type maps to a known calculation name
        if calculation_type not in cls._calculation_methods:
            valid_types = list(cls._calculation_methods.keys())
            raise ValueError(
                f"Invalid calculation type: '{calculation_type}'. Valid types are: {valid_types}"
            )

        # Get the calculation name
        calculation_name = cls._calculation_methods[calculation_type]

        # For other types, resolve the Calculation class from the registry
        try:
            calculation_cls: type[Calculation] = Registry.get(calculation_name)
        except KeyError:
            # This should ideally not happen if _calculation_methods is synced with registry
            raise ValueError(
                f"Calculation class '{calculation_name}' (for type '{calculation_type}') not found in Registry."
            ) from None  # Prevent chaining the KeyError

        # Instantiate the calculation, passing any extra kwargs
        try:
            # Extract any metadata that should be stored on the node, not passed to calculation
            node_kwargs = {}
            if "metric_name" in calculation_kwargs:
                node_kwargs["metric_name"] = calculation_kwargs.pop("metric_name")
            if "metric_description" in calculation_kwargs:
                node_kwargs["metric_description"] = calculation_kwargs.pop(
                    "metric_description"
                )

            # Special handling for FormulaCalculation which needs input_variable_names
            if calculation_type == "formula":
                if formula_variable_names and len(formula_variable_names) == len(
                    inputs
                ):
                    calculation_kwargs["input_variable_names"] = formula_variable_names
                elif not formula_variable_names:
                    # Generate default names like var_0, var_1, ...
                    calculation_kwargs["input_variable_names"] = [
                        f"var_{i}" for i in range(len(inputs))
                    ]
                    logger.warning(
                        f"No formula_variable_names provided for formula node '{name}'. Using defaults: {calculation_kwargs['input_variable_names']}"
                    )
                else:
                    # Mismatch between provided names and number of inputs
                    raise ConfigurationError(
                        f"Mismatch between formula_variable_names ({len(formula_variable_names)}) and number of inputs ({len(inputs)}) for node '{name}'"
                    )

            calculation_instance = calculation_cls(**calculation_kwargs)
        except TypeError as e:
            logger.exception(
                f"Failed to instantiate calculation '{calculation_name}' with kwargs {calculation_kwargs}"
            )
            raise TypeError(
                f"Could not instantiate calculation '{calculation_name}' for node '{name}'. "
                f"Check required arguments for {calculation_cls.__name__}. Provided kwargs: {calculation_kwargs}"
            ) from e

        # Create and return a CalculationNode with the instantiated calculation
        logger.debug(
            f"Creating calculation node '{name}' with '{calculation_name}' calculation."
        )

        return CalculationNode(name, inputs, calculation_instance, **node_kwargs)

    @classmethod
    def create_forecast_node(
        cls,
        name: str,
        base_node: Node,
        base_period: str,
        forecast_periods: list[str],
        forecast_type: str,
        growth_params: Union[float, list[float], Callable[[], float]],
    ) -> Node:
        """Create a forecast node of the specified type using core forecast classes.

        Args:
            name: Custom name for the forecast node.
            base_node: The Node instance to base projections on.
            base_period: Period identifier providing the base value.
            forecast_periods: List of periods for which to forecast.
            forecast_type: Forecast method ('simple', 'curve', 'statistical',
                'average', 'historical_growth').
            growth_params: Parameters controlling forecast behavior (float,
                list of floats, or callable). Ignored for 'average' and 'historical_growth'.

        Returns:
            A Node instance implementing the chosen forecast.

        Raises:
            ValueError: If an unsupported forecast_type is provided.

        Examples:
            >>> forecast = NodeFactory.create_forecast_node(
            ...     name="RevForecast",
            ...     base_node=revenue,
            ...     base_period="2023",
            ...     forecast_periods=["2024", "2025"],
            ...     forecast_type="simple",
            ...     growth_params=0.05
            ... )
        """
        # Prepare placeholder to unify forecast node type
        node: ForecastNode
        # Instantiate the appropriate forecast node with proper type checking
        if forecast_type == "simple":
            if not isinstance(growth_params, (int, float)):
                raise TypeError("growth_params must be a float for 'simple' forecast")
            node = FixedGrowthForecastNode(
                base_node, base_period, forecast_periods, float(growth_params)
            )
        elif forecast_type == "curve":
            if not isinstance(growth_params, list):
                raise TypeError(
                    "growth_params must be a list of floats for 'curve' forecast"
                )
            rates: list[float] = [float(r) for r in growth_params]
            node = CurveGrowthForecastNode(
                base_node, base_period, forecast_periods, rates
            )
        elif forecast_type == "statistical":
            if not callable(growth_params):
                raise TypeError(
                    "growth_params must be a callable returning float for 'statistical' forecast"
                )
            node = StatisticalGrowthForecastNode(
                base_node, base_period, forecast_periods, growth_params
            )
        elif forecast_type == "average":
            node = AverageValueForecastNode(base_node, base_period, forecast_periods)
        elif forecast_type == "historical_growth":
            node = AverageHistoricalGrowthForecastNode(
                base_node, base_period, forecast_periods
            )
        else:
            raise ValueError(f"Invalid forecast type: {forecast_type}")

        # Override forecast node's name to match factory 'name' argument
        node.name = name
        logger.debug(
            f"Forecast node created with custom name: {name} (original: {base_node.name})"
        )
        return node

    @classmethod
    def create_from_dict(
        cls, data: dict[str, Any], context: Optional[dict[str, Node]] = None
    ) -> Node:
        """Create a node from its dictionary representation.

        This method provides a unified interface for deserializing nodes from
        their dictionary representations, handling dependency resolution and
        type-specific deserialization logic.

        Args:
            data: Serialized node data containing at minimum a 'type' field.
            context: Optional dictionary of existing nodes for resolving dependencies.
                Required for nodes that have dependencies (calculation, forecast nodes).

        Returns:
            Reconstructed node instance.

        Raises:
            ValueError: If the data is invalid, missing required fields, or contains
                an unknown node type.
            ConfigurationError: If dependencies cannot be resolved or node creation fails.

        Examples:
            >>> # Simple node without dependencies
            >>> data = {
            ...     'type': 'financial_statement_item',
            ...     'name': 'Revenue',
            ...     'values': {'2023': 1000.0}
            ... }
            >>> node = NodeFactory.create_from_dict(data)

            >>> # Node with dependencies
            >>> calc_data = {
            ...     'type': 'calculation',
            ...     'name': 'GrossProfit',
            ...     'inputs': ['Revenue', 'COGS'],
            ...     'calculation_type': 'subtraction'
            ... }
            >>> context = {'Revenue': revenue_node, 'COGS': cogs_node}
            >>> calc_node = NodeFactory.create_from_dict(calc_data, context)
        """
        if not isinstance(data, dict):
            raise TypeError("Node data must be a dictionary")

        node_type = data.get("type")
        if not node_type:
            raise ValueError("Missing 'type' field in node data")

        logger.debug(f"Creating node of type '{node_type}' from dictionary")

        # Handle nodes without dependencies first
        if node_type == "financial_statement_item":
            return FinancialStatementItemNode.from_dict(data)

        # Handle nodes that require context for dependency resolution
        if context is None:
            context = {}

        # For calculation nodes, use the appropriate from_dict_with_context method
        if node_type == "calculation":
            return cast(Node, CalculationNode.from_dict_with_context(data, context))
        elif node_type == "formula_calculation":
            return cast(
                Node, FormulaCalculationNode.from_dict_with_context(data, context)
            )
        elif node_type == "custom_calculation":
            raise ConfigurationError(
                "CustomCalculationNode cannot be deserialized because it contains "
                "non-serializable Python functions. Manual reconstruction required."
            )

        # Handle stats nodes
        elif node_type == "yoy_growth":
            return YoYGrowthNode.from_dict_with_context(data, context)
        elif node_type == "multi_period_stat":
            return MultiPeriodStatNode.from_dict_with_context(data, context)
        elif node_type == "two_period_average":
            return TwoPeriodAverageNode.from_dict_with_context(data, context)

        # Handle forecast nodes
        elif node_type == "forecast":
            # Determine the specific forecast type from the data
            forecast_type = data.get("forecast_type")
            if not forecast_type:
                raise ValueError("Missing 'forecast_type' field in forecast node data")

            # Get the appropriate forecast node class
            forecast_class = cls._forecast_type_registry.get(forecast_type)
            if not forecast_class:
                valid_types = list(cls._forecast_type_registry.keys())
                raise ValueError(
                    f"Unknown forecast type '{forecast_type}'. Valid types: {valid_types}"
                )

            # Handle non-serializable forecast types
            if forecast_type in ["statistical", "custom"]:
                raise ConfigurationError(
                    f"Forecast type '{forecast_type}' cannot be deserialized because it contains "
                    "non-serializable functions. Manual reconstruction required."
                )

            # Use the specific forecast class's from_dict_with_context method
            return forecast_class.from_dict_with_context(data, context)

        # Handle specific forecast node types (for backward compatibility)
        elif node_type in cls._node_type_registry:
            node_class = cls._node_type_registry[node_type]
            if hasattr(node_class, "from_dict_with_context"):
                return cast(Node, node_class.from_dict_with_context(data, context))
            else:
                return cast(Node, node_class.from_dict(data))  # type: ignore[attr-defined]

        else:
            valid_types = list(cls._node_type_registry.keys())
            raise ValueError(
                f"Unknown node type: '{node_type}'. Valid types: {valid_types}"
            )

    @classmethod
    def _create_custom_node_from_callable(
        cls,
        name: str,
        inputs: list[Node],
        formula: Callable[..., Any],
        description: Optional[str] = None,
    ) -> CustomCalculationNode:
        """Create a :class:`CustomCalculationNode` from an arbitrary Python callable.

        This helper is useful for ad-hoc or complex calculations that are not
        (yet) formalized as reusable strategies. The supplied ``formula`` is
        invoked with the *values* of each input node during evaluation.

        Args:
            name: Identifier for the custom calculation node.
            inputs: List of nodes supplying arguments to ``formula``.
            formula: Callable performing the calculation.
            description: Human-readable description of the calculation logic.

        Returns:
            The newly created :class:`CustomCalculationNode` instance.

        Raises:
            ValueError: If *name* is empty.
            TypeError: If *formula* is not callable or *inputs* contain non-Node objects.

        Examples:
            Defining a tax-calculation node::

                def tax_logic(revenue, expenses, tax_rate):
                    profit = revenue - expenses
                    return max(profit, 0) * tax_rate

                tax_node = NodeFactory._create_custom_node_from_callable(
                    name="IncomeTax",
                    inputs=[revenue, expenses, tax_rate_node],
                    formula=tax_logic,
                )

            Using a lambda for a quick ratio::

                quick_ratio = NodeFactory._create_custom_node_from_callable(
                    name="QuickRatioCustom",
                    inputs=[cash, receivables, current_liabilities],
                    formula=lambda cash, rec, liab: (cash + rec) / liab if liab else 0,
                )
        """
        # Validate inputs
        if not name or not isinstance(name, str):
            raise ValueError("Node name must be a non-empty string")

        if not inputs:
            # Allowing no inputs might be valid for some custom functions (e.g., constants)
            # Reconsider if this check is always needed here.
            logger.warning(f"Creating CustomCalculationNode '{name}' with no inputs.")
            # raise ValueError("Custom node must have at least one input")  # noqa: ERA001

        if not callable(formula):
            raise TypeError("Formula must be a callable function")
        if not all(isinstance(i, Node) for i in inputs):
            raise TypeError("All items in inputs must be Node instances.")

        # Use the imported CustomCalculationNode
        logger.debug(f"Creating CustomCalculationNode: {name} using provided callable.")
        return CustomCalculationNode(
            name, inputs, formula_func=formula, description=description
        )
