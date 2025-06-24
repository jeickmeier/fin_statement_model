"""PreprocessingConfig sub-model."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from fin_statement_model.preprocessing.config import (
    StatementFormattingConfig,
    TransformationType,
)

__all__ = ["PreprocessingConfig"]


class PreprocessingConfig(BaseModel):
    """Settings for data preprocessing operations.

    Attributes are identical to the former definition in
    ``fin_statement_model.config.models``.
    """

    auto_clean_data: bool = Field(True, description="Automatically clean data on import")
    fill_missing_with_zero: bool = Field(False, description="Fill missing values with zero instead of None")
    remove_empty_periods: bool = Field(True, description="Remove periods with all empty values")
    standardize_period_format: bool = Field(True, description="Standardize period names to consistent format")
    default_normalization_type: (
        Literal[
            "percent_of",
            "minmax",
            "standard",
            "scale_by",
        ]
        | None
    ) = Field(None, description="Default normalization method")
    default_transformation_type: TransformationType = Field(
        TransformationType.GROWTH_RATE,
        description="Default time series transformation type",
    )
    default_time_series_periods: int = Field(1, description="Default number of periods for time series transformations")
    default_time_series_window_size: int = Field(3, description="Default window size for time series transformations")
    default_conversion_aggregation: str = Field("sum", description="Default aggregation method for period conversion")
    statement_formatting: StatementFormattingConfig = Field(
        default=StatementFormattingConfig.model_validate({}),
        description="Default statement formatting configuration for preprocessing",
    )

    model_config = ConfigDict(extra="forbid")
