"""Helpers for single-node forecasting operations.

This module provides functions for forecasting the values of a single node in a financial statement graph.
It includes both mutating (in-place) and non-mutating (pure) forecast operations, as well as internal
utilities for value clamping and error handling.

Example:
    >>> from fin_statement_model.forecasting.forecaster.node_forecast import forecast_node_non_mutating
    >>> values = forecast_node_non_mutating(fsg, node_name="revenue", forecast_periods=["2024", "2025"])
    >>> assert isinstance(values, dict)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

import numpy as np

from fin_statement_model.config import cfg
from fin_statement_model.core.node_factory import NodeFactory
from fin_statement_model.forecasting.errors import ForecastNodeError
from fin_statement_model.forecasting.period_manager import PeriodManager
from fin_statement_model.forecasting.strategies import get_forecast_method
from fin_statement_model.forecasting.validators import ForecastValidator

if TYPE_CHECKING:
    from fin_statement_model.core.nodes import Node
    from fin_statement_model.forecasting.types import ForecastConfig

# Bring BaseForecastMethod into the runtime namespace so that external callers
# (and the test-suite) can safely monkey-patch it.  Import placed below the
# TYPE_CHECKING block to avoid unnecessary overhead during static analysis.
from fin_statement_model.forecasting.methods.base import (
    BaseForecastMethod,  # pylint: disable=wrong-import-position
)

logger = logging.getLogger(__name__)

__all__ = [
    "BaseForecastMethod",
    "_forecast_node_mutating",
    "forecast_node_non_mutating",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _calc_bad_value(**kwargs: Any) -> float:
    """Get the fallback value for bad forecasts (NaN/Inf/errors).

    Args:
        **kwargs: May include 'bad_forecast_value'.

    Returns:
        The fallback value as a float.
    """
    return float(kwargs.get("bad_forecast_value", cfg("forecasting.default_bad_forecast_value")))


def _clamp(value: float, allow_negative: bool, bad_value: float) -> float:
    """Clamp a forecast value to avoid NaN/Inf and optionally disallow negatives.

    Args:
        value: The forecast value to check.
        allow_negative: If False, negative values are replaced with bad_value.
        bad_value: The fallback value for NaN/Inf/negatives.

    Returns:
        The clamped value.
    """
    if np.isnan(value) or np.isinf(value):
        return bad_value
    if not allow_negative and value < 0:
        return bad_value
    return value


# ---------------------------------------------------------------------------
# Mutating forecast (updates original node)
# ---------------------------------------------------------------------------


def _forecast_node_mutating(
    *,
    node: Node,
    historical_periods: list[str],
    forecast_periods: list[str],
    forecast_config: ForecastConfig,
    **kwargs: Any,
) -> None:
    """Compute forecast values and write them into ``node.values`` in-place.

    This function mutates the node by updating its values for the forecast periods.
    It is used by StatementForecaster.create_forecast.

    Args:
        node: The node to forecast (must have a 'values' dict).
        historical_periods: List of historical periods for base values.
        forecast_periods: List of periods to forecast.
        forecast_config: Validated forecast configuration.
        **kwargs: Additional arguments (e.g., bad_forecast_value, allow_negative_forecasts).

    Returns:
        None. The node is modified in-place.

    Raises:
        ForecastNodeError: If the node is missing required attributes.

    Example:
        >>> _forecast_node_mutating(node, ["2022"], ["2023"], forecast_config, bad_forecast_value=0.0)
    """
    base_period = PeriodManager.determine_base_period(node, historical_periods)

    method = get_forecast_method(forecast_config.method)
    base_method = cast("BaseForecastMethod", method)
    params = base_method.get_forecast_params(forecast_config.config, forecast_periods)

    tmp_node = NodeFactory.create_forecast_node(
        name=f"{node.name}_forecast_temp",
        base_node=node,
        base_period=base_period,
        forecast_periods=forecast_periods,
        forecast_type=params["forecast_type"],
        growth_params=params["growth_params"],
    )

    if not hasattr(node, "values") or not isinstance(node.values, dict):
        logger.error("Node %s lacks a 'values' dict - cannot store forecast", node.name)
        raise ForecastNodeError(f"Node {node.name} lacks a 'values' dictionary.", node_id=node.name)

    bad_value = _calc_bad_value(**kwargs)
    allow_neg = kwargs.get("allow_negative_forecasts", cfg("forecasting.allow_negative_forecasts"))

    for period in forecast_periods:
        try:
            raw_val = tmp_node.calculate(period)
            val = _clamp(raw_val, allow_neg, bad_value)
        except (ForecastNodeError, ValueError, ArithmeticError):
            logger.exception("Error forecasting %s@%s", node.name, period)
            val = bad_value
        node.values[period] = float(val)

    if hasattr(node, "clear_cache") and callable(node.clear_cache):
        node.clear_cache()


# ---------------------------------------------------------------------------
# Non-mutating forecast (returns dict)
# ---------------------------------------------------------------------------


def forecast_node_non_mutating(
    fsg: Any,  # FinancialStatementGraph - kept generic to avoid circular import
    *,
    node_name: str,
    forecast_periods: list[str],
    base_period: str | None = None,
    forecast_config: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, float]:
    """Return forecast values for a single node without mutating the graph.

    This function is pure and does not modify the graph or node state. It is suitable for
    what-if analysis, scenario comparison, or retrieving forecast values for reporting.

    Args:
        fsg: The FinancialStatementGraph instance.
        node_name: Name of the node to forecast.
        forecast_periods: List of periods to forecast.
        base_period: Optional base period to use for forecasting.
        forecast_config: Optional forecast configuration dict.
        **kwargs: Additional arguments (e.g., bad_forecast_value, allow_negative_forecasts).

    Returns:
        Dictionary mapping forecast periods to their calculated values.

    Raises:
        ForecastNodeError: If the node is not found or configuration is invalid.

    Example:
        >>> values = forecast_node_non_mutating(fsg, node_name="revenue", forecast_periods=["2024"])
        >>> assert isinstance(values, dict)
    """
    node = fsg.get_node(node_name)
    if node is None:
        raise ForecastNodeError(
            f"Node {node_name} not found in graph",
            node_id=node_name,
            available_nodes=list(fsg.nodes.keys()),
        )

    # Determine historical periods ------------------------------------------------
    historical_periods = [base_period] if base_period else PeriodManager.infer_historical_periods(fsg, forecast_periods)

    ForecastValidator.validate_forecast_inputs(historical_periods, forecast_periods)

    if forecast_config is None:
        default_method = cfg("forecasting.default_method")
        forecast_config = {
            "method": default_method,
            "config": (cfg("forecasting.default_growth_rate") if default_method == "simple" else {}),
        }

    validated_config = ForecastValidator.validate_forecast_config(forecast_config)
    ForecastValidator.validate_node_for_forecast(node, validated_config.method)

    calc_base_period = PeriodManager.determine_base_period(node, historical_periods, base_period)

    method = get_forecast_method(validated_config.method)
    base_method = cast("BaseForecastMethod", method)
    params = base_method.get_forecast_params(validated_config.config, forecast_periods)

    try:
        temp_node = NodeFactory.create_forecast_node(
            name=f"{node_name}_temp_forecast",
            base_node=node,
            base_period=calc_base_period,
            forecast_periods=forecast_periods,
            forecast_type=params["forecast_type"],
            growth_params=params["growth_params"],
        )
    except Exception as exc:
        logger.exception("Failed to create temp forecast node for %s", node_name)
        raise ForecastNodeError(
            "Could not create temporary forecast node",
            node_id=node_name,
            reason=str(exc),
        ) from exc

    bad_value = _calc_bad_value(**kwargs)
    allow_neg = kwargs.get("allow_negative_forecasts", cfg("forecasting.allow_negative_forecasts"))

    results: dict[str, float] = {}
    for period in forecast_periods:
        try:
            val = temp_node.calculate(period)
            val = _clamp(val, allow_neg, bad_value)
        except (ForecastNodeError, ValueError, ArithmeticError) as exc:
            logger.warning("Error calculating forecast for %s@%s: %s", node_name, period, exc)
            val = bad_value
        results[period] = float(val)

    ForecastValidator.validate_forecast_result(results, forecast_periods, node_name)
    return results
