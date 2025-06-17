"""Helpers for multi-node / batch forecasting operations.

This module provides functions for forecasting multiple nodes in a financial statement graph
in a single batch operation. It is used by the StatementForecaster controller for non-mutating
batch forecasts.

Example:
    >>> from fin_statement_model.forecasting.forecaster.batch import batch_forecast_values
    >>> results = batch_forecast_values(
    ...     fsg, node_names=["revenue", "costs"], forecast_periods=["2024", "2025"]
    ... )
    >>> assert "revenue" in results
"""

from __future__ import annotations

from typing import Any, Optional
import logging

from fin_statement_model.config import cfg
from fin_statement_model.forecasting.errors import ForecastNodeError
from fin_statement_model.forecasting.types import ForecastResult
from fin_statement_model.forecasting.period_manager import PeriodManager
from fin_statement_model.forecasting.validators import ForecastValidator

from .node_forecast import forecast_node_non_mutating

logger = logging.getLogger(__name__)

__all__ = ["batch_forecast_values"]


def batch_forecast_values(
    *,
    fsg: Any,
    node_names: list[str],
    forecast_periods: list[str],
    forecast_configs: Optional[dict[str, dict[str, Any]]] = None,
    base_period: Optional[str] = None,
    **kwargs: Any,
) -> dict[str, ForecastResult]:
    """Forecast many nodes without mutating the graph (batch operation).

    This function returns a dictionary mapping node names to ForecastResult objects, each
    containing forecasted values and metadata. It is suitable for batch what-if analysis or
    scenario comparison.

    Args:
        fsg: The FinancialStatementGraph instance.
        node_names: List of node names to forecast.
        forecast_periods: List of periods to forecast.
        forecast_configs: Optional mapping of node names to their forecast configs.
        base_period: Optional base period to use for all nodes.
        **kwargs: Additional arguments (e.g., continue_on_error).

    Returns:
        Dictionary mapping node names to ForecastResult objects.

    Raises:
        ForecastNodeError: If a node is not found and continue_on_error is False.

    Example:
        >>> results = batch_forecast_values(
        ...     fsg, node_names=["revenue"], forecast_periods=["2024"]
        ... )
        >>> assert "revenue" in results
    """

    continue_on_err: bool = kwargs.get(
        "continue_on_error", cfg("forecasting.continue_on_error")
    )

    results: dict[str, ForecastResult] = {}
    forecast_configs = forecast_configs or {}

    for node_name in node_names:
        raw_cfg = forecast_configs.get(node_name)
        try:
            values = forecast_node_non_mutating(
                fsg,
                node_name=node_name,
                forecast_periods=forecast_periods,
                base_period=base_period,
                forecast_config=raw_cfg,
                **kwargs,
            )

            node = fsg.get_node(node_name)
            historical_periods = PeriodManager.infer_historical_periods(
                fsg, forecast_periods
            )
            actual_base = PeriodManager.determine_base_period(
                node, historical_periods, base_period
            )

            validated_cfg = ForecastValidator.validate_forecast_config(
                raw_cfg
                or {
                    "method": cfg("forecasting.default_method"),
                    "config": cfg("forecasting.default_growth_rate"),
                }
            )

            results[node_name] = ForecastResult(
                node_name=node_name,
                periods=forecast_periods,
                values=values,
                method=validated_cfg.method,
                base_period=actual_base,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error forecasting node %s", node_name)
            if continue_on_err:
                continue
            raise ForecastNodeError(
                f"Error forecasting node {node_name}: {exc}",
                node_id=node_name,
                reason=str(exc),
            ) from exc

    return results
