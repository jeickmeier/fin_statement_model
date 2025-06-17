"""User-facing forecasting façade.

This module defines the StatementForecaster class, which provides a high-level API for performing forecasting operations on a FinancialStatementGraph. It exposes mutating and non-mutating forecast methods, delegating the core logic to helper modules. This controller is the main entry point for users who want to generate, retrieve, or batch forecast values for financial statement nodes.

Example:
    >>> from fin_statement_model.forecasting import StatementForecaster
    >>> forecaster = StatementForecaster(graph)
    >>> # Mutating forecast (modifies the graph)
    >>> forecaster.create_forecast(
    ...     forecast_periods=["2024", "2025"],
    ...     node_configs={
    ...         "revenue": {"method": "simple", "config": 0.05},
    ...         "costs": {"method": "curve", "config": [0.03, 0.04]},
    ...     },
    ... )
    >>> # Non-mutating forecast (returns values)
    >>> values = forecaster.forecast_value(
    ...     "revenue", ["2024", "2025"], forecast_config={"method": "simple", "config": 0.05}
    ... )
    >>> assert isinstance(values, dict)
"""

from __future__ import annotations

from typing import Any, Optional
import logging


from fin_statement_model.config import cfg
from fin_statement_model.core.nodes import Node
from fin_statement_model.forecasting.errors import ForecastNodeError
from fin_statement_model.forecasting.period_manager import PeriodManager
from fin_statement_model.forecasting.validators import ForecastValidator
from fin_statement_model.forecasting.types import ForecastResult

from .node_forecast import (
    _forecast_node_mutating,  # internal helper
    forecast_node_non_mutating,
)
from .batch import batch_forecast_values

logger = logging.getLogger(__name__)


