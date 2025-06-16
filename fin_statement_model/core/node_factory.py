"""Factory helpers for creating nodes in the financial statement model.

This module centralizes node-creation logic to ensure consistent initialization
for all node types (financial statement items, calculations, forecasts, stats).
"""

import logging
from typing import Any, Callable, ClassVar, Optional, Union, cast

from fin_statement_model.core.errors import ConfigurationError

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

# ---------------------------------------------------------------------------
# Legacy calculation registry fully removed – client code should migrate to
# formula-based nodes via ``NodeFactory.create_calculation_node``.
# ---------------------------------------------------------------------------


# Configure logging
logger = logging.getLogger(__name__)


class NodeFactory:
    """Factory for creating nodes in the financial statement model.

    The class exposes convenience helpers that hide the underlying registry
    and deserialization logic, so client code can create nodes declaratively
    (e.g., via YAML configs or simple Python calls) without importing every
    concrete node class.

    Notes:
        • In **v2** the separate calculation registry has been removed.
          ``NodeFactory.create_calculation_node`` now produces a
          `FormulaCalculationNode` directly, constructing a Python expression
          from the provided inputs (or using an explicit *formula* keyword).

    Internal lookup tables:
        _calculation_methods: Legacy mapping from *calculation_type* keys to
            class names kept solely for backward-compat serialisation. They no
            longer need to exist in the runtime codebase.
        _node_type_registry: Mapping of node-type strings to concrete :class:`Node`
            subclasses used when deserialising from dictionaries.
    """

    # Legacy mapping preserved for <-> YAML round-trips; the concrete classes
    # no longer exist after removal of the old calculation registry but the string keys
    # are still used in `CalculationNode.to_dict()` to label the operation.
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
        # Refactored: build a FormulaCalculationNode directly – the legacy Calculation
        # registry was removed.  Supported *calculation_type*s now map to simple Python
        # expressions or to an explicit ``formula`` string supplied via **calculation_kwargs.

        # ------------------------------------------------------------------
        # Basic validation --------------------------------------------------
        # ------------------------------------------------------------------
        if not name or not isinstance(name, str):
            raise ValueError("Node name must be a non-empty string")
        if not inputs:
            raise ValueError("Calculation node must have at least one input")
        if not all(isinstance(n, Node) for n in inputs):
            raise TypeError("All items in *inputs* must be Node instances")

        calc_type = calculation_type.lower()

        # Helper: build formula string from *inputs* -----------------------------------
        def _expr_from_inputs(op: str) -> str:
            return f" {op} ".join(node.name for node in inputs)

        if calc_type in {"addition", "add"}:
            formula_expr = _expr_from_inputs("+")
        elif calc_type in {"subtraction", "subtract", "minus"}:
            if len(inputs) != 2:
                raise ValueError("subtraction requires exactly two inputs")
            formula_expr = f"{inputs[0].name} - {inputs[1].name}"
        elif calc_type in {"multiplication", "multiply"}:
            formula_expr = _expr_from_inputs("*")
        elif calc_type in {"division", "divide"}:
            if len(inputs) != 2:
                raise ValueError("division requires exactly two inputs")
            formula_expr = f"{inputs[0].name} / {inputs[1].name}"
        elif calc_type in {"formula", "custom_formula"}:
            # Expect explicit formula text in kwargs
            formula_expr = calculation_kwargs.pop("formula", None)
            if formula_expr is None:
                raise ValueError(
                    "'formula' keyword argument required when calculation_type is 'formula'"
                )
            # Replace placeholders if variable names provided -----------------
            if formula_variable_names:
                for placeholder, node in zip(
                    formula_variable_names, inputs, strict=False
                ):
                    formula_expr = formula_expr.replace(placeholder, node.name)
        else:
            raise ValueError(
                f"Unsupported calculation_type '{calculation_type}'. "
                "Supported types: addition, subtraction, multiplication, division, formula."
            )

        # ------------------------------------------------------------------
        # Build mapping variable → Node instance ---------------------------
        # ------------------------------------------------------------------
        inputs_dict = {node.name: node for node in inputs}

        # Extract optional metric metadata (pop to avoid passing to FCN) -----
        metric_name = calculation_kwargs.pop("metric_name", None)
        metric_description = calculation_kwargs.pop("metric_description", None)

        # ------------------------------------------------------------------
        # Return FormulaCalculationNode (subclass of CalculationNode) -------
        # ------------------------------------------------------------------
        return FormulaCalculationNode(
            name,
            inputs=inputs_dict,
            formula=formula_expr,
            metric_name=metric_name,
            metric_description=metric_description,
        )

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
