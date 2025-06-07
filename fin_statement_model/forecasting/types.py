"""Type definitions and data structures for forecasting module.

This module contains all the type aliases, enums, and data structures
used throughout the forecasting sub-module.
"""

from typing import Any, Union, Literal
from collections.abc import Callable
import numpy as np

from pydantic import BaseModel, ConfigDict, model_validator, ValidationError

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
ForecastMethodType = Literal[
    "simple",
    "curve",
    "statistical",
    "average",
    "historical_growth",
]


class StatisticalConfig(BaseModel):
    """Configuration for statistical forecasting method."""

    distribution: str
    params: dict[str, float]

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_distribution(cls, values):  # noqa: N805
        distribution = values.distribution
        params = values.params

        if distribution == "normal":
            required = {"mean", "std"}
            missing = required - params.keys()
            if missing:
                raise ForecastConfigurationError(
                    "Normal distribution requires 'mean' and 'std' parameters",
                    config=params,
                    missing_params=list(missing),
                )
        elif distribution == "uniform":
            required = {"low", "high"}
            missing = required - params.keys()
            if missing:
                raise ForecastConfigurationError(
                    "Uniform distribution requires 'low' and 'high' parameters",
                    config=params,
                    missing_params=list(missing),
                )
        else:
            raise ForecastConfigurationError(
                f"Unsupported distribution: {distribution}",
                config=params,
                invalid_params={"distribution": f"'{distribution}' is not supported"},
            )

        return values


class ForecastConfig(BaseModel):
    """Configuration for a forecast operation."""

    method: ForecastMethodType
    config: Any  # Method-specific configuration

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_config(cls, values):  # noqa: N805
        method = values.method
        cfg = values.config or {}

        valid_methods = {
            "simple",
            "curve",
            "statistical",
            "average",
            "historical_growth",
        }

        if method not in valid_methods:
            raise ForecastMethodError(method=method, supported_methods=list(valid_methods))

        if method == "statistical":
            # Delegate validation to StatisticalConfig for detailed checks
            try:
                StatisticalConfig(**cfg) if isinstance(
                    cfg, dict
                ) else StatisticalConfig.model_validate(cfg)
            except (ForecastConfigurationError, ValidationError) as exc:
                # Re-raise as ForecastConfigurationError for consistency
                raise ForecastConfigurationError(
                    "Invalid statistical configuration",
                    config=cfg,
                ) from exc

        return values


class ForecastResult(BaseModel):
    """Result of a forecast operation."""

    node_name: str
    periods: list[str]
    values: PeriodValue
    method: ForecastMethodType
    base_period: str

    model_config = ConfigDict(extra="forbid")

    def get_value(self, period: str) -> float:
        """Get the forecast value for a specific period."""
        if period not in self.values:
            raise ForecastResultError(
                f"Period {period} not found in forecast results",
                period=period,
                available_periods=list(self.values.keys()),
            )
        return self.values[period]
