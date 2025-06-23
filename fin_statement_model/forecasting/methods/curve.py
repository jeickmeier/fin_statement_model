"""Curve forecast method with variable growth rates per period.

This module implements the CurveForecastMethod, which forecasts future values using a list of
growth rates (one per forecast period) or a single value expanded to all periods.

Configuration:
    - Single numeric value: Will be expanded to match forecast periods
    - List of numeric values: One growth rate per forecast period

Example:
    >>> from fin_statement_model.forecasting.methods.curve import CurveForecastMethod
    >>> method = CurveForecastMethod()
    >>> params = method.get_forecast_params([0.05, 0.04, 0.03], ["2024", "2025", "2026"])
    >>> params["forecast_type"]
    'curve'
    >>> params["growth_params"]
    [0.05, 0.04, 0.03]
"""

from typing import Any

from .base import BaseForecastMethod


class CurveForecastMethod(BaseForecastMethod):
    """Forecast future values using variable growth rates per period.

    This method applies different growth rates for each forecast period,
    allowing non-linear growth patterns across periods.

    Configuration:
        - Single numeric value: Will be expanded to match forecast periods
        - List of numeric values: One growth rate per forecast period

    Example:
        >>> from fin_statement_model.forecasting.methods.curve import CurveForecastMethod
        >>> method = CurveForecastMethod()
        >>> params = method.get_forecast_params([0.05, 0.04, 0.03], ["2024", "2025", "2026"])
        >>> params["forecast_type"]
        'curve'
        >>> params["growth_params"]
        [0.05, 0.04, 0.03]
    """

    @property
    def name(self) -> str:
        """Return the method name.

        Returns:
            The unique name of the forecast method ('curve').
        """
        return "curve"

    @property
    def internal_type(self) -> str:
        """Return the internal forecast type for NodeFactory.

        Returns:
            The internal type string used by the node factory ('curve').
        """
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
                    raise TypeError(f"Curve method: non-numeric value at index {i}: {type(value)}")
        elif not isinstance(config, int | float):
            raise TypeError(f"Curve method requires numeric or list of numeric values, got {type(config)}")

    def normalize_params(self, config: Any, forecast_periods: list[str]) -> dict[str, Any]:
        """Normalize parameters for the NodeFactory.

        Args:
            config: Growth rates (single value or list).
            forecast_periods: List of periods to forecast.

        Returns:
            Dict with 'forecast_type' and 'growth_params' keys.

        Raises:
            ValueError: If list length doesn't match forecast periods.

        Example:
            >>> from fin_statement_model.forecasting.methods.curve import CurveForecastMethod
            >>> method = CurveForecastMethod()
            >>> method.normalize_params([0.05, 0.04, 0.03], ["2024", "2025", "2026"])
            {'forecast_type': 'curve', 'growth_params': [0.05, 0.04, 0.03]}
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
