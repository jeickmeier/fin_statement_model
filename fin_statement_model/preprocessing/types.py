"""Define types and TypedDicts for preprocessing transformers.

This module provides a TabularData alias (pd.DataFrame only) and configuration TypedDicts.
"""

from typing import Optional
from pydantic import BaseModel
import pandas as pd

# Alias for tabular data inputs (DataFrame-only) accepted by transformers
TabularData = pd.DataFrame


class NormalizationConfig(BaseModel):
    """Configuration for normalization transformations.

    Attributes:
        normalization_type: 'percent_of', 'minmax', 'standard', or 'scale_by'
        reference: reference field name for 'percent_of' normalization
        scale_factor: factor to apply for 'scale_by' normalization
    """

    normalization_type: Optional[str] = None
    reference: Optional[str] = None
    scale_factor: Optional[float] = None


class TimeSeriesConfig(BaseModel):
    """Configuration for time series transformations.

    Attributes:
        transformation_type: 'growth_rate', 'moving_avg', 'cagr', 'yoy', or 'qoq'
        periods: number of periods for percentage change or other transformations
        window_size: window size for rolling calculations
    """

    transformation_type: Optional[str] = None
    periods: Optional[int] = None
    window_size: Optional[int] = None


class PeriodConversionConfig(BaseModel):
    """Configuration for period conversion transformations.

    Attributes:
        conversion_type: 'quarterly_to_annual', 'monthly_to_quarterly', etc.
        aggregation: aggregation method: 'sum', 'mean', 'last', etc.
    """

    conversion_type: Optional[str] = None
    aggregation: Optional[str] = None


class StatementFormattingConfig(BaseModel):
    """Configuration for formatting statement output.

    Attributes:
        statement_type: 'income_statement', 'balance_sheet', 'cash_flow'
        add_subtotals: whether to insert computed subtotals
        apply_sign_convention: whether to apply sign rules to values
    """

    statement_type: Optional[str] = None
    add_subtotals: Optional[bool] = None
    apply_sign_convention: Optional[bool] = None
