"""Financial data transformers for the Financial Statement Model.

This module provides the TimeSeriesTransformer which applies growth rates,
moving averages, CAGR, year-over-year, and quarter-over-quarter conversions.
"""

import pandas as pd
from typing import Union, Optional, ClassVar

from fin_statement_model.preprocessing.types import TimeSeriesConfig
from fin_statement_model.preprocessing.enums import TransformationType
from fin_statement_model.preprocessing.base_transformer import DataTransformer


class TimeSeriesTransformer(DataTransformer):
    """Transformer for time series financial data.

    This transformer can apply common time series transformations like:
    - Calculating growth rates
    - Calculating moving averages
    - Computing compound annual growth rate (CAGR)
    - Converting to year-over-year or quarter-over-quarter comparisons
    """

    TRANSFORMATION_TYPES: ClassVar[list[str]] = [t.value for t in TransformationType]

    def __init__(
        self,
        transformation_type: Union[str, TransformationType] = TransformationType.GROWTH_RATE,
        periods: int = 1,
        window_size: int = 3,
        config: Optional[TimeSeriesConfig] = None,
    ):
        """Initialize the time series transformer.

        Args:
            transformation_type: Type of transformation to apply
                - 'growth_rate': Calculate period-to-period growth rates
                - 'moving_avg': Calculate moving average
                - 'cagr': Calculate compound annual growth rate
                - 'yoy': Year-over-year comparison
                - 'qoq': Quarter-over-quarter comparison
            periods: Number of periods to use in calculations
            window_size: Size of the moving average window
            config: Additional configuration options
        """
        super().__init__(config)
        # Normalize to string
        if isinstance(transformation_type, TransformationType):
            ttype = transformation_type.value
        else:
            ttype = transformation_type
        if ttype not in self.TRANSFORMATION_TYPES:
            raise ValueError(
                f"Invalid transformation type: {ttype}. Must be one of {self.TRANSFORMATION_TYPES}"
            )
        self.transformation_type = ttype

        self.periods = periods
        self.window_size = window_size

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Transform time series data based on the configured transformation type.

        Args:
            data: pd.DataFrame containing time series financial data

        Returns:
            pd.DataFrame: Transformed DataFrame
        """
        if not isinstance(data, pd.DataFrame):
            raise TypeError(f"Unsupported data type: {type(data)}. Expected pandas.DataFrame")
        return self._transform_dataframe(data)

    def _transform_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform a DataFrame with time series data."""
        result = df.copy()

        if self.transformation_type == "growth_rate":
            for col in df.columns:
                result[f"{col}_growth"] = df[col].pct_change(periods=self.periods) * 100

        elif self.transformation_type == "moving_avg":
            for col in df.columns:
                result[f"{col}_ma{self.window_size}"] = (
                    df[col].rolling(window=self.window_size).mean()
                )

        elif self.transformation_type == "cagr":
            # Assuming the index represents time periods
            n_periods = len(df) - 1
            for col in df.columns:
                start = df[col].iloc[0]
                end = df[col].iloc[-1]
                if start > 0:
                    result[f"{col}_cagr"] = ((end / start) ** (1 / n_periods) - 1) * 100

        elif self.transformation_type == "yoy":
            for col in df.columns:
                result[f"{col}_yoy"] = df[col].pct_change(periods=12) * 100

        elif self.transformation_type == "qoq":
            for col in df.columns:
                result[f"{col}_qoq"] = df[col].pct_change(periods=3) * 100

        return result
