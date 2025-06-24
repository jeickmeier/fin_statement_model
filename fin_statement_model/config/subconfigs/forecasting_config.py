"""ForecastingConfig sub-model."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["ForecastingConfig"]


class ForecastingConfig(BaseModel):
    """Settings for forecasting behavior.

    Attributes:
        default_method (Literal): Default forecasting method ('simple',
            'historical_growth', 'curve', 'statistical', or 'ml').
        default_periods (int): Default number of periods to forecast.
        default_growth_rate (float): Default growth rate for simple forecasting.
        min_historical_periods (int): Minimum historical periods required.
        allow_negative_forecasts (bool): Allow negative forecast values.
        add_missing_periods (bool): Add missing forecast periods.
        default_bad_forecast_value (float): Value for invalid forecasts.
        continue_on_error (bool): Continue forecasting other nodes if one fails.
        historical_growth_aggregation (Literal['mean', 'median']): Aggregation method.
        random_seed (Optional[int]): Seed for statistical forecasting.
        base_period_strategy (Literal): Strategy for selecting base period.
    """

    default_method: Literal["simple", "average_growth", "curve", "statistical", "ml"] = Field(
        "simple",
        description="Default forecasting method",
    )
    default_periods: int = Field(5, description="Default number of periods to forecast")
    default_growth_rate: float = Field(0.0, description="Default growth rate for simple forecasting")
    min_historical_periods: int = Field(3, description="Minimum historical periods required for forecasting")
    allow_negative_forecasts: bool = Field(True, description="Allow negative values in forecasts")
    add_missing_periods: bool = Field(True, description="Whether to add missing forecast periods to the graph")
    default_bad_forecast_value: float = Field(
        0.0,
        description="Default value to use for NaN, Inf, or error forecasts",
    )
    continue_on_error: bool = Field(
        True,
        description="Whether to continue forecasting other nodes if one node fails",
    )
    historical_growth_aggregation: Literal["mean", "median"] = Field(
        "mean",
        description="Aggregation method for historical growth rate: 'mean' or 'median'",
    )
    random_seed: int | None = Field(
        None,
        description="Random seed for statistical forecasting to ensure reproducible results",
    )
    base_period_strategy: Literal[
        "preferred_then_most_recent",
        "most_recent",
        "last_historical",
    ] = Field(
        "preferred_then_most_recent",
        description=(
            "Strategy for selecting base period: 'preferred_then_most_recent' (default), "
            "'most_recent' (ignore preferred, pick most recent with data), or "
            "'last_historical' (always use last historical period)."
        ),
    )

    @field_validator("default_periods")
    @classmethod
    def validate_periods(cls, v: int) -> int:
        """Validate that *default_periods* is positive."""
        if v <= 0:
            raise ValueError("default_periods must be positive")
        return v

    model_config = ConfigDict(extra="forbid")
