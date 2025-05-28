"""Type definitions and data structures for forecasting module.

This module contains all the type aliases, enums, and data structures
used throughout the forecasting sub-module.
"""

from typing import Any, Union, Literal
from collections.abc import Callable
import numpy as np
from dataclasses import dataclass

# Type aliases for clarity
Numeric = Union[int, float, np.number[Any]]
GrowthRate = Union[float, list[float], Callable[[], float]]
PeriodValue = dict[str, float]

# Forecast method types
ForecastMethodType = Literal[
    "simple", "curve", "statistical", "average", "historical_growth"
]

# Internal forecast types used by NodeFactory
InternalForecastType = Literal[
    "fixed", "curve", "statistical", "average", "historical_growth"
]


@dataclass
class ForecastConfig:
    """Configuration for a forecast operation."""

    method: ForecastMethodType
    config: Any  # Method-specific configuration

    def __post_init__(self) -> None:
        """Validate the forecast configuration."""
        if self.method not in [
            "simple",
            "curve",
            "statistical",
            "average",
            "historical_growth",
        ]:
            raise ValueError(f"Invalid forecast method: {self.method}")


@dataclass
class StatisticalConfig:
    """Configuration for statistical forecasting methods."""

    distribution: Literal["normal", "uniform"]
    params: dict[str, float]

    def __post_init__(self) -> None:
        """Validate the statistical configuration."""
        if self.distribution == "normal":
            if "mean" not in self.params or "std" not in self.params:
                raise ValueError(
                    "Normal distribution requires 'mean' and 'std' parameters"
                )
        elif self.distribution == "uniform":
            if "low" not in self.params or "high" not in self.params:
                raise ValueError(
                    "Uniform distribution requires 'low' and 'high' parameters"
                )
        else:
            raise ValueError(f"Unsupported distribution: {self.distribution}")


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
            raise KeyError(f"Period {period} not found in forecast results")
        return self.values[period]
