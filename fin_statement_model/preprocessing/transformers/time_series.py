"""Provide the TimeSeriesTransformer for applying common financial time series transformations.

This module defines the transformer for computing growth rates, moving averages,
compound annual growth rate (CAGR), year-over-year (YoY), and quarter-over-quarter (QoQ) changes.
"""

import logging
from typing import ClassVar, Optional, Union

import numpy as np
import pandas as pd

from fin_statement_model.preprocessing.base_transformer import DataTransformer
from fin_statement_model.preprocessing.config import (
    TimeSeriesConfig,
    TransformationType,
)

logger = logging.getLogger(__name__)


class TimeSeriesTransformer(DataTransformer):
    """Transformer for time series financial data analysis.

    This transformer provides common time series transformations used in financial
    analysis to identify trends, growth patterns, and period-over-period changes.

    Supported transformation types:
        - **growth_rate**: Calculate period-to-period growth rates (%)
        - **moving_avg**: Calculate moving averages over specified window
        - **cagr**: Compute compound annual growth rate
        - **yoy**: Year-over-year comparison (%)
        - **qoq**: Quarter-over-quarter comparison (%)

    Data Frequency Assumptions:
        The transformer makes no assumptions about the frequency of your data.
        You must specify the appropriate 'periods' parameter based on your data:

        - For **monthly data**:
            - YoY: use periods=12 (compare to same month last year)
            - QoQ: use periods=3 (compare to same month last quarter)

        - For **quarterly data**:
            - YoY: use periods=4 (compare to same quarter last year)
            - QoQ: use periods=1 (compare to previous quarter)

        - For **annual data**:
            - YoY: use periods=1 (compare to previous year)

    Examples:
        Calculate year-over-year growth for quarterly revenue data:

        >>> import pandas as pd
        >>> from fin_statement_model.preprocessing.transformers import TimeSeriesTransformer
        >>>
        >>> # Quarterly revenue data
        >>> data = pd.DataFrame({
        ...     'revenue': [100, 105, 110, 115, 120, 125, 130, 135],
        ...     'costs': [60, 62, 65, 68, 70, 73, 75, 78]
        ... }, index=pd.date_range('2022-Q1', periods=8, freq='Q'))
        >>>
        >>> # Calculate YoY growth (comparing to same quarter previous year)
        >>> yoy_transformer = TimeSeriesTransformer(
        ...     transformation_type='yoy',
        ...     periods=4  # 4 quarters back for quarterly data
        ... )
        >>> yoy_growth = yoy_transformer.transform(data)
        >>> print(yoy_growth[['revenue_yoy', 'costs_yoy']].iloc[4:])  # First 4 periods will be NaN
        #             revenue_yoy  costs_yoy
        # 2023-Q1           20.0      16.67
        # 2023-Q2           19.05     17.74
        # 2023-Q3           18.18     15.38
        # 2023-Q4           17.39     14.71

        Calculate 3-month moving average for monthly data:

        >>> # Monthly sales data
        >>> monthly_data = pd.DataFrame({
        ...     'sales': [100, 95, 105, 110, 108, 115, 120, 118, 125]
        ... }, index=pd.date_range('2023-01', periods=9, freq='M'))
        >>>
        >>> # Calculate 3-month moving average
        >>> ma_transformer = TimeSeriesTransformer(
        ...     transformation_type='moving_avg',
        ...     window_size=3
        ... )
        >>> ma_result = ma_transformer.transform(monthly_data)
        >>> print(ma_result['sales_ma3'].round(2))
        # 2023-01-31       NaN
        # 2023-02-28       NaN
        # 2023-03-31    100.00
        # 2023-04-30    103.33
        # 2023-05-31    107.67
        # 2023-06-30    111.00
        # 2023-07-31    114.33
        # 2023-08-31    117.67
        # 2023-09-30    121.00

    Note:
        - Growth rate calculations will return NaN for periods without valid
          comparison data (e.g., first 4 periods for YoY with quarterly data)
        - CAGR requires at least 2 data points and positive starting values
        - Moving averages will have NaN values for the first (window_size - 1) periods
    """

    TRANSFORMATION_TYPES: ClassVar[list[str]] = [t.value for t in TransformationType]

    def __init__(
        self,
        transformation_type: Union[
            str, TransformationType
        ] = TransformationType.GROWTH_RATE,
        periods: int = 1,
        window_size: int = 3,
        config: Optional[TimeSeriesConfig] = None,
    ):
        """Initialize the time series transformer.

        Args:
            transformation_type: Type of transformation to apply. Can be either
                a string or TransformationType enum value:
                - 'growth_rate': Period-to-period growth rate
                - 'moving_avg': Rolling window average
                - 'cagr': Compound annual growth rate
                - 'yoy': Year-over-year growth rate
                - 'qoq': Quarter-over-quarter growth rate
            periods: Number of periods for lag calculations. Critical for YoY/QoQ:
                - For YoY with quarterly data: use periods=4
                - For YoY with monthly data: use periods=12
                - For QoQ with quarterly data: use periods=1
                - For QoQ with monthly data: use periods=3
                - For growth_rate: use periods=1 for consecutive period growth
            window_size: Size of the moving average window (only used for 'moving_avg').
                Default is 3.
            config: Optional TimeSeriesConfig object containing configuration.
                If provided, overrides other parameters.

        Raises:
            ValueError: If transformation_type is invalid.

        Examples:
            >>> # YoY for quarterly data
            >>> transformer = TimeSeriesTransformer('yoy', periods=4)
            >>>
            >>> # 3-month moving average
            >>> transformer = TimeSeriesTransformer('moving_avg', window_size=3)
            >>>
            >>> # Quarter-over-quarter for monthly data
            >>> transformer = TimeSeriesTransformer('qoq', periods=3)
        """
        super().__init__(config.model_dump() if config else None)
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
            data: DataFrame containing time series financial data. The DataFrame
                should have a time-based index (DatetimeIndex, PeriodIndex, or
                sequential numeric index) for meaningful time series analysis.

        Returns:
            DataFrame with new columns containing transformed values:
            - For 'growth_rate': adds '{column}_growth' columns
            - For 'moving_avg': adds '{column}_ma{window_size}' columns
            - For 'cagr': adds '{column}_cagr' columns (single value repeated)
            - For 'yoy': adds '{column}_yoy' columns
            - For 'qoq': adds '{column}_qoq' columns

            Original columns are preserved in all cases.

        Raises:
            TypeError: If data is not a pandas DataFrame.

        Examples:
            >>> df = pd.DataFrame({'revenue': [100, 110, 120, 130]})
            >>> transformer = TimeSeriesTransformer('growth_rate')
            >>> result = transformer.transform(df)
            >>> print(result)
            #    revenue  revenue_growth
            # 0      100             NaN
            # 1      110            10.0
            # 2      120            9.09
            # 3      130            8.33
        """
        if not isinstance(data, pd.DataFrame):
            raise TypeError(
                f"Unsupported data type: {type(data)}. Expected pandas.DataFrame"
            )
        return super().transform(data)

    def _transform_impl(
        self, data: Union[pd.DataFrame, pd.Series]
    ) -> Union[pd.DataFrame, pd.Series]:
        """Transform time series data.

        Internal method that performs the actual transformation based on
        the configured transformation type.

        Args:
            data: DataFrame or Series containing time series data.

        Returns:
            Transformed data with the same type as input.
        """
        # Handle Series by converting to DataFrame temporarily
        if isinstance(data, pd.Series):
            temp_df = data.to_frame()
            result_df = self._transform_dataframe(temp_df)
            return result_df.iloc[:, 0]  # Return as Series
        else:
            return self._transform_dataframe(data)

    def _transform_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform a DataFrame with time series data.

        Args:
            df: DataFrame containing time series data with a time-based index.

        Returns:
            DataFrame with new columns added for the specified transformation type.

        Raises:
            NotImplementedError: If the specified transformation_type is not supported.
        """
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
            n_periods_for_cagr = len(df) - 1

            if n_periods_for_cagr < 1:
                logger.warning(
                    "CAGR requires at least 2 periods. Returning NaN for all columns."
                )
                for col in df.columns:
                    result[f"{col}_cagr"] = pd.NA
            else:
                for col in df.columns:
                    start_val = df[col].iloc[0]
                    end_val = df[col].iloc[-1]

                    if pd.isna(start_val) or pd.isna(end_val) or start_val == 0:
                        result[f"{col}_cagr"] = pd.NA
                        continue

                    ratio = end_val / start_val
                    # Check for negative base with fractional exponent leading to complex numbers
                    if ratio < 0 and (1 / n_periods_for_cagr) % 1 != 0:
                        result[f"{col}_cagr"] = pd.NA
                    else:
                        try:
                            # Ensure result is float, np.power can handle negative base if exponent is integer
                            power_val = np.power(ratio, (1 / n_periods_for_cagr))
                            if np.iscomplex(
                                power_val
                            ):  # Should be caught by above, but defensive
                                result[f"{col}_cagr"] = pd.NA
                            else:
                                result[f"{col}_cagr"] = (float(power_val) - 1) * 100
                        except (
                            ValueError,
                            TypeError,
                            ZeroDivisionError,
                        ):  # Catch any math errors
                            result[f"{col}_cagr"] = pd.NA

        elif self.transformation_type == "yoy":
            if self.periods not in [
                4,
                12,
            ]:  # Assuming YoY is typically for quarterly (lag 4) or monthly (lag 12)
                logger.warning(
                    f"For YoY transformation, 'periods' parameter is {self.periods}. "
                    f"This will calculate change over {self.periods} periods. "
                    f"Commonly, 4 (for quarterly data) or 12 (for monthly data) is used for YoY."
                )
            for col in df.columns:
                result[f"{col}_yoy"] = df[col].pct_change(periods=self.periods) * 100

        elif self.transformation_type == "qoq":
            if self.periods not in [
                1,
                3,
            ]:  # Assuming QoQ is typically for quarterly (lag 1) or monthly (lag 3)
                logger.warning(
                    f"For QoQ transformation, 'periods' parameter is {self.periods}. "
                    f"This will calculate change over {self.periods} periods. "
                    f"Commonly, 1 (for quarterly data) or 3 (for monthly data) is used for QoQ."
                )
            for col in df.columns:
                result[f"{col}_qoq"] = df[col].pct_change(periods=self.periods) * 100

        else:
            # This case should ideally be caught by the __init__ validation,
            # but as a safeguard during development:
            raise NotImplementedError(
                f"Transformation type '{self.transformation_type}' is defined in TransformationType enum but not implemented in TimeSeriesTransformer."
            )

        return result
