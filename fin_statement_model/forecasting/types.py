"""Define types and data structures for the forecasting module.

This module provides type aliases, Pydantic models for configuration and
results, and error types used throughout the forecasting sub-module.
"""

from collections.abc import Callable
from typing import Any, Literal, Union

import numpy as np
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from fin_statement_model.forecasting.errors import (
    ForecastConfigurationError,
    ForecastMethodError,
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
    """Define configuration schema for statistical forecasting method.

    Validates 'distribution' and 'params' based on the distribution type.
    """

    distribution: str
    params: dict[str, float]

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")  # type: ignore[arg-type]
    def _validate_distribution(cls, values: "StatisticalConfig") -> "StatisticalConfig":
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
    """Define configuration for a forecast operation.

    Enforces method selection and method-specific parameters.
    """

    method: ForecastMethodType
    config: Any  # Method-specific configuration

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")  # type: ignore[arg-type]
    def _validate_config(cls, values: "ForecastConfig") -> "ForecastConfig":
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
            raise ForecastMethodError(
                "Invalid forecast method",
                method=method,
                supported_methods=list(valid_methods),
            )

        if method == "statistical":
            # Delegate validation to StatisticalConfig for detailed checks
            try:
                (
                    StatisticalConfig(**cfg)
                    if isinstance(cfg, dict)
                    else StatisticalConfig.model_validate(cfg)
                )
            except (ForecastConfigurationError, ValidationError) as exc:
                # Re-raise as ForecastConfigurationError for consistency
                raise ForecastConfigurationError(
                    "Invalid statistical configuration",
                    config=cfg,
                ) from exc

        return values


class ForecastResult(BaseModel):
    """Represent forecast results for a node.

    Contains the node name, forecast periods, result values, method, and base period.
    """

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
