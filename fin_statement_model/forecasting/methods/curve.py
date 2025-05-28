"""Curve forecasting method with variable growth rates.

This method applies different growth rates for each forecast period.
"""

from typing import Any

from .base import BaseForecastMethod
from fin_statement_model.forecasting.types import InternalForecastType


class CurveForecastMethod(BaseForecastMethod):
    """Variable growth rate forecasting.

    This method applies different growth rates for each forecast period,
    allowing for non-linear growth patterns.

    Configuration:
        - List of numeric values: One growth rate per forecast period
        - Single numeric value: Will be expanded to match forecast periods

    Example:
        >>> method = CurveForecastMethod()
        >>> params = method.get_forecast_params([0.05, 0.04, 0.03], ['2024', '2025', '2026'])
        >>> # Returns: {'forecast_type': 'curve', 'growth_params': [0.05, 0.04, 0.03]}
    """

    @property
    def name(self) -> str:
        """Return the method name."""
        return "curve"

    @property
    def internal_type(self) -> InternalForecastType:
        """Return the internal forecast type for NodeFactory."""
        return "curve"

    def validate_config(self, config: Any) -> None:
        """Validate the configuration for curve method.

        Args:
            config: Should be a numeric value or a list of numeric values.

        Raises:
            ValueError: If config is empty list.
            TypeError: If config is not numeric or list of numerics.
        """
        if isinstance(config, list):
            if not config:
                raise ValueError("Curve method: empty list provided")
            for i, value in enumerate(config):
                if not isinstance(value, int | float):
                    raise TypeError(
                        f"Curve method: non-numeric value at index {i}: {type(value)}"
                    )
        elif not isinstance(config, int | float):
            raise TypeError(
                f"Curve method requires numeric or list of numeric values, got {type(config)}"
            )

    def normalize_params(
        self, config: Any, forecast_periods: list[str]
    ) -> dict[str, Any]:
        """Normalize parameters for the NodeFactory.

        Args:
            config: Growth rates (single value or list).
            forecast_periods: List of periods to forecast.

        Returns:
            Dict with 'forecast_type' and 'growth_params' keys.

        Raises:
            ValueError: If list length doesn't match forecast periods.
        """
        if not isinstance(config, list):
            # Single value - expand to match forecast periods
            growth_rates = [float(config)] * len(forecast_periods)
        else:
            # List of values - must match forecast periods length
            if len(config) != len(forecast_periods):
                raise ValueError(
                    f"Curve method: growth rate list length ({len(config)}) "
                    f"must match forecast periods ({len(forecast_periods)})"
                )
            growth_rates = [float(x) for x in config]

        return {"forecast_type": self.internal_type, "growth_params": growth_rates}