class StatementForecaster:
    """Coordinate forecasting operations on a FinancialStatementGraph.

    This controller provides three high-level entry points:

    1. ``create_forecast`` – Mutates the graph and adds forecast values.
    2. ``forecast_value`` – Returns forecast values for a node without mutating the graph.
    3. ``forecast_multiple`` – Returns forecast results for multiple nodes in a batch.

    Args:
        fsg: The FinancialStatementGraph instance to operate on.

    Example:
        >>> from fin_statement_model.forecasting import StatementForecaster
        >>> forecaster = StatementForecaster(graph)
        >>> # Mutating forecast
        >>> forecaster.create_forecast(
        ...     forecast_periods=["2024", "2025"],
        ...     node_configs={"revenue": {"method": "simple", "config": 0.05}}
        ... )
        >>> # Non-mutating forecast
        >>> values = forecaster.forecast_value("revenue", ["2024", "2025"])
        >>> assert isinstance(values, dict)
    """

    def __init__(self, fsg: Any) -> None:
        """Initialize the StatementForecaster.

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
        """Add forecast data to the underlying graph (in-place).

        This method mutates the graph by adding new forecast periods and updating node values.
        It is suitable for scenarios where you want to persist forecast results.

        Args:
            forecast_periods: List of future periods to forecast (e.g., ["2024", "2025"]).
            node_configs: Mapping of node names to their forecast configurations.
                Each config should contain:
                    - 'method': Forecasting method (e.g., 'simple', 'curve').
                    - 'config': Method-specific parameters (e.g., growth rate).
            historical_periods: Optional list of historical periods to use as base.
            **kwargs: Additional arguments (e.g., add_missing_periods: bool).

        Returns:
            None. The graph is modified in-place.

        Raises:
            ForecastNodeError: If a node is not found or configuration is invalid.

        Example:
            >>> from fin_statement_model.forecasting import StatementForecaster
            >>> forecaster = StatementForecaster(graph)
            >>> forecaster.create_forecast(
            ...     forecast_periods=["2024"],
            ...     node_configs={"revenue": {"method": "simple", "config": 0.05}}
            ... )
        """
        logger.info("Creating forecast for periods %s", forecast_periods)
        historical_periods = PeriodManager.infer_historical_periods(
            self.fsg, forecast_periods, historical_periods
        )
        ForecastValidator.validate_forecast_inputs(
            historical_periods, forecast_periods, node_configs
        )
        add_missing = kwargs.get(
            "add_missing_periods", cfg("forecasting.add_missing_periods")
        )
        PeriodManager.ensure_periods_exist(
            self.fsg, forecast_periods, add_missing=add_missing
        )
        node_configs = node_configs or {}
        for node_name, raw_config in node_configs.items():
            node: Node | None = self.fsg.get_node(node_name)
            if node is None:
                raise ForecastNodeError(
                    f"Node {node_name} not found in graph",
                    node_id=node_name,
                    available_nodes=list(self.fsg.nodes.keys()),
                )
            forecast_config = ForecastValidator.validate_forecast_config(raw_config)
            ForecastValidator.validate_node_for_forecast(node, forecast_config.method)
            _forecast_node_mutating(
                node=node,
                historical_periods=historical_periods,
                forecast_periods=forecast_periods,
                forecast_config=forecast_config,
                **kwargs,
            )

    def forecast_value(
        self,
        node_name: str,
        forecast_periods: list[str],
        base_period: Optional[str] = None,
        forecast_config: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> dict[str, float]:
        """Return forecast values for a single node without mutating the graph.

        This method is ideal for what-if analysis, scenario comparison, or retrieving
        forecast values without persisting them to the graph.

        Args:
            node_name: Name of the node to forecast (e.g., 'revenue').
            forecast_periods: List of future periods to forecast.
            base_period: Optional base period to use for forecasting.
            forecast_config: Optional forecast configuration dict.
            **kwargs: Additional arguments (e.g., bad_forecast_value, allow_negative_forecasts).

        Returns:
            Dictionary mapping forecast periods to their calculated values.
            Example: {"2024": 1050.0, "2025": 1102.5}

        Raises:
            ForecastNodeError: If the node is not found or configuration is invalid.

        Example:
            >>> from fin_statement_model.forecasting import StatementForecaster
            >>> forecaster = StatementForecaster(graph)
            >>> values = forecaster.forecast_value("revenue", ["2024", "2025"])
            >>> assert isinstance(values, dict)
        """
        return forecast_node_non_mutating(
            self.fsg,
            node_name=node_name,
            forecast_periods=forecast_periods,
            base_period=base_period,
            forecast_config=forecast_config,
            **kwargs,
        )

    def forecast_multiple(
        self,
        node_names: list[str],
        forecast_periods: list[str],
        forecast_configs: Optional[dict[str, dict[str, Any]]] = None,
        base_period: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, ForecastResult]:
        """Return forecast results for multiple nodes without mutating the graph.

        This method is a convenience wrapper for batch forecasting. It returns a dictionary
        mapping node names to ForecastResult objects, each containing forecasted values and metadata.

        Args:
            node_names: List of node names to forecast.
            forecast_periods: List of future periods to forecast.
            forecast_configs: Optional mapping of node names to their forecast configs.
            base_period: Optional base period to use for all nodes.
            **kwargs: Additional arguments (e.g., continue_on_error).

        Returns:
            Dictionary mapping node names to ForecastResult objects.

        Raises:
            ForecastNodeError: If a node is not found and continue_on_error is False.

        Example:
            >>> from fin_statement_model.forecasting import StatementForecaster
            >>> forecaster = StatementForecaster(graph)
            >>> results = forecaster.forecast_multiple(["revenue", "costs"], ["2024", "2025"])
            >>> assert "revenue" in results
            >>> assert hasattr(results["revenue"], "values")
        """
        return batch_forecast_values(
            fsg=self.fsg,
            node_names=node_names,
            forecast_periods=forecast_periods,
            forecast_configs=forecast_configs,
            base_period=base_period,
            **kwargs,
        )
