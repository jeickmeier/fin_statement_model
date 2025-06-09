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
from fin_statement_model.config import cfg
from fin_statement_model.core.nodes import Node
from fin_statement_model.core.node_factory import NodeFactory
from fin_statement_model.forecasting.errors import (
    ForecastNodeError,
)

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
            **kwargs: Additional arguments passed to the forecasting logic:
                add_missing_periods (bool): Whether to add missing forecast periods to the graph.

        Returns:
            None (modifies the graph in-place)

        Raises:
            ForecastNodeError: If no historical periods found, no forecast periods provided,
                              or invalid forecasting method/configuration.
        """
        logger.info(
            f"StatementForecaster: Creating forecast for periods {forecast_periods}"
        )
        try:
            # Use PeriodManager to infer historical periods
            historical_periods = PeriodManager.infer_historical_periods(
                self.fsg, forecast_periods, historical_periods
            )

            # Validate inputs using ForecastValidator
            ForecastValidator.validate_forecast_inputs(
                historical_periods, forecast_periods, node_configs
            )

            # Ensure forecast periods exist in the graph (override via add_missing_periods)
            add_missing = kwargs.get(
                "add_missing_periods", cfg("forecasting.add_missing_periods")
            )
            PeriodManager.ensure_periods_exist(
                self.fsg, forecast_periods, add_missing=add_missing
            )

            if node_configs is None:
                node_configs = {}

            for node_name, config in node_configs.items():
                node = self.fsg.get_node(node_name)
                if node is None:
                    raise ForecastNodeError(
                        f"Node {node_name} not found in graph",
                        node_id=node_name,
                        available_nodes=list(self.fsg.nodes.keys()),
                    )

                # Validate node can be forecasted
                forecast_config = ForecastValidator.validate_forecast_config(config)
                ForecastValidator.validate_node_for_forecast(
                    node, forecast_config.method
                )

                self._forecast_node(
                    node, historical_periods, forecast_periods, forecast_config
                )

            logger.info(
                f"Created forecast for {len(forecast_periods)} periods and {len(node_configs)} nodes"
            )
        except Exception as e:
            logger.error(f"Error creating forecast: {e}", exc_info=True)
            raise ForecastNodeError(
                f"Error creating forecast: {e}", node_id=None, reason=str(e)
            )

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
            ForecastNodeError: If no historical periods provided or invalid method.
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
        params = base_method.get_forecast_params(
            forecast_config.config, forecast_periods
        )

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
                # Default fallback for bad forecasts, overrideable via bad_forecast_value kwarg
                bad_value = kwargs.get(
                    "bad_forecast_value", cfg("forecasting.default_bad_forecast_value")
                )
                if np.isnan(val) or np.isinf(val):
                    logger.warning(
                        f"Bad forecast {val} for {node.name}@{period}; defaulting to {bad_value}"
                    )
                    val = bad_value
                # Clamp negative values if disallowed
                allow_neg = kwargs.get(
                    "allow_negative_forecasts",
                    cfg("forecasting.allow_negative_forecasts"),
                )
                if not allow_neg and val < 0:
                    # Ensure bad_value is non-negative when clamping negative values
                    if bad_value < 0:
                        logger.warning(
                            f"bad_forecast_value ({bad_value}) is negative but allow_negative_forecasts is False. Using 0.0 instead."
                        )
                        bad_value = 0.0
                    logger.warning(
                        f"Negative forecast {val} for {node.name}@{period}; clamping to {bad_value}"
                    )
                    val = bad_value
                node.values[period] = float(val)  # Update the original node
            except Exception as e:
                logger.error(
                    f"Error forecasting {node.name}@{period}: {e}", exc_info=True
                )
                node.values[period] = bad_value  # Set default on error

        # Clear cache of the original node as its values have changed
        if hasattr(node, "clear_cache") and callable(node.clear_cache):
            node.clear_cache()
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
                If not provided, uses global forecasting defaults.
            **kwargs: Additional arguments passed to the internal forecasting logic.
                bad_forecast_value (float): Default to use for NaN/Inf or errors (overrides config)
                allow_negative_forecasts (bool): Whether to allow negative forecast values (overrides config)

        Returns:
            A dictionary mapping forecast periods to their calculated values.
            Example: {'2024': 1050.0, '2025': 1102.5}

        Raises:
            ForecastNodeError: If node not found, no historical periods available,
                              or invalid forecast configuration.
        """
        # Optional override for bad forecast fallback
        bad_value = kwargs.get(
            "bad_forecast_value", cfg("forecasting.default_bad_forecast_value")
        )
        # Locate the node
        node = self.fsg.get_node(node_name)
        if node is None:
            raise ForecastNodeError(
                f"Node {node_name} not found in graph",
                node_id=node_name,
                available_nodes=list(self.fsg.nodes.keys()),
            )

        # Determine historical periods
        if base_period:
            historical_periods = [base_period]
        else:
            historical_periods = PeriodManager.infer_historical_periods(
                self.fsg, forecast_periods
            )

        # Validate inputs
        ForecastValidator.validate_forecast_inputs(historical_periods, forecast_periods)

        # Set default config if not provided, using global forecasting defaults
        if forecast_config is None:
            default_method = cfg("forecasting.default_method")
            # Use method-appropriate default config
            if default_method == "simple":
                forecast_config = {
                    "method": default_method,
                    "config": cfg("forecasting.default_growth_rate"),
                }
            else:
                # For other methods, use empty config and let the method handle defaults
                forecast_config = {"method": default_method, "config": {}}

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
        params = base_method.get_forecast_params(
            validated_config.config, forecast_periods
        )

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
            raise ForecastNodeError(
                f"Could not create temporary forecast node: {e}",
                node_id=node_name,
                reason=str(e),
            )

        # Calculate results using the temporary node
        results: dict[str, float] = {}
        for period in forecast_periods:
            try:
                value = temp_forecast_node.calculate(period)
                # Handle potential NaN/Inf results from calculation
                results[period] = bad_value if not np.isfinite(value) else float(value)
                # Clamp negative values if disallowed
                allow_neg = kwargs.get(
                    "allow_negative_forecasts",
                    cfg("forecasting.allow_negative_forecasts"),
                )
                if not allow_neg and results[period] < 0:
                    logger.warning(
                        f"Negative forecast {results[period]} for {node_name}@{period}; clamping to {bad_value}"
                    )
                    results[period] = bad_value
            except Exception as e:
                logger.warning(
                    f"Error calculating temporary forecast for {node_name}@{period}: {e}. Returning {bad_value}"
                )
                results[period] = bad_value

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
        # Determine error propagation strategy (override via continue_on_error kwarg)
        continue_on_err = kwargs.get(
            "continue_on_error", cfg("forecasting.continue_on_error")
        )
        results: dict[str, ForecastResult] = {}
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
                default_method = cfg("forecasting.default_method")
                config = ForecastValidator.validate_forecast_config(
                    node_config
                    or {
                        "method": default_method,
                        "config": cfg("forecasting.default_growth_rate"),
                    }
                )

                results[node_name] = ForecastResult(
                    node_name=node_name,
                    periods=forecast_periods,
                    values=values,
                    method=config.method,
                    base_period=actual_base_period,
                )
            except Exception as e:
                logger.exception(f"Error forecasting node {node_name}")
                if continue_on_err:
                    continue
                raise ForecastNodeError(
                    f"Error forecasting node {node_name}: {e}",
                    node_id=node_name,
                    reason=str(e),
                )

        return results

    def forecast_node(
        self,
        node_name: str,
        config: ForecastConfig,
        historical_periods: Optional[int] = None,
    ) -> ForecastResult:
        """Forecast values for a specific node.

        Args:
            node_name: Name of the node to forecast
            config: Forecast configuration
            historical_periods: Number of historical periods to use

        Returns:
            ForecastResult containing the forecasted values

        Raises:
            ForecastNodeError: If node not found in graph
        """
        if node_name not in self.fsg.nodes:
            raise ForecastNodeError(
                f"Node {node_name} not found in graph",
                node_id=node_name,
                available_nodes=list(self.fsg.nodes.keys()),
            )
        # TODO: implement detailed forecasting logic for a single node
        raise NotImplementedError("forecast_node is not implemented")

    def forecast_all(
        self,
        default_config: ForecastConfig,
        node_configs: Optional[dict[str, ForecastConfig]] = None,
    ) -> dict[str, ForecastResult]:
        """Forecast all forecastable nodes in the graph.

        Args:
            default_config: Default configuration for nodes without specific config
            node_configs: Optional node-specific configurations

        Returns:
            Dictionary mapping node names to forecast results

        Raises:
            ForecastNodeError: If node not found in graph
        """
        node_configs = node_configs or {}
        results = {}

        for node_name, node in self.fsg.nodes.items():
            if self._is_forecastable(node):
                config = node_configs.get(node_name, default_config)
                try:
                    results[node_name] = self.forecast_node(node_name, config)
                except Exception as e:
                    logger.warning(f"Failed to forecast {node_name}: {e}")
                    continue

        return results

    def _is_forecastable(self, node: Node) -> bool:
        """Determine if a node is forecastable (has a 'values' dictionary)."""
        return hasattr(node, "values") and isinstance(node.values, dict)

    def create_forecast_node(
        self,
        base_node_name: str,
        forecast_name: str,
        config: ForecastConfig,
    ) -> str:
        """Create a new forecast node based on an existing node.

        Args:
            base_node_name: Name of the node to base forecast on
            forecast_name: Name for the new forecast node
            config: Forecast configuration

        Returns:
            Name of the created forecast node

        Raises:
            ForecastNodeError: If base node not found or forecast node creation fails
        """
        if base_node_name not in self.fsg.nodes:
            raise ForecastNodeError(
                f"Node {base_node_name} not found in graph",
                node_id=base_node_name,
                available_nodes=list(self.fsg.nodes.keys()),
            )

        base_node = self.fsg.nodes[base_node_name]

        # Create forecast node
        try:
            forecast_node = NodeFactory.create_forecast_node(  # type: ignore[call-arg]
                name=forecast_name,
                base_node=base_node,
                forecast_config=config,
            )
            self.fsg.add_node(forecast_node)
            return forecast_name
        except Exception as e:
            raise ForecastNodeError(
                f"Could not create temporary forecast node: {e}",
                node_id=forecast_name,
                reason=str(e),
            ) from e
