"""Average forecasting method based on historical values.

This method forecasts future values as the average of historical values.
"""

import logging
from typing import Any, Optional
import numpy as np

from fin_statement_model.core.nodes import Node
from .base import BaseForecastMethod

logger = logging.getLogger(__name__)


class AverageForecastMethod(BaseForecastMethod):
    """Historical average forecasting.

    This method calculates forecast values as the average of historical
    values. Useful for stable metrics or when expecting mean reversion.

    Configuration:
        - Not required (pass 0 or None)
        - The method will automatically use all available historical data

    Example:
        >>> method = AverageForecastMethod()
        >>> params = method.get_forecast_params(None, ['2024', '2025'])
        >>> # Returns: {'forecast_type': 'average', 'growth_params': None}
    """

    @property
    def name(self) -> str:
        """Return the method name."""
        return "average"

    @property
    def internal_type(self) -> str:
        """Return the internal forecast type for NodeFactory."""
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
        """
        return {
            "forecast_type": self.internal_type,
            "growth_params": None,  # Average method doesn't use growth params
        }

    def prepare_historical_data(
        self, node: Node, historical_periods: list[str]
    ) -> Optional[list[float]]:
        """Prepare historical data for average calculation.

        Args:
            node: The node to extract historical data from.
            historical_periods: List of historical periods.

        Returns:
            List of valid historical values.

        Raises:
            ValueError: If no valid historical data is available.
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
                except Exception as e:
                    # Log the exception and skip this period
                    logger.debug(
                        f"Skipping period {period} for node {node.name} in average calculation: {e}"
                    )
                    continue

        if not historical_values:
            raise ValueError(
                f"No valid historical data available for node {node.name} to compute average"
            )

        return historical_values
