"""Average forecast method using historical mean.

This module implements the AverageForecastMethod, which forecasts future values as the historical
average of available data points. This is useful for stable metrics or when expecting mean reversion.

Configuration:
    - Not required (pass None or 0)

Example:
    >>> from fin_statement_model.forecasting.methods.average import AverageForecastMethod
    >>> method = AverageForecastMethod()
    >>> params = method.get_forecast_params(None, ["2024", "2025"])
    >>> params["forecast_type"]
    'average'
    >>> params["growth_params"] is None
    True
"""

import logging
from typing import Any

import numpy as np

from fin_statement_model.core.nodes import Node

from .base import BaseForecastMethod

logger = logging.getLogger(__name__)


class AverageForecastMethod(BaseForecastMethod):
    """Forecast future values as the historical average of available data.

    This method calculates forecast values as the historical average of available
    data points. Useful for stable metrics or when expecting mean reversion.

    Configuration:
        - Not required (pass None or 0)

    Example:
        >>> from fin_statement_model.forecasting.methods.average import AverageForecastMethod
        >>> method = AverageForecastMethod()
        >>> params = method.get_forecast_params(None, ["2024", "2025"])
        >>> params["forecast_type"]
        'average'
        >>> params["growth_params"] is None
        True
    """

    @property
    def name(self) -> str:
        """Return the method name.

        Returns:
            The unique name of the forecast method ('average').
        """
        return "average"

    @property
    def internal_type(self) -> str:
        """Return the internal forecast type for NodeFactory.

        Returns:
            The internal type string used by the node factory ('average').
        """
        return "average"

    def validate_config(self, config: Any) -> None:
        """Validate the configuration for average method.

        Args:
            config: Not used for average method, can be None or 0.

        Note:
            Average method doesn't require configuration as it uses
            historical data automatically.
        """
        # Average method doesn't need specific configuration
        # Accept None, 0, or any placeholder value

    def normalize_params(self, config: Any, forecast_periods: list[str]) -> dict[str, Any]:
        """Normalize parameters for the NodeFactory.

        Args:
            config: Not used for average method.
            forecast_periods: List of periods to forecast (not used).

        Returns:
            Dict with 'forecast_type' and 'growth_params' keys.
            For average method, growth_params is None.

        Example:
            >>> from fin_statement_model.forecasting.methods.average import AverageForecastMethod
            >>> method = AverageForecastMethod()
            >>> method.normalize_params(None, ["2024", "2025"])
            {'forecast_type': 'average', 'growth_params': None}
        """
        _ = (config, forecast_periods)  # Parameters intentionally unused
        return {
            "forecast_type": self.internal_type,
            "growth_params": None,  # Average method doesn't use growth params
        }

    def prepare_historical_data(self, node: Node, historical_periods: list[str]) -> list[float] | None:
        """Prepare historical data for average calculation.

        Args:
            node: The node to extract historical data from.
            historical_periods: List of historical periods.

        Returns:
            List of valid historical values.

        Raises:
            ValueError: If no valid historical data is available.

        Example:
            >>> # This method is called internally by the forecasting engine.
        """
        if not hasattr(node, "calculate") or not callable(node.calculate):
            raise ValueError(f"Node {node.name} cannot be calculated for average method")

        if not hasattr(node, "values") or not isinstance(node.values, dict):
            raise ValueError(f"Node {node.name} does not have values dictionary for average method")

        # Extract historical values
        historical_values = []
        for period in historical_periods:
            if period in node.values:
                try:
                    value = node.calculate(period)
                    if value is not None and not np.isnan(value) and not np.isinf(value):
                        historical_values.append(float(value))
                except (ValueError, TypeError, ArithmeticError) as e:
                    # Log the exception and skip this period
                    logger.debug("Skipping period %s for node %s in average calculation: %s", period, node.name, e)
                    continue

        if not historical_values:
            raise ValueError(f"No valid historical data available for node {node.name} to compute average")

        return historical_values
