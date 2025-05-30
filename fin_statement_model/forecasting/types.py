"""Type definitions and data structures for forecasting module.

This module contains all the type aliases, enums, and data structures
used throughout the forecasting sub-module.
"""

from typing import Any, Union, Literal
from collections.abc import Callable
import numpy as np
from dataclasses import dataclass

from fin_statement_model.forecasting.errors import (
    ForecastMethodError,
    ForecastConfigurationError,
    ForecastResultError,
)

# Type aliases for clarity
Numeric = Union[int, float, np.number[Any]]
GrowthRate = Union[float, list[float], Callable[[], float]]
PeriodValue = dict[str, float]

# Forecast method types
ForecastMethodType = Literal["simple", "curve", "statistical", "average", "historical_growth"]


@dataclass
class StatisticalConfig:
    """Configuration for statistical forecasting method."""

    distribution: str
    params: dict[str, float]

    def __post_init__(self) -> None:
        """Validate the statistical configuration."""
        self.validate()

    def validate(self) -> None:
        """Validate the statistical configuration.

        Raises:
            ForecastConfigurationError: If parameters are invalid.
        """
        if self.distribution == "normal":
            if "mean" not in self.params or "std" not in self.params:
                raise ForecastConfigurationError(
                    "Normal distribution requires 'mean' and 'std' parameters",
                    config=self.params,
                    missing_params=["mean", "std"]
                    if "mean" not in self.params and "std" not in self.params
                    else ["mean"]
                    if "mean" not in self.params
                    else ["std"],
                )
        elif self.distribution == "uniform":
            if "low" not in self.params or "high" not in self.params:
                raise ForecastConfigurationError(
                    "Uniform distribution requires 'low' and 'high' parameters",
                    config=self.params,
                    missing_params=["low", "high"]
                    if "low" not in self.params and "high" not in self.params
                    else ["low"]
                    if "low" not in self.params
                    else ["high"],
                )
        else:
            raise ForecastConfigurationError(
                f"Unsupported distribution: {self.distribution}",
                config=self.params,
                invalid_params={"distribution": f"'{self.distribution}' is not supported"},
            )


@dataclass
class ForecastConfig:
    """Configuration for a forecast operation."""

    method: ForecastMethodType
    config: Any  # Method-specific configuration

    def __post_init__(self) -> None:
        """Validate the forecast configuration."""
        self.validate()

    def validate(self) -> None:
        """Validate the forecast configuration.

        Raises:
            ForecastMethodError: If method is invalid.
            ForecastConfigurationError: If parameters are invalid for the method.
        """
        valid_methods = ["simple", "curve", "statistical", "average", "historical_growth"]
        if self.method not in valid_methods:
            raise ForecastMethodError(
                f"Invalid forecast method: {self.method}",
                method=self.method,
                supported_methods=valid_methods,
            )

        # Validate parameters for specific methods
        if self.method == "statistical":
            distribution = self.config.get("distribution", "normal")
            params = self.config.get("params", {})
            if distribution == "normal":
                if "mean" not in params or "std" not in params:
                    raise ForecastConfigurationError(
                        "Normal distribution requires 'mean' and 'std' parameters",
                        config=self.config,
                        missing_params=["mean", "std"]
                        if "mean" not in params and "std" not in params
                        else ["mean"]
                        if "mean" not in params
                        else ["std"],
                    )
            elif distribution == "uniform":
                if "low" not in params or "high" not in params:
                    raise ForecastConfigurationError(
                        "Uniform distribution requires 'low' and 'high' parameters",
                        config=self.config,
                        missing_params=["low", "high"]
                        if "low" not in params and "high" not in params
                        else ["low"]
                        if "low" not in params
                        else ["high"],
                    )
            else:
                raise ForecastConfigurationError(
                    f"Unsupported distribution: {distribution}",
                    config=self.config,
                    invalid_params={"distribution": f"'{distribution}' is not supported"},
                )


@dataclass
class ForecastResult:
    """Result of a forecast operation."""

    node_name: str
    periods: list[str]
    values: PeriodValue
    method: ForecastMethodType
    base_period: str

    def get_value(self, period: str) -> float:
        """Get the forecast value for a specific period."""
        if period not in self.values:
            raise ForecastResultError(
                f"Period {period} not found in forecast results",
                period=period,
                available_periods=list(self.values.keys()),
            )
        return self.values[period]
