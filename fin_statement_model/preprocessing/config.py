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
    """Configuration for normalization transformations.

    Attributes:
        normalization_type: Type of normalization to apply (e.g., 'percent_of', 'minmax', 'standard', 'scale_by').
        reference: Reference column name for 'percent_of' normalization.
        scale_factor: Scaling factor for 'scale_by' normalization.
    """

    normalization_type: Optional[str] = None
    reference: Optional[str] = None
    scale_factor: Optional[float] = None


class TimeSeriesConfig(BaseModel):
    """Configuration for time series transformations.

    Attributes:
        transformation_type: Type of time series transformation (e.g., 'growth_rate', 'moving_avg', 'cagr', 'yoy', 'qoq').
        periods: Number of periods for lag-based calculations.
        window_size: Window size for moving average calculations.
    """

    transformation_type: Optional[str] = None
    periods: Optional[int] = None
    window_size: Optional[int] = None


class PeriodConversionConfig(BaseModel):
    """Configuration for period conversion transformations.

    Attributes:
        conversion_type: Type of period conversion (e.g., 'quarterly_to_annual', 'monthly_to_quarterly', 'monthly_to_annual', 'quarterly_to_ttm').
        aggregation: Aggregation method for conversion (e.g., 'sum', 'mean', 'last', 'first', 'max', 'min').
    """

    conversion_type: Optional[str] = None
    aggregation: Optional[str] = None


class StatementFormattingConfig(BaseModel):
    """Configuration for formatting statement output.

    Attributes:
        statement_type: Type of financial statement (e.g., 'income_statement', 'balance_sheet', 'cash_flow').
        add_subtotals: Whether to include subtotal lines in formatted output.
        apply_sign_convention: Whether to apply standard sign conventions (e.g., liabilities as negative).
    """

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
