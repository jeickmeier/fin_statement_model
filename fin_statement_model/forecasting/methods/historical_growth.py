"""Forecast future values based on average historical growth patterns.

This method calculates future values by determining the average historical
growth rate and applying it to the base value for forecast periods.

Configuration:
    - Not required (pass None or 0)
    - Automatically calculates growth from historical data based on minimum periods configured

Example:
    >>> method = HistoricalGrowthForecastMethod()
    >>> params = method.get_forecast_params(None, ["2024", "2025"])
    >>> # Returns: {"forecast_type": "historical_growth", "growth_params": None}
"""

import logging
from typing import Any, Optional

import numpy as np

from fin_statement_model.config.helpers import cfg
from fin_statement_model.core.nodes import Node

from .base import BaseForecastMethod

logger = logging.getLogger(__name__)


class HistoricalGrowthForecastMethod(BaseForecastMethod):
    """Forecast future values based on average historical growth patterns.

    This method calculates the average historical growth rate and applies it to
    forecast future values. Useful when past growth patterns are expected to
    continue.

    Configuration:
        - Not required (pass None or 0)
        - Automatically calculates growth from historical data requiring at least
          cfg("forecasting.min_historical_periods") data points

    Example:
        >>> method = HistoricalGrowthForecastMethod()
        >>> params = method.get_forecast_params(None, ["2024", "2025"])
        >>> # Returns: {"forecast_type": "historical_growth", "growth_params": None}
    """

    @property
    def name(self) -> str:
        """Return the method name."""
        return "historical_growth"

    @property
    def internal_type(self) -> str:
        """Return the internal forecast type for NodeFactory."""
        return "historical_growth"

    def validate_config(self, config: Any) -> None:
        """Validate the configuration for historical growth method.

        Args:
            config: Not used for historical growth method, can be None or 0.

        Note:
            Historical growth method doesn't require configuration as it
            calculates growth from historical data automatically.
        """
        # Historical growth method doesn't need specific configuration
        # Accept None, 0, or any placeholder value

    def normalize_params(
        self, config: Any, forecast_periods: list[str]
    ) -> dict[str, Any]:
        """Normalize parameters for the NodeFactory.

        Args:
            config: Not used for historical growth method.
            forecast_periods: List of periods to forecast (not used).

        Returns:
            Dict with 'forecast_type' and 'growth_params' keys.
            For historical growth method, growth_params is None.
        """
        return {
            "forecast_type": self.internal_type,
            "growth_params": None,  # Historical growth method calculates internally
        }

    def prepare_historical_data(
        self, node: Node, historical_periods: list[str]
    ) -> Optional[list[float]]:
        """Prepare historical data for growth calculation.

        Args:
            node: The node to extract historical data from.
            historical_periods: List of historical periods.

        Returns:
            List of valid historical values (at least 2 needed for growth).

        Raises:
            ValueError: If insufficient historical data is available.
        """
        if not hasattr(node, "calculate") or not callable(node.calculate):
            raise ValueError(
                f"Node {node.name} cannot be calculated for historical growth method"
            )

        if not hasattr(node, "values") or not isinstance(node.values, dict):
            raise ValueError(
                f"Node {node.name} does not have values dictionary for historical growth method"
            )

        # Extract historical values in chronological order
        historical_values = []
        for period in historical_periods:
            if period in node.values:
                try:
                    value = node.calculate(period)
                    if (
                        value is not None
                        and not np.isnan(value)
                        and not np.isinf(value)
                    ):
                        historical_values.append(float(value))
                except Exception as e:
                    # Log the exception and skip this period
                    logger.debug(
                        f"Skipping period {period} for node {node.name} in historical growth calculation: {e}"
                    )
                    continue

        min_periods = cfg("forecasting.min_historical_periods")
        if len(historical_values) < min_periods:
            raise ValueError(
                f"Need at least {min_periods} historical data points for node {node.name} "
                f"to compute growth rate, found {len(historical_values)}"
            )

        return historical_values

    def calculate_average_growth_rate(self, historical_values: list[float]) -> float:
        """Calculate the average growth rate from historical values.

        Args:
            historical_values: List of historical values in chronological order.

        Returns:
            Average growth rate.

        Note:
            This is a helper method that can be used by the forecast node
            implementation to calculate the growth rate.
        """
        # Calculate period-over-period growth rates
        if len(historical_values) < 2:
            return 0.0

        growth_rates: list[float] = []
        for i in range(1, len(historical_values)):
            previous_value = historical_values[i - 1]
            if previous_value != 0:
                growth_rates.append(
                    (historical_values[i] - previous_value) / previous_value
                )

        if not growth_rates:
            return 0.0

        # Determine aggregation method: 'mean' or 'median'
        agg_method = cfg("forecasting.historical_growth_aggregation")
        if agg_method == "median":
            try:
                return float(np.median(growth_rates))
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Failed to calculate median growth rate, falling back to mean: {e}"
                )
                return float(np.mean(growth_rates))
        # Default to mean
        return float(np.mean(growth_rates))
