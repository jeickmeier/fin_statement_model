"""Forecast future values by sampling from statistical distributions.

This method generates forecast values by sampling from specified statistical
distributions, useful for Monte Carlo simulations and uncertainty analysis.

Configuration:
    - 'distribution': 'normal' or 'uniform'
    - 'params': Distribution-specific parameters
        - For 'normal': {'mean': float, 'std': float}
        - For 'uniform': {'low': float, 'high': float}

Example:
    >>> method = StatisticalForecastMethod()
    >>> config = {
    ...     "distribution": "normal",
    ...     "params": {"mean": 0.05, "std": 0.02}
    ... }
    >>> params = method.get_forecast_params(config, ["2024", "2025"])
    >>> # Returns: {"forecast_type": "statistical", "growth_params": <callable>}
"""

from typing import Any
import numpy as np
from pydantic import ValidationError
from fin_statement_model.config.helpers import cfg

from .base import BaseForecastMethod
from fin_statement_model.forecasting.types import StatisticalConfig


class StatisticalForecastMethod(BaseForecastMethod):
    """Forecast future values by sampling from statistical distributions.

    This method generates forecast values by sampling from specified statistical
    distributions, useful for Monte Carlo simulations and uncertainty analysis.

    Configuration:
        - 'distribution': 'normal' or 'uniform'
        - 'params': Distribution-specific parameters
            - For 'normal': {'mean': float, 'std': float}
            - For 'uniform': {'low': float, 'high': float}

    Example:
        >>> method = StatisticalForecastMethod()
        >>> config = {
        ...     "distribution": "normal",
        ...     "params": {"mean": 0.05, "std": 0.02}
        ... }
        >>> params = method.get_forecast_params(config, ["2024", "2025"])
        >>> # Returns: {"forecast_type": "statistical", "growth_params": <callable>}
    """

    @property
    def name(self) -> str:
        """Return the method name."""
        return "statistical"

    @property
    def internal_type(self) -> str:
        """Return the internal forecast type for NodeFactory."""
        return "statistical"

    def validate_config(self, config: Any) -> None:
        """Validate the configuration for statistical method.

        Args:
            config: Should be a dict with 'distribution' and 'params' keys.

        Raises:
            TypeError: If config is invalid.
        """
        if not isinstance(config, dict):
            raise TypeError(
                f"Statistical method requires dict configuration, got {type(config)}"
            )

        if "distribution" not in config:
            raise ValueError("Statistical method requires 'distribution' key")

        if "params" not in config:
            raise ValueError("Statistical method requires 'params' key")

        # Validate using StatisticalConfig model (raises ValidationError or ForecastConfigurationError)
        try:
            StatisticalConfig(
                distribution=config["distribution"], params=config["params"]
            )
        except (ValueError, TypeError, ValidationError) as e:
            raise ValueError(f"Invalid statistical configuration: {e}") from e

    def normalize_params(
        self, config: Any, forecast_periods: list[str]
    ) -> dict[str, Any]:
        """Normalize parameters for the NodeFactory.

        Args:
            config: Statistical distribution configuration.
            forecast_periods: List of periods to forecast (not used).

        Returns:
            Dict with 'forecast_type' and 'growth_params' keys.
            The 'growth_params' value is a callable that generates random values.
        """
        # Create validated config
        stat_config = StatisticalConfig(
            distribution=config["distribution"], params=config["params"]
        )

        # Seed RNG if configured
        seed = cfg("forecasting.random_seed")
        if seed is not None:
            rng = np.random.RandomState(seed)
        else:
            rng = np.random.RandomState()

        # Create generator function based on distribution
        def generator() -> float:
            """Generate a random growth rate from the specified distribution."""
            if stat_config.distribution == "normal":
                return float(
                    rng.normal(stat_config.params["mean"], stat_config.params["std"])
                )
            elif stat_config.distribution == "uniform":
                return float(
                    rng.uniform(stat_config.params["low"], stat_config.params["high"])
                )
            else:
                # This shouldn't happen due to validation, but just in case
                raise ValueError(
                    f"Unsupported distribution: {stat_config.distribution}"
                )

        return {"forecast_type": self.internal_type, "growth_params": generator}
