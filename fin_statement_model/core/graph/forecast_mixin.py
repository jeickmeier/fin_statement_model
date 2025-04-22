"""Mixin providing forecasting methods for FinancialStatementGraph.

- create_forecast
- _forecast_node.
"""

from __future__ import annotations

import logging
import numpy as np
from typing import Any, Optional, Union, Callable

# Make sure FinancialStatementItemNode is importable if needed for type checking
from fin_statement_model.core.nodes import Node

# from ..nodes import FinancialStatementItemNode # If specific type check needed
from fin_statement_model.core.node_factory import NodeFactory

logger = logging.getLogger(__name__)


class ForecastOperationsMixin:
    """Graph mixin providing forecasting operations."""

    def create_forecast(
        self,
        forecast_periods: list[str],
        node_configs: Optional[dict[str, dict[str, Any]]] = None,
        historical_periods: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Create forecasts for financial statement items on the graph.

        Args:
            forecast_periods: List of future periods to forecast
            node_configs: Dictionary mapping node names to their forecast configurations.
                         Each configuration should be a dictionary with:
                         - 'method': The forecasting method ('simple', 'curve', 'statistical', 'average', 'historical_growth')
                         - 'config': The configuration specific to the method:
                           - For 'simple': float growth rate
                           - For 'curve': list of growth rates for each period
                           - For 'statistical': dict with 'distribution' and 'params'
                           - For 'average' or 'historical_growth': None
            historical_periods: Optional list of historical periods to use as base
            **kwargs: Additional arguments passed to _forecast_node

        Example:
            fsg.create_forecast(
                forecast_periods=["FY2023", "FY2024", "FY2025"],
                node_configs={
                    "revenue_americas": {
                        "method": "curve",
                        "config": [0.05, 0.06, 0.07]
                    },
                    "revenue_europe": {
                        "method": "statistical",
                        "config": {
                            "distribution": "normal",
                            "params": {"mean": 0.05, "std": 0.02}
                        }
                    },
                    "revenue_apac": {
                        "method": "historical_growth",
                        "config": None
                    }
                }
            )
        """
        try:
            if historical_periods is None:
                # Try to get historical periods from the instance first
                if hasattr(self, "get_historical_periods") and callable(
                    getattr(self, "get_historical_periods")
                ):
                    historical_periods = self.get_historical_periods()
                    logger.debug(
                        f"Using historical periods from get_historical_periods: {historical_periods}"
                    )
                else:
                    # Infer historical periods if the method doesn't exist
                    if not self.periods or not forecast_periods:
                        raise ValueError(
                            "Cannot infer historical periods: graph periods or forecast periods are missing."
                        )
                    first_forecast_period = forecast_periods[0]
                    try:
                        first_forecast_index = self.periods.index(first_forecast_period)
                        historical_periods = self.periods[:first_forecast_index]
                        logger.debug(f"Inferred historical periods: {historical_periods}")
                    except ValueError:
                        # If the first forecast period isn't in the main list, assume all are historical
                        historical_periods = list(self.periods)
                        logger.warning(
                            f"First forecast period {first_forecast_period} not found in graph periods {self.periods}. Assuming all are historical."
                        )

            else:
                logger.debug(f"Using explicitly provided historical periods: {historical_periods}")

            if not historical_periods:
                raise ValueError("No historical periods found for forecasting")

            if not forecast_periods:
                raise ValueError("No forecast periods provided")

            for period in forecast_periods:
                if period not in self.periods:
                    self.add_periods([period])
                    logger.debug(f"Added forecast period to graph: {period}")

            if node_configs is None:
                node_configs = {}

            for node_name, config in node_configs.items():
                node = self.get_node(node_name)
                if node is None:
                    raise ValueError(f"Node {node_name} not found in graph")

                # Ensure we are trying to forecast a node that can store values
                # Typically FinancialStatementItemNode
                if not hasattr(node, "values") or not isinstance(node.values, dict):
                    logger.warning(
                        f"Skipping forecast for node {node_name}: Not a compatible value-storing node (e.g., FinancialStatementItemNode). Type is {type(node).__name__}"
                    )
                    continue

                method = config.get("method", "simple")
                growth_config = config.get("config")

                if method == "simple":
                    if isinstance(growth_config, list):
                        growth_config = growth_config[0]
                elif method == "curve":
                    if not isinstance(growth_config, list):
                        growth_config = [growth_config] * len(forecast_periods)
                elif method == "statistical":
                    if not isinstance(growth_config, dict) or "distribution" not in growth_config:
                        raise ValueError(
                            f"Statistical method requires distribution parameters for {node_name}"
                        )
                elif method in {"average", "historical_growth"}:
                    growth_config = 0.0  # Placeholder, calculated in _forecast_node
                else:
                    raise ValueError(f"Invalid forecasting method: {method}")

                self._forecast_node(
                    node, historical_periods, forecast_periods, growth_config, method
                )

            # Recalculate the graph after forecasting
            # This now relies on the original nodes having updated values
            self.recalculate_all()

            logger.info(
                f"Created forecast for {len(forecast_periods)} periods using {len(node_configs)} nodes"
            )

        except Exception as e:
            logger.error(
                f"Error creating forecast: {e}", exc_info=True
            )  # Add exc_info for better debugging
            raise

    def _forecast_node(
        self,
        node: Node,  # Hint with base Node, but expect FinancialStatementItemNode usually
        historical_periods: list[str],
        forecast_periods: list[str],
        growth_config: Union[float, list[float], Callable[[], float]],
        method: str,
        **kwargs: dict[str, Any],
    ) -> None:
        """Calculate forecast values and update the original node."""
        if not historical_periods:
            raise ValueError(f"No historical periods available for forecasting node {node.name}")

        # Determine base historical period
        base_period = historical_periods[-1]

        # Ensure the node has a 'values' dict and the base period exists
        if not hasattr(node, "values") or not isinstance(node.values, dict):
            logger.error(f"Cannot forecast node {node.name}: Does not have a 'values' dictionary.")
            return  # Or raise error

        if base_period not in node.values:
            logger.warning(
                f"Base period {base_period} not found in node {node.name} values. Available periods: {sorted(node.values.keys())}"
            )
            # Attempt to find the latest available historical period
            available_historical = sorted(
                [p for p in node.values if p in historical_periods], reverse=True
            )
            if available_historical:
                base_period = available_historical[0]
                logger.info(f"Using {base_period} as base period instead for node {node.name}")
            else:
                raise ValueError(
                    f"No valid historical base period found in node {node.name}'s values."
                )

        # Prepare transformation to forecast
        method_to_type = {
            "simple": "fixed",
            "curve": "curve",
            "statistical": "statistical",
            "average": "average",
            "historical_growth": "historical_growth",
        }
        forecast_type = method_to_type.get(method)
        if forecast_type is None:
            raise ValueError(f"Invalid forecasting method: {method}")

        # Determine growth parameters
        growth_params = None
        if method == "simple":
            growth_params = float(growth_config)
        elif method == "curve":
            if not isinstance(growth_config, list) or len(growth_config) != len(forecast_periods):
                raise ValueError(
                    f"Growth rates list for {node.name} ({len(growth_config)}) must match number of forecast periods ({len(forecast_periods)})"
                )
            growth_params = [float(rate) for rate in growth_config]
        elif method == "statistical":
            distribution = growth_config["distribution"]
            params = growth_config["params"]

            def gen() -> float:  # Define generator within scope
                if distribution == "normal":
                    return np.random.normal(params["mean"], params["std"])
                elif distribution == "uniform":
                    return np.random.uniform(params["low"], params["high"])
                else:
                    raise ValueError(f"Unsupported distribution: {distribution}")

            growth_params = gen  # Assign the generator function
        elif method == "average":
            historical_values = [node.calculate(p) for p in historical_periods if p in node.values]
            valid = [v for v in historical_values if v is not None and not np.isnan(v)]
            if not valid:
                raise ValueError(f"No valid historical data to compute average for {node.name}")
            growth_params = sum(valid) / len(valid)
        elif method == "historical_growth":
            # Calculation for historical growth needs base_node and historical_periods
            # This might be better handled inside the specific ForecastNode implementation
            # For now, pass None or a placeholder if the factory/node handles it.
            growth_params = None  # Factory/Node should calculate this
        else:
            # This case should be caught by method_to_type check earlier
            raise ValueError(f"Unhandled forecasting method: {method}")

        # 1. Create a TEMPORARY forecast node instance to calculate values
        try:
            temp_forecast_node = NodeFactory.create_forecast_node(
                name=f"{node.name}_forecast_temp",  # Temporary name
                base_node=node,  # Pass the original node
                base_period=base_period,
                forecast_periods=forecast_periods,
                forecast_type=forecast_type,
                growth_params=growth_params,
            )
        except Exception as e:
            logger.error(
                f"Failed to create temporary forecast node for {node.name}: {e}",
                exc_info=True,
            )
            raise  # Re-raise the error from the factory

        # 2. Calculate the forecast values using the temporary node
        forecast_values: dict[str, float] = {}
        for period in forecast_periods:
            try:
                # Assuming ForecastNode subclasses implement calculate
                value = temp_forecast_node.calculate(period)
                # Handle potential NaN or Inf values from calculations
                if np.isnan(value) or np.isinf(value):
                    logger.warning(
                        f"Forecast for {node.name} period {period} resulted in {value}. Replacing with 0.0."
                    )
                    value = 0.0
                forecast_values[period] = value
            except Exception as e:
                logger.error(
                    f"Error calculating forecast for {node.name} period {period}: {e}",
                    exc_info=True,
                )
                forecast_values[period] = 0.0  # Default to 0 on error

        # 3. Update the ORIGINAL node's values dictionary
        # We already checked hasattr(node, 'values') and isinstance(node.values, dict) above
        original_node_values = node.values
        updated_count = 0
        for period, value in forecast_values.items():
            if period in forecast_periods:  # Ensure we only update forecast periods
                original_node_values[period] = value
                updated_count += 1

        logger.debug(f"Updated {updated_count} forecast values in original node {node.name}")

        # Clear the original node's cache AFTER updating its values
        if hasattr(node, "clear_cache"):
            node.clear_cache()

        # DO NOT REPLACE THE NODE ANYMORE
        # self.replace_node(node.name, forecast_node)
        # logger.debug(f"Forecast applied to node {node.name}")

    def forecast_value(
        self,
        node_name: str,
        forecast_periods: list[str],
        base_period: str | None = None,
        forecast_config: Optional[dict] = None,
        **kwargs: dict[str, Any],
    ) -> dict[str, float]:
        """Forecasts the value of a node for specified future periods.

        Args:
            node_name: The name of the node to forecast
            forecast_periods: List of future periods to forecast
            base_period: The base period to use for forecasting
            forecast_config: The configuration for forecasting
            **kwargs: Additional arguments passed to _forecast_node

        Returns:
            A dictionary mapping forecast periods to their forecast values
        """
        node = self.get_node(node_name)
        if node is None:
            raise ValueError(f"Node {node_name} not found in graph")

        # Ensure we are trying to forecast a node that can store values
        # Typically FinancialStatementItemNode
        if not hasattr(node, "values") or not isinstance(node.values, dict):
            logger.warning(
                f"Skipping forecast for node {node_name}: Not a compatible value-storing node (e.g., FinancialStatementItemNode). Type is {type(node).__name__}"
            )
            return {}

        if base_period is None:
            # Try to get historical periods from the instance first
            if hasattr(self, "get_historical_periods") and callable(
                getattr(self, "get_historical_periods")
            ):
                historical_periods = self.get_historical_periods()
                logger.debug(
                    f"Using historical periods from get_historical_periods: {historical_periods}"
                )
            else:
                # Infer historical periods if the method doesn't exist
                if not self.periods or not forecast_periods:
                    raise ValueError(
                        "Cannot infer historical periods: graph periods or forecast periods are missing."
                    )
                first_forecast_period = forecast_periods[0]
                try:
                    first_forecast_index = self.periods.index(first_forecast_period)
                    historical_periods = self.periods[:first_forecast_index]
                    logger.debug(f"Inferred historical periods: {historical_periods}")
                except ValueError:
                    # If the first forecast period isn't in the main list, assume all are historical
                    historical_periods = list(self.periods)
                    logger.warning(
                        f"First forecast period {first_forecast_period} not found in graph periods {self.periods}. Assuming all are historical."
                    )

        else:
            logger.debug(f"Using explicitly provided historical period: {base_period}")
            historical_periods = [base_period]

        if not historical_periods:
            raise ValueError("No historical periods found for forecasting")

        if not forecast_periods:
            raise ValueError("No forecast periods provided")

        for period in forecast_periods:
            if period not in self.periods:
                self.add_periods([period])
                logger.debug(f"Added forecast period to graph: {period}")

        if forecast_config is None:
            forecast_config = {}

        method = forecast_config.get("method", "simple")
        growth_config = forecast_config.get("config")

        if method == "simple":
            if isinstance(growth_config, list):
                growth_config = growth_config[0]
        elif method == "curve":
            if not isinstance(growth_config, list):
                growth_config = [growth_config] * len(forecast_periods)
        elif method == "statistical":
            if not isinstance(growth_config, dict) or "distribution" not in growth_config:
                raise ValueError(
                    f"Statistical method requires distribution parameters for {node_name}"
                )
        elif method in {"average", "historical_growth"}:
            growth_config = 0.0  # Placeholder, calculated in _forecast_node
        else:
            raise ValueError(f"Invalid forecasting method: {method}")

        forecast_values = self._forecast_node(
            node, historical_periods, forecast_periods, growth_config, method
        )

        # Recalculate the graph after forecasting
        # This now relies on the original nodes having updated values
        self.recalculate_all()

        logger.info(
            f"Created forecast for {len(forecast_periods)} periods using {len(forecast_config)} config"
        )

        return forecast_values

    def _forecast_node(
        self,
        node: Node,  # Hint with base Node, but expect FinancialStatementItemNode usually
        historical_periods: list[str],
        forecast_periods: list[str],
        growth_config: Union[float, list[float], Callable[[], float]],
        method: str,
        **kwargs: dict[str, Any],
    ) -> dict[str, float]:
        """Recursive helper to calculate forecast values, handling dependencies."""
        if not historical_periods:
            raise ValueError(f"No historical periods available for forecasting node {node.name}")

        # Determine base historical period
        base_period = historical_periods[-1]

        # Ensure the node has a 'values' dict and the base period exists
        if not hasattr(node, "values") or not isinstance(node.values, dict):
            logger.error(f"Cannot forecast node {node.name}: Does not have a 'values' dictionary.")
            return {}

        if base_period not in node.values:
            logger.warning(
                f"Base period {base_period} not found in node {node.name} values. Available periods: {sorted(node.values.keys())}"
            )
            # Attempt to find the latest available historical period
            available_historical = sorted(
                [p for p in node.values if p in historical_periods], reverse=True
            )
            if available_historical:
                base_period = available_historical[0]
                logger.info(f"Using {base_period} as base period instead for node {node.name}")
            else:
                raise ValueError(
                    f"No valid historical base period found in node {node.name}'s values."
                )

        # Prepare transformation to forecast
        method_to_type = {
            "simple": "fixed",
            "curve": "curve",
            "statistical": "statistical",
            "average": "average",
            "historical_growth": "historical_growth",
        }
        forecast_type = method_to_type.get(method)
        if forecast_type is None:
            raise ValueError(f"Invalid forecasting method: {method}")

        # Determine growth parameters
        growth_params = None
        if method == "simple":
            growth_params = float(growth_config)
        elif method == "curve":
            if not isinstance(growth_config, list) or len(growth_config) != len(forecast_periods):
                raise ValueError(
                    f"Growth rates list for {node.name} ({len(growth_config)}) must match number of forecast periods ({len(forecast_periods)})"
                )
            growth_params = [float(rate) for rate in growth_config]
        elif method == "statistical":
            distribution = growth_config["distribution"]
            params = growth_config["params"]

            def gen() -> float:  # Define generator within scope
                if distribution == "normal":
                    return np.random.normal(params["mean"], params["std"])
                elif distribution == "uniform":
                    return np.random.uniform(params["low"], params["high"])
                else:
                    raise ValueError(f"Unsupported distribution: {distribution}")

            growth_params = gen  # Assign the generator function
        elif method == "average":
            historical_values = [node.calculate(p) for p in historical_periods if p in node.values]
            valid = [v for v in historical_values if v is not None and not np.isnan(v)]
            if not valid:
                raise ValueError(f"No valid historical data to compute average for {node.name}")
            growth_params = sum(valid) / len(valid)
        elif method == "historical_growth":
            # Calculation for historical growth needs base_node and historical_periods
            # This might be better handled inside the specific ForecastNode implementation
            # For now, pass None or a placeholder if the factory/node handles it.
            growth_params = None  # Factory/Node should calculate this
        else:
            # This case should be caught by method_to_type check earlier
            raise ValueError(f"Unhandled forecasting method: {method}")

        # 1. Create a TEMPORARY forecast node instance to calculate values
        try:
            temp_forecast_node = NodeFactory.create_forecast_node(
                name=f"{node.name}_forecast_temp",  # Temporary name
                base_node=node,  # Pass the original node
                base_period=base_period,
                forecast_periods=forecast_periods,
                forecast_type=forecast_type,
                growth_params=growth_params,
            )
        except Exception as e:
            logger.error(
                f"Failed to create temporary forecast node for {node.name}: {e}",
                exc_info=True,
            )
            raise  # Re-raise the error from the factory

        # 2. Calculate the forecast values using the temporary node
        forecast_values: dict[str, float] = {}
        for period in forecast_periods:
            try:
                # Assuming ForecastNode subclasses implement calculate
                value = temp_forecast_node.calculate(period)
                # Handle potential NaN or Inf values from calculations
                if np.isnan(value) or np.isinf(value):
                    logger.warning(
                        f"Forecast for {node.name} period {period} resulted in {value}. Replacing with 0.0."
                    )
                    value = 0.0
                forecast_values[period] = value
            except Exception as e:
                logger.error(
                    f"Error calculating forecast for {node.name} period {period}: {e}",
                    exc_info=True,
                )
                forecast_values[period] = 0.0  # Default to 0 on error

        # 3. Update the ORIGINAL node's values dictionary
        # We already checked hasattr(node, 'values') and isinstance(node.values, dict) above
        original_node_values = node.values
        updated_count = 0
        for period, value in forecast_values.items():
            if period in forecast_periods:  # Ensure we only update forecast periods
                original_node_values[period] = value
                updated_count += 1

        logger.debug(f"Updated {updated_count} forecast values in original node {node.name}")

        # Clear the original node's cache AFTER updating its values
        if hasattr(node, "clear_cache"):
            node.clear_cache()

        # DO NOT REPLACE THE NODE ANYMORE
        # self.replace_node(node.name, forecast_node)
        # logger.debug(f"Forecast applied to node {node.name}")

        return forecast_values
