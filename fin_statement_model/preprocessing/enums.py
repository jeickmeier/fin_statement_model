"""Define Enum classes for preprocessing transformer types.

Centralize transformer type constants as Enums for clarity.
"""

from enum import Enum


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
    ANNUAL_TO_TTM = "annual_to_ttm"


class StatementType(Enum):
    """Available statement types for StatementFormattingTransformer."""

    INCOME_STATEMENT = "income_statement"
    BALANCE_SHEET = "balance_sheet"
    CASH_FLOW = "cash_flow"
