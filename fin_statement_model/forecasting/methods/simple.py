"""Simple growth rate forecasting method.

This method applies a constant growth rate to forecast future values.
"""

from typing import Any

from .base import BaseForecastMethod


class SimpleForecastMethod(BaseForecastMethod):
    """Simple growth rate forecasting.

    This method applies a constant growth rate to the base value
    for all forecast periods.

    Configuration:
        - Single numeric value: The growth rate (e.g., 0.05 for 5% growth)
        - List with single value: Will use the first value

    Example:
        >>> method = SimpleForecastMethod()
        >>> params = method.get_forecast_params(0.05, ['2024', '2025'])
        >>> # Returns: {'forecast_type': 'simple', 'growth_params': 0.05}
    """

    @property
    def name(self) -> str:
        """Return the method name."""
        return "simple"

    @property
    def internal_type(self) -> str:
        """Return the internal forecast type for NodeFactory."""
        return "simple"

    def validate_config(self, config: Any) -> None:
        """Validate the configuration for simple method.

        Args:
            config: Should be a numeric value or a list containing a numeric value.

        Raises:
            ValueError: If config is empty list.
            TypeError: If config is not numeric or a list with numeric value.
        """
        if isinstance(config, list):
            if not config:
                raise ValueError("Simple method: empty list provided")
            if not isinstance(config[0], int | float):
                raise TypeError(
                    f"Simple method requires numeric growth rate, got {type(config[0])}"
                )
        elif not isinstance(config, int | float):
            raise TypeError(
                f"Simple method requires numeric growth rate, got {type(config)}"
            )

    def normalize_params(
        self, config: Any, forecast_periods: list[str]
    ) -> dict[str, Any]:
        """Normalize parameters for the NodeFactory.

        Args:
            config: The growth rate (numeric or list with numeric).
            forecast_periods: List of periods to forecast (not used for simple method).

        Returns:
            Dict with 'forecast_type' and 'growth_params' keys.
        """
        # Handle list input - take first value
        growth_rate = float(config[0]) if isinstance(config, list) else float(config)

        return {"forecast_type": self.internal_type, "growth_params": growth_rate}
