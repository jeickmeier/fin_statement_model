"""Define types and TypedDicts for preprocessing transformers.

This module provides TabularData alias and configuration TypedDicts.
"""

from typing import TypeAlias, TypedDict, Union
import pandas as pd

# Alias for tabular data inputs accepted by transformers
TabularData: TypeAlias = Union[pd.DataFrame, dict[str, float]]


class NormalizationConfig(TypedDict, total=False):
    """Configuration for normalization transformations.

    Attributes:
        normalization_type: 'percent_of', 'minmax', 'standard', or 'scale_by'
        reference: reference field name for 'percent_of' normalization
        scale_factor: factor to apply for 'scale_by' normalization
    """

    normalization_type: str  # 'percent_of', 'minmax', 'standard', 'scale_by'
    reference: str  # reference field name for percent_of
    scale_factor: float  # factor for scale_by normalization


class TimeSeriesConfig(TypedDict, total=False):
    """Configuration for time series transformations.

    Attributes:
        transformation_type: 'growth_rate', 'moving_avg', 'cagr', 'yoy', or 'qoq'
        periods: number of periods for percentage change or other transformations
        window_size: window size for rolling calculations
    """

    transformation_type: str  # 'growth_rate', 'moving_avg', 'cagr', 'yoy', 'qoq'
    periods: int  # periods for pct_change or other
    window_size: int  # window size for rolling calculations


class PeriodConversionConfig(TypedDict, total=False):
    """Configuration for period conversion transformations.

    Attributes:
        conversion_type: 'quarterly_to_annual', 'monthly_to_quarterly', etc.
        aggregation: aggregation method: 'sum', 'mean', 'last', etc.
    """

    conversion_type: str  # 'quarterly_to_annual', 'monthly_to_quarterly', etc.
    aggregation: str  # aggregation method: sum, mean, last, etc.


class StatementFormattingConfig(TypedDict, total=False):
    """Configuration for formatting statement output.

    Attributes:
        statement_type: 'income_statement', 'balance_sheet', 'cash_flow'
        add_subtotals: whether to insert computed subtotals
        apply_sign_convention: whether to apply sign rules to values
    """

    statement_type: str  # 'income_statement', 'balance_sheet', 'cash_flow'
    add_subtotals: bool  # whether to insert subtotals
    apply_sign_convention: bool  # whether to apply sign rules
