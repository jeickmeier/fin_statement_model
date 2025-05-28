"""Provide a factory for creating nodes in the financial statement model.

This module centralizes node creation logic and ensures consistent initialization
for different types of nodes used in the financial statement model.
"""

import logging
from typing import Any, Union, Optional, ClassVar
from collections.abc import Callable

# Force import of strategies package to ensure registration happens

from .nodes import (
    Node,
    FinancialStatementItemNode,
    CalculationNode,
    CustomCalculationNode,
)
from .nodes.forecast_nodes import (
    FixedGrowthForecastNode,
    CurveGrowthForecastNode,
    StatisticalGrowthForecastNode,
    AverageValueForecastNode,
    AverageHistoricalGrowthForecastNode,
)

# Force import of calculations package to ensure registration happens
from fin_statement_model.core.calculations import Registry, Calculation
from fin_statement_model.core.errors import ConfigurationError

# Configure logging
logger = logging.getLogger(__name__)


class NodeFactory:
    """Provide a factory for creating nodes in the financial statement model.

    This class centralizes node creation for financial statement items,
    calculations, metrics, forecasts, and custom logic.

    Attributes:
        _calculation_methods: Maps simple string keys (e.g., 'addition') to
            the class names of Calculation implementations registered in the
            `Registry`. This allows creating CalculationNodes without
            directly importing Calculation classes.
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

    # Mapping from node type names to Node classes
    _node_types: ClassVar[dict[str, type[Node]]] = {
        "financial_statement_item": FinancialStatementItemNode,
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
                node_kwargs["metric_description"] = calculation_kwargs.pop("metric_description")

            # Special handling for FormulaCalculation which needs input_variable_names
            if calculation_type == "formula":
                if formula_variable_names and len(formula_variable_names) == len(inputs):
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
        logger.debug(f"Creating calculation node '{name}' with '{calculation_name}' calculation.")

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
        # Instantiate the appropriate forecast node
        if forecast_type == "simple":
            node = FixedGrowthForecastNode(base_node, base_period, forecast_periods, growth_params)
        elif forecast_type == "curve":
            node = CurveGrowthForecastNode(base_node, base_period, forecast_periods, growth_params)
        elif forecast_type == "statistical":
            node = StatisticalGrowthForecastNode(
                base_node, base_period, forecast_periods, growth_params
            )
        elif forecast_type == "average":
            node = AverageValueForecastNode(base_node, base_period, forecast_periods)
        elif forecast_type == "historical_growth":
            node = AverageHistoricalGrowthForecastNode(base_node, base_period, forecast_periods)
        else:
            raise ValueError(f"Invalid forecast type: {forecast_type}")

        # Override forecast node's name to match factory 'name' argument
        node.name = name
        logger.debug(f"Forecast node created with custom name: {name} (original: {base_node.name})")
        return node

    @classmethod
    def _create_custom_node_from_callable(
        cls,
        name: str,
        inputs: list[Node],
        formula: Callable,
        description: Optional[str] = None,
    ) -> CustomCalculationNode:
        """Create a CustomCalculationNode using a Python callable for the calculation logic.

        This supports ad-hoc or complex calculations not covered by standard
        strategies or metrics. The `formula` callable will be invoked with
        input node values at calculation time.

        Note:
            Renamed from `create_metric_node` to avoid confusion with metric-based nodes.

        Args:
            name: Identifier for the custom calculation node.
            inputs: List of Node instances providing values to the formula.
            formula: Callable that computes a value from input node values.
            description: Optional description of the calculation logic.

        Returns:
            A CustomCalculationNode configured with the provided formula.

        Raises:
            ValueError: If name is empty or not a string.
            TypeError: If formula is not callable or inputs contain non-Node items.

        Examples:
            >>> def complex_tax_logic(revenue, expenses, tax_rate_node):
            ...     profit = revenue - expenses
            ...     if profit <= 0:
            ...         return 0.0
            ...     tax_rate = tax_rate_node
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
