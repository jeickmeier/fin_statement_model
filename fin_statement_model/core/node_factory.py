"""Node Factory for the Financial Statement Model.

This module provides a factory for creating different types of nodes used in the financial statement model.
It centralizes node creation logic and ensures consistent node initialization.
"""

import logging
from typing import Callable, Any, Union, Optional, ClassVar

# Force import of strategies package to ensure registration happens

from .nodes import (
    Node,
    FinancialStatementItemNode,
    StrategyCalculationNode,
    MetricCalculationNode,
    CustomCalculationNode,
)
from .nodes.forecast_nodes import (
    FixedGrowthForecastNode,
    CurveGrowthForecastNode,
    StatisticalGrowthForecastNode,
    AverageValueForecastNode,
    AverageHistoricalGrowthForecastNode,
)

# Use absolute import for Registry to ensure consistency
# from .strategies import Registry, Strategy
from fin_statement_model.core.strategies import Registry, Strategy

# Configure logging
logger = logging.getLogger(__name__)


class NodeFactory:
    """Factory class for creating nodes in the financial statement model.

    This class centralizes the creation of all types of nodes, ensuring consistent
    initialization and simplifying the creation process. It provides methods
    for creating financial statement items, calculation nodes (via strategies,
    metrics, or custom functions).

    Attributes:
        _calculation_strategies: Maps simple string keys (e.g., 'addition') to
            the class names of Strategy implementations registered in the
            `Registry`. This allows creating StrategyCalculationNodes without
            directly importing Strategy classes.
    """

    # Mapping of calculation type strings to strategy names (keys in the Registry)
    _calculation_strategies: ClassVar[dict[str, str]] = {
        "addition": "AdditionStrategy",
        "subtraction": "SubtractionStrategy",
        "multiplication": "MultiplicationStrategy",
        "division": "DivisionStrategy",
        "weighted_average": "WeightedAverageStrategy",
        "custom_formula": "CustomFormulaStrategy",
    }

    # Mapping from node type names to Node classes
    _node_types: ClassVar[dict[str, type[Node]]] = {
        "financial_statement_item": FinancialStatementItemNode,
        "metric_calculation": MetricCalculationNode,
    }

    @classmethod
    def create_financial_statement_item(
        cls, name: str, values: dict[str, float]
    ) -> FinancialStatementItemNode:
        """Creates a FinancialStatementItemNode representing a base financial item.

        This node typically holds historical or projected values for a specific
        line item (e.g., Revenue, COGS) over different periods.

        Args:
            name: The unique identifier for the node (e.g., "Revenue").
            values: A dictionary where keys are period identifiers (e.g., "2023Q1")
                and values are the corresponding numerical values for that period.

        Returns:
            An initialized FinancialStatementItemNode.

        Raises:
            ValueError: If the provided name is empty or not a string.

        Example:
            >>> revenue_node = NodeFactory.create_financial_statement_item(
            ...     name="Revenue",
            ...     values={"2023": 1000.0, "2024": 1100.0}
            ... )
            >>> revenue_node.name
            'Revenue'
            >>> revenue_node.get_value("2023")
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
        **strategy_kwargs: Any,
    ) -> StrategyCalculationNode:
        """Creates a StrategyCalculationNode using a pre-defined calculation strategy.

        This method looks up the calculation strategy based on the `calculation_type`
        string (e.g., 'addition', 'division') in the `_calculation_strategies`
        map, retrieves the corresponding Strategy class from the `Registry`,
        instantiates it (passing `strategy_kwargs`), and creates the node.

        Args:
            name: The unique identifier for the calculation node (e.g., "GrossProfit").
            inputs: A list of Node objects that serve as inputs to the calculation.
            calculation_type: A string key representing the desired calculation
                (e.g., 'addition', 'subtraction', 'custom_formula'). Must match a
                key in `_calculation_strategies`.
            **strategy_kwargs: Additional keyword arguments required by the specific
                Strategy's constructor. For example, 'CustomFormulaStrategy' might
                require a 'formula_string' kwarg.

        Returns:
            An initialized StrategyCalculationNode configured with the specified strategy.

        Raises:
            ValueError: If `name` is invalid, `inputs` is empty, `calculation_type`
                is not found in `_calculation_strategies`, or the corresponding
                strategy name is not registered in the `Registry`.
            TypeError: If the resolved strategy class cannot be instantiated with
                the provided `strategy_kwargs`.

        Example:
            Assuming 'revenue_node' and 'cogs_node' exist:
            >>> gross_profit_node = NodeFactory.create_calculation_node(
            ...     name="GrossProfit",
            ...     inputs=[revenue_node, cogs_node],
            ...     calculation_type="subtraction"
            ... )

            Using a strategy that requires extra arguments:
            >>> weighted_cost_node = NodeFactory.create_calculation_node(
            ...     name="WeightedCost",
            ...     inputs=[cost_node1, cost_node2],
            ...     calculation_type="weighted_average",
            ...     weights=[0.6, 0.4] # Passed as strategy_kwargs
            ... )

            Using a custom formula string (assuming 'CustomFormulaStrategy' exists):
            >>> ratio_node = NodeFactory.create_calculation_node(
            ...     name="DebtEquityRatio",
            ...     inputs=[debt_node, equity_node],
            ...     calculation_type="custom_formula",
            ...     formula_string="debt / equity" # Passed as strategy_kwargs
            ... )
        """
        # Validate inputs
        if not name or not isinstance(name, str):
            raise ValueError("Node name must be a non-empty string")

        if not inputs:
            raise ValueError("Calculation node must have at least one input")

        # Check if the calculation type maps to a known strategy name
        if calculation_type not in cls._calculation_strategies:
            valid_types = list(cls._calculation_strategies.keys())
            raise ValueError(
                f"Invalid calculation type: '{calculation_type}'. Valid types are: {valid_types}"
            )

        # Get the strategy name and resolve the strategy class from the registry
        strategy_name = cls._calculation_strategies[calculation_type]
        try:
            # Assuming Registry.get returns the strategy class
            strategy_cls: type[Strategy] = Registry.get(strategy_name)
        except KeyError:
            raise ValueError(
                f"Strategy '{strategy_name}' not found in Registry for type '{calculation_type}'"
            )

        # Instantiate the strategy, passing any extra kwargs
        try:
            strategy_instance = strategy_cls(**strategy_kwargs)
        except TypeError as e:
            logger.exception(
                f"Failed to instantiate strategy '{strategy_name}' with kwargs {strategy_kwargs}"
            )
            raise TypeError(
                f"Could not instantiate strategy '{strategy_name}' for node '{name}'. "
                f"Check required arguments for {strategy_cls.__name__}. Provided kwargs: {strategy_kwargs}"
            ) from e

        # Create and return a StrategyCalculationNode with the instantiated strategy
        logger.debug(
            f"Creating strategy calculation node '{name}' with '{strategy_name}' strategy."
        )
        return StrategyCalculationNode(name, inputs, strategy_instance)

    @classmethod
    def create_metric_node(
        cls, name: str, metric_name: str, input_nodes: dict[str, Node]
    ) -> MetricCalculationNode:
        """Creates a MetricCalculationNode based on a pre-defined metric definition.

        This node represents a standard financial metric (e.g., "current_ratio")
        whose calculation logic (inputs, formula) is defined elsewhere, typically
        loaded from configuration (like YAML files) and managed by the
        `MetricCalculationNode` itself or a metric registry.

        Args:
            name: The unique identifier for this specific instance of the metric node
                (e.g., "CompanyCurrentRatio").
            metric_name: The key identifying the metric definition (e.g.,
                "current_ratio"). This key is used by `MetricCalculationNode`
                to look up the definition (inputs, formula, description).
            input_nodes: A dictionary mapping the *required input names* defined
                in the metric definition (e.g., "total_current_assets") to the
                actual `Node` objects providing those values (e.g.,
                `{"total_current_assets": assets_node, "total_current_liabilities": liab_node}`).

        Returns:
            An initialized MetricCalculationNode instance, ready to calculate the metric.

        Raises:
            ValueError: If `name` is invalid, `metric_name` does not correspond to a
                valid metric definition, the definition is incomplete, or the
                provided `input_nodes` do not match the required inputs specified
                in the metric definition (missing keys, extra keys, wrong types).
            TypeError: If `input_nodes` is not a dictionary.

        Example:
            Assuming 'assets_node' and 'liabilities_node' exist, and a metric
            definition for "current_ratio" exists requiring inputs named
            "current_assets" and "current_liabilities":
            >>> current_ratio_node = NodeFactory.create_metric_node(
            ...     name="CompanyCurrentRatio",
            ...     metric_name="current_ratio",
            ...     input_nodes={
            ...         "current_assets": assets_node,
            ...         "current_liabilities": liabilities_node
            ...     }
            ... )
        """
        logger.debug(f"Attempting to create metric node '{name}' for metric '{metric_name}'")

        # Basic input validation
        if not name or not isinstance(name, str):
            raise ValueError("Node name must be a non-empty string")
        if not isinstance(input_nodes, dict):
            raise TypeError("input_nodes must be a dictionary of Node objects.")

        # The MetricCalculationNode constructor now handles definition loading,
        # validation of the definition, and validation of input_nodes.
        try:
            node = MetricCalculationNode(
                name=name, metric_name=metric_name, input_nodes=input_nodes
            )
            logger.info(
                f"Successfully created MetricCalculationNode '{name}' for metric '{metric_name}'"
            )
            return node
        except (ValueError, TypeError):
            logger.exception(
                f"Failed to create MetricCalculationNode '{name}' for metric '{metric_name}'"
            )
            # Re-raise the specific error from the constructor
            raise
        else:
            return node

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
        """Create a forecast node of the specified type using core forecast classes."""
        if forecast_type == "fixed":
            return FixedGrowthForecastNode(base_node, base_period, forecast_periods, growth_params)
        elif forecast_type == "curve":
            return CurveGrowthForecastNode(base_node, base_period, forecast_periods, growth_params)
        elif forecast_type == "statistical":
            return StatisticalGrowthForecastNode(
                base_node, base_period, forecast_periods, growth_params
            )
        elif forecast_type == "average":
            return AverageValueForecastNode(base_node, base_period, forecast_periods, growth_params)
        elif forecast_type == "historical_growth":
            return AverageHistoricalGrowthForecastNode(
                base_node, base_period, forecast_periods, growth_params
            )
        else:
            raise ValueError(f"Invalid forecast type: {forecast_type}")

    @classmethod
    def _create_custom_node_from_callable(
        cls,
        name: str,
        inputs: list[Node],
        formula: Callable,
        description: Optional[str] = None,
    ) -> CustomCalculationNode:
        """Creates a CustomCalculationNode using a Python callable for the calculation logic.

        This is suitable for ad-hoc or complex calculations that are not covered by
        standard strategies or pre-defined metrics. The provided `formula` function
        will be executed during the calculation phase.

        Note:
            Previously named `create_metric_node`, renamed to avoid confusion with
            `MetricCalculationNode` which relies on defined metric specifications.

        Args:
            name: The unique identifier for the custom calculation node.
            inputs: A list of Node objects whose values will be passed as arguments
                to the `formula` function during calculation. The order matters if
                the formula expects positional arguments.
            formula: A Python callable (function, lambda, method) that performs the
                calculation. It should accept arguments corresponding to the values
                of the `inputs` nodes for a given period and return the calculated value.
            description: An optional string describing the purpose of the calculation.

        Returns:
            An initialized CustomCalculationNode.

        Raises:
            ValueError: If `name` is invalid.
            TypeError: If `formula` is not a callable or if any item in `inputs`
                is not a `Node` instance.

        Example:
            >>> def complex_tax_logic(revenue, expenses, tax_rate_node):
            ...     profit = revenue - expenses
            ...     if profit <= 0:
            ...         return 0.0
            ...     # Assume tax_rate_node.get_value(period) returns the rate
            ...     # (Actual implementation details depend on how CalculationEngine passes values)
            ...     # This example assumes values are passed directly
            ...     tax_rate = tax_rate_node # Or the value extracted by the engine
            ...     return profit * tax_rate
            ...
            >>> tax_node = NodeFactory._create_custom_node_from_callable(
            ...     name="CalculatedTaxes",
            ...     inputs=[revenue_node, expenses_node, tax_rate_schedule_node],
            ...     formula=complex_tax_logic,
            ...     description="Calculates income tax based on profit and a variable rate."
            ... )

            Using a lambda for a simple ratio:
            >>> quick_ratio_node = NodeFactory._create_custom_node_from_callable(
            ...    name="QuickRatioCustom",
            ...    inputs=[cash_node, receivables_node, current_liabilities_node],
            ...    formula=lambda cash, rec, liab: (cash + rec) / liab if liab else 0
            ... )
        """
        # Validate inputs
        if not name or not isinstance(name, str):
            raise ValueError("Node name must be a non-empty string")

        if not inputs:
            # Allowing no inputs might be valid for some custom functions (e.g., constants)
            # Reconsider if this check is always needed here.
            logger.warning(f"Creating CustomCalculationNode '{name}' with no inputs.")
            # raise ValueError("Custom node must have at least one input")

        if not callable(formula):
            raise TypeError("Formula must be a callable function")
        if not all(isinstance(i, Node) for i in inputs):
            raise TypeError("All items in inputs must be Node instances.")

        # Use the imported CustomCalculationNode
        logger.debug(f"Creating CustomCalculationNode: {name} using provided callable.")
        return CustomCalculationNode(name, inputs, formula_func=formula, description=description)

    # Consider adding a method for creating FormulaCalculationNode if needed directly
    # @classmethod
    # def create_formula_node(cls, name: str, inputs: Dict[str, Node], formula: str) -> FormulaCalculationNode:
    #     ...
