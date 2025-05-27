"""Forecasting operations dedicated to statement-level financial graphs."""

import logging
from typing import Any, Optional, Union
from collections.abc import Callable
import numpy as np

# Core imports
from fin_statement_model.core.nodes import Node
from fin_statement_model.core.node_factory import NodeFactory

logger = logging.getLogger(__name__)


class StatementForecaster:
    """Handles forecasting operations specifically for a FinancialStatementGraph."""

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

        Args:
            forecast_periods: List of future periods to forecast.
            node_configs: Mapping of node names to their forecast configurations.
            historical_periods: Optional list of historical periods to use as base.
            **kwargs: Additional arguments passed to the forecasting logic.

        Returns:
            None
        """
        logger.info(f"StatementForecaster: Creating forecast for periods {forecast_periods}")
        try:
            if historical_periods is None:
                if not self.fsg.periods or not forecast_periods:
                    raise ValueError(
                        "Cannot infer historical periods: missing graph or forecast periods."
                    )
                first_forecast = forecast_periods[0]
                try:
                    idx = self.fsg.periods.index(first_forecast)
                    historical_periods = self.fsg.periods[:idx]
                    logger.debug(f"Inferred historical periods: {historical_periods}")
                except ValueError:
                    historical_periods = list(self.fsg.periods)
                    logger.warning(
                        f"First forecast period {first_forecast} not found; using all periods."
                    )
            else:
                logger.debug(f"Using explicitly provided historical periods: {historical_periods}")

            if not historical_periods:
                raise ValueError("No historical periods found for forecasting")
            if not forecast_periods:
                raise ValueError("No forecast periods provided")

            # Ensure forecast periods exist in the graph
            existing_periods = set(self.fsg.periods)
            new_periods = []
            for period in forecast_periods:
                if period not in existing_periods:
                    new_periods.append(period)
                    # Correct the call: add_periods is on fsg (the graph), not manipulator
                    self.fsg.add_periods([period])
            if new_periods:
                logger.info(f"Added new periods to graph for forecasting: {new_periods}")

            if node_configs is None:
                node_configs = {}

            for node_name, config in node_configs.items():
                node = self.fsg.get_node(node_name)
                if node is None:
                    raise ValueError(f"Node {node_name} not found in graph")
                if not hasattr(node, "values") or not isinstance(node.values, dict):
                    logger.warning(
                        f"Skipping forecast for node {node_name}: not a value-storing node"
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
                    growth_config = 0.0
                else:
                    raise ValueError(f"Invalid forecasting method: {method}")

                self._forecast_node(
                    node, historical_periods, forecast_periods, growth_config, method
                )

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
        growth_config: Union[float, list[float], Callable[[], float]],
        method: str,
        **kwargs: dict[str, Any],
    ) -> None:
        """Calculate forecast values and update the original node.

        Args:
            node: The graph node to forecast.
            historical_periods: List of historical periods for base values.
            forecast_periods: List of periods for which to calculate forecasts.
            growth_config: Growth parameter(s) (rate, list, or generator).
            method: Forecasting method name.
            **kwargs: Additional arguments passed to growth logic.

        Returns:
            None
        """
        logger.debug(f"StatementForecaster: Forecasting node {node.name} using method {method}")
        if not historical_periods:
            raise ValueError(f"No historical periods for node {node.name}")

        # Determine base period (last available historical period for the node)
        base_period = None
        if hasattr(node, "values") and isinstance(node.values, dict):
            available_historical = sorted(
                [p for p in node.values if p in historical_periods], reverse=True
            )
            if available_historical:
                base_period = available_historical[0]

        # Fallback or if node has no values dict
        if base_period is None:
            base_period = historical_periods[-1]  # Use last provided historical period
            logger.info(
                f"Using {base_period} as base period for {node.name} (node might lack values or specific history)"
            )

        # --- Keep logic to determine forecast_type and growth_params ---
        method_map = {
            "simple": "fixed",
            "curve": "curve",
            "statistical": "statistical",
            "average": "average",
            "historical_growth": "historical_growth",
        }
        forecast_type = method_map.get(method)
        if forecast_type is None:
            raise ValueError(f"Invalid forecasting method: {method}")

        growth_params: Any  # Define type more precisely if possible
        if method == "simple":
            growth_params = float(growth_config)
        elif method == "curve":
            if not isinstance(growth_config, list) or len(growth_config) != len(forecast_periods):
                raise ValueError("Curve growth list length mismatch")
            growth_params = [float(x) for x in growth_config]
        elif method == "statistical":
            if not isinstance(growth_config, dict) or "distribution" not in growth_config:
                raise ValueError(
                    f"Statistical method requires distribution parameters for {node.name}"
                )
            distr = growth_config["distribution"]
            params = growth_config["params"]

            def gen() -> float:
                if distr == "normal":
                    return np.random.normal(params["mean"], params["std"])
                elif distr == "uniform":
                    return np.random.uniform(params["low"], params["high"])
                else:
                    raise ValueError(f"Unsupported distribution: {distr}")

            growth_params = gen
        elif method == "average":
            if not hasattr(node, "calculate") or not callable(node.calculate):
                raise ValueError(f"Node {node.name} cannot be calculated for average method.")
            hist_vals = [
                node.calculate(p)
                for p in historical_periods
                if hasattr(node, "values") and p in node.values
            ]
            valid = [v for v in hist_vals if v is not None and not np.isnan(v)]
            if not valid:
                raise ValueError(f"No valid historical data to compute average for {node.name}")
            # For 'average' forecast node type, growth_params is not directly used by factory
            # The node itself calculates the average. Set growth_params=None.
            growth_params = None
        elif method == "historical_growth":
            # For 'historical_growth' forecast node type, growth_params is not directly used by factory
            # The node itself calculates the average growth. Set growth_params=None.
            growth_params = None
        else:
            growth_params = growth_config  # Pass through for potential custom types
        # --- End logic for forecast_type and growth_params ---

        # --- START RESTORED LOGIC ---
        # Create a temporary node to perform calculations
        tmp_node = NodeFactory.create_forecast_node(
            name=f"{node.name}_forecast_temp",
            base_node=node,
            base_period=base_period,
            forecast_periods=forecast_periods,
            forecast_type=forecast_type,
            growth_params=growth_params,
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

        # --- END RESTORED LOGIC ---

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

        Args:
            node_name: Name of the node to forecast.
            forecast_periods: List of future periods to forecast.
            base_period: Optional base period to use for forecasting. If omitted, inferred from graph.
            forecast_config: Forecast configuration dict mapping 'method' and 'config'.
            **kwargs: Additional arguments passed to the internal forecasting logic.

        Returns:
            A mapping from forecast period to its forecasted float value.
        """
        # Locate the node
        node = self.fsg.get_node(node_name)
        if node is None:
            raise ValueError(f"Node {node_name} not found in graph")

        # Determine historical periods list
        if base_period:
            historical_periods = [base_period]
        # Try custom getter, otherwise infer
        elif hasattr(self.fsg, "get_historical_periods") and callable(
            getattr(self.fsg, "get_historical_periods")
        ):
            historical_periods = self.fsg.get_historical_periods()
        else:
            if not self.fsg.periods or not forecast_periods:
                raise ValueError(
                    "Cannot infer historical periods: graph or forecast periods missing"
                )
            first = forecast_periods[0]
            try:
                idx = self.fsg.periods.index(first)
                historical_periods = self.fsg.periods[:idx]
            except ValueError:
                historical_periods = list(self.fsg.periods)

        if not historical_periods:
            raise ValueError("No historical periods found for forecasting")
        if not forecast_periods:
            raise ValueError("No forecast periods provided")

        # --- Note: Do NOT add forecast periods to the main graph here ---
        # for period in forecast_periods:
        #     if period not in self.fsg.periods:
        #         self.fsg.add_periods([period]) # Don't modify graph state

        config = forecast_config or {}
        method = config.get("method", "simple")
        growth_cfg = config.get("config")
        # Normalize configuration parameters
        if method == "simple" and isinstance(growth_cfg, list):
            growth_cfg = growth_cfg[0]
        elif method == "curve" and not isinstance(growth_cfg, list):
            growth_cfg = [growth_cfg] * len(forecast_periods)
        elif method == "statistical":
            if not isinstance(growth_cfg, dict) or "distribution" not in growth_cfg:
                raise ValueError(f"Statistical forecast requires distribution for {node_name}")
        elif method in {"average", "historical_growth"}:
            growth_cfg = 0.0  # Will be handled by forecast node type
        else:
            # Leave other methods as-is
            pass

        # --- START Non-Mutating Calculation Logic ---
        # Determine base period (ensure logic matches _forecast_node)
        calc_base_period = None
        if hasattr(node, "values") and isinstance(node.values, dict):
            available_historical = sorted(
                [p for p in node.values if p in historical_periods], reverse=True
            )
            if available_historical:
                calc_base_period = available_historical[0]
        if calc_base_period is None:
            calc_base_period = historical_periods[-1]

        # Prepare forecast_type and growth_params (reuse logic from _forecast_node)
        method_map = {
            "simple": "fixed",
            "curve": "curve",
            "statistical": "statistical",
            "average": "average",
            "historical_growth": "historical_growth",
        }
        forecast_type = method_map.get(method)
        if forecast_type is None:
            raise ValueError(f"Invalid method: {method}")

        growth_params: Any = None  # Default
        if method == "simple":
            growth_params = float(growth_cfg)
        elif method == "curve":
            if not isinstance(growth_cfg, list) or len(growth_cfg) != len(forecast_periods):
                raise ValueError("Curve growth list length mismatch")
            growth_params = [float(x) for x in growth_cfg]
        elif method == "statistical":
            # Simplified - assume growth_cfg has needed keys
            if not isinstance(growth_cfg, dict):
                raise ValueError("Invalid config for statistical method")
            distr = growth_cfg.get("distribution")
            params = growth_cfg.get("params")
            if not distr or not params:
                raise ValueError("Missing distribution or params for statistical")

            def gen() -> float:
                if distr == "normal":
                    return np.random.normal(params["mean"], params["std"])
                elif distr == "uniform":
                    return np.random.uniform(params["low"], params["high"])
                else:
                    raise ValueError(f"Unsupported distribution: {distr}")

            growth_params = gen
        elif method in {"average", "historical_growth"}:
            growth_params = None
        else:
            growth_params = growth_cfg

        # Create a temporary forecast node (DO NOT add to graph)
        try:
            temp_forecast_node = NodeFactory.create_forecast_node(
                name=f"{node_name}_temp_forecast",  # Temporary name
                base_node=node,  # Use the actual node from graph as base
                base_period=calc_base_period,
                forecast_periods=forecast_periods,
                forecast_type=forecast_type,
                growth_params=growth_params,
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

        return results
        # --- END Non-Mutating Calculation Logic ---
