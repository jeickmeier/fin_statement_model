"""Types and data structures for the forecasting module.

This module provides type aliases, Pydantic models for configuration and
results, and error types used throughout the forecasting sub-module.

Features:
    - Type aliases for numeric and growth rate types
    - Pydantic models for forecast configuration, statistical config, and results
    - Validation logic for method selection and statistical parameters
    - Error types for robust handling

Example:
    >>> from fin_statement_model.forecasting.types import ForecastConfig, ForecastResult
    >>> cfg = ForecastConfig(method="simple", config=0.05)
    >>> cfg.method
    'simple'
    >>> result = ForecastResult(
    ...     node_name="revenue",
    ...     periods=["2024", "2025"],
    ...     values={"2024": 1050.0, "2025": 1102.5},
    ...     method="simple",
    ...     base_period="2023"
    ... )
    >>> result.get_value("2024")
    1050.0
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
    """Configuration schema for statistical forecasting method.

    Validates 'distribution' and 'params' based on the distribution type.

    Example:
        >>> from fin_statement_model.forecasting.types import StatisticalConfig
        >>> StatisticalConfig(distribution="normal", params={"mean": 0.05, "std": 0.02})
        StatisticalConfig(distribution='normal', params={'mean': 0.05, 'std': 0.02})
    """

    distribution: str
    params: dict[str, float]

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")  # type: ignore[arg-type]
    def _validate_distribution(cls, values: "StatisticalConfig") -> "StatisticalConfig":
        """Validate distribution and parameters for statistical config.

        Args:
            values: The StatisticalConfig instance.

        Returns:
            The validated StatisticalConfig instance.

        Raises:
            ForecastConfigurationError: If required parameters are missing or distribution is unsupported.
        """
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
    """Configuration for a forecast operation.

    Enforces method selection and method-specific parameters.

    Example:
        >>> from fin_statement_model.forecasting.types import ForecastConfig
        >>> ForecastConfig(method="simple", config=0.05)
        ForecastConfig(method='simple', config=0.05)
    """

    method: ForecastMethodType
    config: Any  # Method-specific configuration

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")  # type: ignore[arg-type]
    def _validate_config(cls, values: "ForecastConfig") -> "ForecastConfig":
        """Validate method and config for forecast operation.

        Args:
            values: The ForecastConfig instance.

        Returns:
            The validated ForecastConfig instance.

        Raises:
            ForecastMethodError: If method is invalid.
            ForecastConfigurationError: If statistical config is invalid.
        """
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
    """Forecast results for a node.

    Contains the node name, forecast periods, result values, method, and base period.

    Example:
        >>> from fin_statement_model.forecasting.types import ForecastResult
        >>> result = ForecastResult(
        ...     node_name="revenue",
        ...     periods=["2024", "2025"],
        ...     values={"2024": 1050.0, "2025": 1102.5},
        ...     method="simple",
        ...     base_period="2023"
        ... )
        >>> result.get_value("2024")
        1050.0
    """

    node_name: str
    periods: list[str]
    values: PeriodValue
    method: ForecastMethodType
    base_period: str

    model_config = ConfigDict(extra="forbid")

    def get_value(self, period: str) -> float:
        """Get the forecast value for a specific period.

        Args:
            period: The period to retrieve the value for.

        Returns:
            The forecast value for the specified period.

        Raises:
            ForecastResultError: If the period is not found in the results.

        Example:
            >>> from fin_statement_model.forecasting.types import ForecastResult
            >>> result = ForecastResult(
            ...     node_name="revenue",
            ...     periods=["2024"],
            ...     values={"2024": 1050.0},
            ...     method="simple",
            ...     base_period="2023"
            ... )
            >>> result.get_value("2024")
            1050.0
        """
        if period not in self.values:
            raise ForecastResultError(
                f"Period {period} not found in forecast results",
                period=period,
                available_periods=list(self.values.keys()),
            )
        return self.values[period]
