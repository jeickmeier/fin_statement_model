"""Forecasting operations dedicated to statement-level financial graphs.

This module provides the StatementForecaster class, which handles forecasting
operations for financial statement graphs. It offers both mutating operations
(that modify the graph) and non-mutating operations (that return forecast values
without changing the graph state).
"""

import logging
from typing import Any, Optional, cast
import numpy as np

# Core imports
from fin_statement_model.core.nodes import Node
from fin_statement_model.core.node_factory import NodeFactory

# Forecasting module imports
from .period_manager import PeriodManager
from .validators import ForecastValidator
from .strategies import get_forecast_method
from .types import ForecastConfig, ForecastResult
from .methods import BaseForecastMethod

logger = logging.getLogger(__name__)


class StatementForecaster:
    """Handles forecasting operations specifically for a FinancialStatementGraph.

    This class provides two main approaches to forecasting:

    1. **Mutating operations** (`create_forecast`): Modifies the graph by adding
       forecast periods and updating node values directly. This is useful when
       you want to extend the graph with forecast data for further analysis.

    2. **Non-mutating operations** (`forecast_value`): Returns forecast values
       without modifying the graph state. This is useful for what-if scenarios
       or when you need forecast values without altering the original data.

    The forecaster supports multiple forecasting methods:
    - simple: Simple growth rate
    - curve: Variable growth rates per period
    - statistical: Random sampling from distributions
    - average: Average of historical values
    - historical_growth: Based on historical growth patterns
    """

    def __init__(self, fsg: Any) -> None:
        """Initialize the forecaster.

        Args:
            fsg: The FinancialStatementGraph instance this forecaster will operate on.
        """
        self.fsg = fsg

    def create_forecast(
        self,
        forecast_periods: list[str],
        node_configs: Optional[dict[str, dict[str, Any]]] = None,
        historical_periods: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Create forecasts for financial statement items on the graph.

        **IMPORTANT**: This method MUTATES the graph by:
        - Adding new periods to the graph if they don't exist
        - Updating node values with forecast data
        - Clearing node caches after updates

        Use `forecast_value` instead if you need forecast values without
        modifying the graph.

        Args:
            forecast_periods: List of future periods to forecast.
            node_configs: Mapping of node names to their forecast configurations.
                Each config should contain:
                - 'method': Forecasting method ('simple', 'curve', 'statistical',
                           'average', 'historical_growth')
                - 'config': Method-specific parameters (growth rate, distribution, etc.)
            historical_periods: Optional list of historical periods to use as base.
                If not provided, will be inferred from the graph's existing periods.
            **kwargs: Additional arguments passed to the forecasting logic.

        Returns:
            None (modifies the graph in-place)

        Raises:
            ValueError: If no historical periods found, no forecast periods provided,
                       or invalid forecasting method/configuration.

        Example:
            >>> forecaster = StatementForecaster(graph)
            >>> forecaster.create_forecast(
            ...     forecast_periods=['2024', '2025'],
            ...     node_configs={
            ...         'revenue': {'method': 'simple', 'config': 0.05},  # 5% growth
            ...         'costs': {'method': 'curve', 'config': [0.03, 0.04]}  # Variable growth
            ...     }
            ... )
        """
        logger.info(f"StatementForecaster: Creating forecast for periods {forecast_periods}")
        try:
            # Use PeriodManager to infer historical periods
            historical_periods = PeriodManager.infer_historical_periods(
                self.fsg, forecast_periods, historical_periods
            )

            # Validate inputs using ForecastValidator
            ForecastValidator.validate_forecast_inputs(
                historical_periods, forecast_periods, node_configs
            )

            # Ensure forecast periods exist in the graph
            PeriodManager.ensure_periods_exist(self.fsg, forecast_periods, add_missing=True)

            if node_configs is None:
                node_configs = {}

            for node_name, config in node_configs.items():
                node = self.fsg.get_node(node_name)
                if node is None:
                    raise ValueError(f"Node {node_name} not found in graph")

                # Validate node can be forecasted
                forecast_config = ForecastValidator.validate_forecast_config(config)
                ForecastValidator.validate_node_for_forecast(node, forecast_config.method)

                self._forecast_node(node, historical_periods, forecast_periods, forecast_config)

            logger.info(
                f"Created forecast for {len(forecast_periods)} periods and {len(node_configs)} nodes"
            )
        except Exception as e:
            logger.error(f"Error creating forecast: {e}", exc_info=True)
            raise

    def _forecast_node(
        self,
        node: Node,
        historical_periods: list[str],
        forecast_periods: list[str],
        forecast_config: ForecastConfig,
        **kwargs: Any,
    ) -> None:
        """Calculate forecast values and update the original node.

        **IMPORTANT**: This is an internal MUTATING method that:
        - Creates a temporary forecast node for calculations
        - Updates the original node's values dictionary with forecast results
        - Clears the original node's cache after updates

        This method should not be called directly. Use `create_forecast` for
        mutating operations or `forecast_value` for non-mutating operations.

        Args:
            node: The graph node to forecast. Must have a 'values' dictionary.
            historical_periods: List of historical periods for base values.
            forecast_periods: List of periods for which to calculate forecasts.
            forecast_config: Validated forecast configuration.
            **kwargs: Additional arguments passed to growth logic.

        Returns:
            None (modifies the node in-place)

        Raises:
            ValueError: If no historical periods provided or invalid method.

        Side Effects:
            - Modifies node.values dictionary with forecast data
            - Clears node cache if clear_cache method exists
        """
        logger.debug(
            f"StatementForecaster: Forecasting node {node.name} using method {forecast_config.method}"
        )

        # Determine base period using PeriodManager
        base_period = PeriodManager.determine_base_period(node, historical_periods)

        # Get the forecast method from registry
        method = get_forecast_method(forecast_config.method)

        # Get normalized parameters for NodeFactory
        # All built-in methods extend BaseForecastMethod which has get_forecast_params
        base_method = cast(BaseForecastMethod, method)
        params = base_method.get_forecast_params(forecast_config.config, forecast_periods)

        # Create a temporary node to perform calculations
        tmp_node = NodeFactory.create_forecast_node(
            name=f"{node.name}_forecast_temp",
            base_node=node,
            base_period=base_period,
            forecast_periods=forecast_periods,
            forecast_type=params["forecast_type"],
            growth_params=params["growth_params"],
        )

        # Ensure the original node has a values dictionary
        if not hasattr(node, "values") or not isinstance(node.values, dict):
            logger.error(
                f"Cannot store forecast for node {node.name}: node does not have a 'values' dictionary."
            )
            return  # Cannot proceed

        # Calculate and update original node's values
        for period in forecast_periods:
            try:
                val = tmp_node.calculate(period)
                if np.isnan(val) or np.isinf(val):
                    logger.warning(
                        f"Bad forecast {val} for {node.name}@{period}; defaulting to 0.0"
                    )
                    val = 0.0
                node.values[period] = float(val)  # Update the original node
            except Exception as e:
                logger.error(f"Error forecasting {node.name}@{period}: {e}", exc_info=True)
                node.values[period] = 0.0  # Set default on error

        # Clear cache of the original node as its values have changed
        if hasattr(node, "clear_cache") and callable(node.clear_cache):
            node.clear_cache()  # type: ignore[no-untyped-call]
            logger.debug(f"Cleared cache for node {node.name} after forecast update.")

    def forecast_value(
        self,
        node_name: str,
        forecast_periods: list[str],
        base_period: Optional[str] = None,
        forecast_config: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> dict[str, float]:
        """Forecast and return values for a node without mutating the graph.

        **IMPORTANT**: This is a NON-MUTATING method that:
        - Does NOT add periods to the graph
        - Does NOT modify any node values
        - Does NOT affect the graph state in any way
        - Returns forecast values as a separate dictionary

        This method is ideal for:
        - What-if analysis
        - Comparing different forecast scenarios
        - Getting forecast values without committing them to the graph
        - API responses where you don't want to modify server state

        Args:
            node_name: Name of the node to forecast.
            forecast_periods: List of future periods to forecast.
            base_period: Optional base period to use for forecasting.
                        If omitted, will be inferred from the node's historical data.
            forecast_config: Forecast configuration dict with:
                - 'method': Forecasting method ('simple', 'curve', 'statistical',
                           'average', 'historical_growth')
                - 'config': Method-specific parameters
                If not provided, defaults to simple method with 0% growth.
            **kwargs: Additional arguments passed to the internal forecasting logic.

        Returns:
            A dictionary mapping forecast periods to their calculated values.
            Example: {'2024': 1050.0, '2025': 1102.5}

        Raises:
            ValueError: If node not found, no historical periods available,
                       or invalid forecast configuration.

        Example:
            >>> forecaster = StatementForecaster(graph)
            >>> # Get forecast without modifying the graph
            >>> values = forecaster.forecast_value(
            ...     'revenue',
            ...     forecast_periods=['2024', '2025'],
            ...     forecast_config={'method': 'simple', 'config': 0.05}
            ... )
            >>> print(values)  # {'2024': 1050.0, '2025': 1102.5}
            >>> # Original graph remains unchanged
        """
        # Locate the node
        node = self.fsg.get_node(node_name)
        if node is None:
            raise ValueError(f"Node {node_name} not found in graph")

        # Determine historical periods
        if base_period:
            historical_periods = [base_period]
        else:
            historical_periods = PeriodManager.infer_historical_periods(self.fsg, forecast_periods)

        # Validate inputs
        ForecastValidator.validate_forecast_inputs(historical_periods, forecast_periods)

        # Set default config if not provided
        if forecast_config is None:
            forecast_config = {"method": "simple", "config": 0.0}

        # Validate and create ForecastConfig
        validated_config = ForecastValidator.validate_forecast_config(forecast_config)
        ForecastValidator.validate_node_for_forecast(node, validated_config.method)

        # Determine base period
        calc_base_period = PeriodManager.determine_base_period(
            node, historical_periods, base_period
        )

        # Get the forecast method from registry
        method = get_forecast_method(validated_config.method)

        # Get normalized parameters for NodeFactory
        # All built-in methods extend BaseForecastMethod which has get_forecast_params
        base_method = cast(BaseForecastMethod, method)
        params = base_method.get_forecast_params(validated_config.config, forecast_periods)

        # Create a temporary forecast node (DO NOT add to graph)
        try:
            temp_forecast_node = NodeFactory.create_forecast_node(
                name=f"{node_name}_temp_forecast",
                base_node=node,
                base_period=calc_base_period,
                forecast_periods=forecast_periods,
                forecast_type=params["forecast_type"],
                growth_params=params["growth_params"],
            )
        except Exception as e:
            logger.error(
                f"Failed to create temporary forecast node for '{node_name}': {e}",
                exc_info=True,
            )
            raise ValueError(f"Could not create temporary forecast node: {e}") from e

        # Calculate results using the temporary node
        results: dict[str, float] = {}
        for period in forecast_periods:
            try:
                value = temp_forecast_node.calculate(period)
                # Handle potential NaN/Inf results from calculation
                results[period] = 0.0 if not np.isfinite(value) else float(value)
            except Exception as e:
                logger.warning(
                    f"Error calculating temporary forecast for {node_name}@{period}: {e}. Returning 0.0"
                )
                results[period] = 0.0

        # Validate results before returning
        ForecastValidator.validate_forecast_result(results, forecast_periods, node_name)

        return results

    def forecast_multiple(
        self,
        node_names: list[str],
        forecast_periods: list[str],
        forecast_configs: Optional[dict[str, dict[str, Any]]] = None,
        base_period: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, ForecastResult]:
        """Forecast multiple nodes without mutating the graph.

        This is a convenience method that forecasts multiple nodes at once
        and returns structured results.

        Args:
            node_names: List of node names to forecast.
            forecast_periods: List of future periods to forecast.
            forecast_configs: Optional mapping of node names to their forecast configs.
                             If not provided, uses simple method with 0% growth for all.
            base_period: Optional base period to use for all nodes.
            **kwargs: Additional arguments passed to forecast_value.

        Returns:
            Dictionary mapping node names to ForecastResult objects.

        Example:
            >>> results = forecaster.forecast_multiple(
            ...     ['revenue', 'costs'],
            ...     ['2024', '2025'],
            ...     {'revenue': {'method': 'simple', 'config': 0.05}}
            ... )
            >>> print(results['revenue'].get_value('2024'))
        """
        results = {}
        configs = forecast_configs or {}

        for node_name in node_names:
            try:
                # Get config for this node or use default
                node_config = configs.get(node_name)

                # Forecast the node
                values = self.forecast_value(
                    node_name, forecast_periods, base_period, node_config, **kwargs
                )

                # Determine actual base period used
                node = self.fsg.get_node(node_name)
                historical_periods = PeriodManager.infer_historical_periods(
                    self.fsg, forecast_periods
                )
                actual_base_period = PeriodManager.determine_base_period(
                    node, historical_periods, base_period
                )

                # Create ForecastResult
                config = ForecastValidator.validate_forecast_config(
                    node_config or {"method": "simple", "config": 0.0}
                )

                results[node_name] = ForecastResult(
                    node_name=node_name,
                    periods=forecast_periods,
                    values=values,
                    method=config.method,
                    base_period=actual_base_period,
                )
            except Exception:
                logger.exception(f"Error forecasting node {node_name}")
                # Continue with other nodes
                continue

        return results
