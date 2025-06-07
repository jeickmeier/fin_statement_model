"""Configuration models and enums for preprocessing transformers.

This module contains Pydantic models and Enums for configuring preprocessing transformations.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel


class NormalizationType(Enum):
    """Available normalization types for NormalizationTransformer."""

    PERCENT_OF = "percent_of"
    MINMAX = "minmax"
    STANDARD = "standard"
    SCALE_BY = "scale_by"


class TransformationType(Enum):
    """Available transformation types for TimeSeriesTransformer."""

    GROWTH_RATE = "growth_rate"
    MOVING_AVG = "moving_avg"
    CAGR = "cagr"
    YOY = "yoy"
    QOQ = "qoq"


class ConversionType(Enum):
    """Available conversion types for PeriodConversionTransformer."""

    QUARTERLY_TO_ANNUAL = "quarterly_to_annual"
    MONTHLY_TO_QUARTERLY = "monthly_to_quarterly"
    MONTHLY_TO_ANNUAL = "monthly_to_annual"
    QUARTERLY_TO_TTM = "quarterly_to_ttm"


class StatementType(Enum):
    """Available statement types for StatementFormattingTransformer."""

    INCOME_STATEMENT = "income_statement"
    BALANCE_SHEET = "balance_sheet"
    CASH_FLOW = "cash_flow"


class NormalizationConfig(BaseModel):
    """Configuration for normalization transformations."""

    normalization_type: Optional[str] = None
    reference: Optional[str] = None
    scale_factor: Optional[float] = None


class TimeSeriesConfig(BaseModel):
    """Configuration for time series transformations."""

    transformation_type: Optional[str] = None
    periods: Optional[int] = None
    window_size: Optional[int] = None


class PeriodConversionConfig(BaseModel):
    """Configuration for period conversion transformations."""

    conversion_type: Optional[str] = None
    aggregation: Optional[str] = None


class StatementFormattingConfig(BaseModel):
    """Configuration for formatting statement output."""

    statement_type: Optional[str] = None
    add_subtotals: Optional[bool] = None
    apply_sign_convention: Optional[bool] = None


__all__ = [
    "ConversionType",
    "NormalizationConfig",
    "NormalizationType",
    "PeriodConversionConfig",
    "StatementFormattingConfig",
    "StatementType",
    "TimeSeriesConfig",
    "TransformationType",
]
