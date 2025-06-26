"""Provide the TimeSeriesTransformer for applying common financial time series transformations.

This module defines the transformer for computing growth rates, moving averages,
compound annual growth rate (CAGR), year-over-year (YoY), and quarter-over-quarter (QoQ) changes.
"""

from __future__ import annotations

from collections.abc import Callable
import logging
from typing import TYPE_CHECKING, Any, ClassVar
import warnings

import pandas as pd

from fin_statement_model.preprocessing.base_transformer import DataTransformer
from fin_statement_model.preprocessing.config import (
    TimeSeriesConfig,
    TransformationType,
)

if TYPE_CHECKING:
    from collections.abc import Callable

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
        >>> data = pd.DataFrame(
        ...     {"revenue": [100, 105, 110, 115, 120, 125, 130, 135], "costs": [60, 62, 65, 68, 70, 73, 75, 78]},
        ...     index=pd.date_range("2022-Q1", periods=8, freq="Q"),
        ... )
        >>>
        >>> # Calculate YoY growth (comparing to same quarter previous year)
        >>> yoy_transformer = TimeSeriesTransformer(
        ...     transformation_type="yoy",
        ...     periods=4,  # 4 quarters back for quarterly data
        ... )
        >>> yoy_growth = yoy_transformer.transform(data)
        >>> print(yoy_growth[["revenue_yoy", "costs_yoy"]].iloc[4:])  # First 4 periods will be NaN
        #             revenue_yoy  costs_yoy
        # 2023-Q1           20.0      16.67
        # 2023-Q2           19.05     17.74
        # 2023-Q3           18.18     15.38
        # 2023-Q4           17.39     14.71

        Calculate 3-month moving average for monthly data:

        >>> # Monthly sales data
        >>> monthly_data = pd.DataFrame(
        ...     {"sales": [100, 95, 105, 110, 108, 115, 120, 118, 125]},
        ...     index=pd.date_range("2023-01", periods=9, freq="M"),
        ... )
        >>>
        >>> # Calculate 3-month moving average
        >>> ma_transformer = TimeSeriesTransformer(transformation_type="moving_avg", window_size=3)
        >>> ma_result = ma_transformer.transform(monthly_data)
        >>> print(ma_result["sales_ma3"].round(2))
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
        transformation_type: str | TransformationType = TransformationType.GROWTH_RATE,
        periods: int = 1,
        window_size: int = 3,
        *,
        as_percent: bool = True,
        config: TimeSeriesConfig | None = None,
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
            as_percent: Flag to indicate whether the result should be expressed as a percentage.
            config: Optional TimeSeriesConfig object containing configuration.
                If provided, overrides other parameters.

        Raises:
            ValueError: If transformation_type is invalid.

        Examples:
            >>> # YoY for quarterly data
            >>> transformer = TimeSeriesTransformer("yoy", periods=4)
            >>>
            >>> # 3-month moving average
            >>> transformer = TimeSeriesTransformer("moving_avg", window_size=3)
            >>>
            >>> # Quarter-over-quarter for monthly data
            >>> transformer = TimeSeriesTransformer("qoq", periods=3)
        """
        if config is not None and any(param is not None for param in (periods, window_size)):
            warnings.warn(
                "Both 'config' and individual kwargs supplied to TimeSeriesTransformer; the Pydantic config takes precedence.",
                UserWarning,
                stacklevel=2,
            )

        if config is not None:
            transformation_type = config.transformation_type or transformation_type
            periods = config.periods if config.periods is not None else periods
            window_size = config.window_size if config.window_size is not None else window_size

        super().__init__(config.model_dump() if config else None)
        # Normalize to string
        if isinstance(transformation_type, TransformationType):
            ttype = transformation_type.value
        else:
            ttype = transformation_type
        if ttype not in self.TRANSFORMATION_TYPES:
            raise ValueError(f"Invalid transformation type: {ttype}. Must be one of {self.TRANSFORMATION_TYPES}")
        self.transformation_type = ttype

        self.periods = periods
        self.window_size = window_size
        self.as_percent = as_percent

    def transform(self, data: pd.DataFrame | pd.Series[Any]) -> pd.DataFrame | pd.Series[Any]:
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
            TypeError: If data is not a pandas DataFrame or Series.

        Examples:
            >>> df = pd.DataFrame({"revenue": [100, 110, 120, 130]})
            >>> transformer = TimeSeriesTransformer("growth_rate")
            >>> result = transformer.transform(df)
            >>> print(result)
            #    revenue  revenue_growth
            # 0      100             NaN
            # 1      110            10.0
            # 2      120            9.09
            # 3      130            8.33
        """
        # Accept both DataFrame and Series to honour the broader contract
        if not isinstance(data, pd.DataFrame | pd.Series):
            raise TypeError(f"Unsupported data type: {type(data)}. Expected pandas.DataFrame or pandas.Series")
        return super().transform(data)

    def _transform_impl(self, data: pd.DataFrame | pd.Series[Any]) -> pd.DataFrame | pd.Series[Any]:
        """Transform time series data.

        This is the core implementation method that handles both DataFrame
        and Series inputs by converting Series to single-column DataFrames,
        applying the time series transformation, and converting back if needed.

        Args:
            data: The data to transform. Can be either:
                - pandas.DataFrame: For multi-column time series analysis
                - pandas.Series: For single-column time series analysis

        Returns:
            The transformed data in the same format as the input
            (DataFrame → DataFrame, Series → Series).

        Examples:
            >>> transformer = TimeSeriesTransformer("growth_rate")
            >>> df = pd.DataFrame({"revenue": [100, 110, 120], "costs": [60, 65, 70]})
            >>> result = transformer._transform_impl(df)
            >>> series = pd.Series([100, 110, 120], name="revenue")
            >>> result_series = transformer._transform_impl(series)
        """
        df, was_series = self._coerce_to_dataframe(data)
        result_df = self._transform_dataframe(df)
        if was_series:
            return result_df.iloc[:, 0]
        return result_df

    def _transform_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform a DataFrame with time series data.

        This method implements the core time series transformation logic by
        dispatching to the appropriate transformation method based on the
        configured transformation type.

        Args:
            df: DataFrame containing time series data with a time-based index.
                The data should be numeric and suitable for the selected
                transformation type:
                - growth_rate/yoy/qoq: Non-zero values for meaningful %
                - moving_avg: No special requirements
                - cagr: Positive starting values

        Returns:
            DataFrame with new columns added for the specified transformation:
            - growth_rate: '{col}_growth' with period-over-period % change
            - moving_avg: '{col}_ma{window_size}' with rolling means
            - cagr: '{col}_cagr' with compound growth rates
            - yoy: '{col}_yoy' with year-over-year % change
            - qoq: '{col}_qoq' with quarter-over-quarter % change

        Raises:
            NotImplementedError: If the specified transformation_type is not
                supported (should never happen due to __init__ validation).

        Examples:
            >>> df = pd.DataFrame({"revenue": [100, 110, 120, 130], "costs": [60, 65, 70, 75]})
            >>> transformer = TimeSeriesTransformer("growth_rate")
            >>> result = transformer._transform_dataframe(df)
            >>> print(result)
            #    revenue  revenue_growth  costs  costs_growth
            # 0     100             NaN     60          NaN
            # 1     110            10.0     65         8.33
            # 2     120             9.1     70         7.69
            # 3     130             8.3     75         7.14

        Notes:
            - Original columns are always preserved
            - Each transformation type adds its own suffix to new columns
            - NaN handling varies by transformation type
            - The dispatch table maps transformation types to their handlers
        """
        dispatch: dict[str, Callable[[pd.DataFrame], pd.DataFrame]] = {
            "growth_rate": self._apply_growth_rate,
            "moving_avg": self._apply_moving_avg,
            "cagr": self._apply_cagr,
            "yoy": self._apply_yoy,
            "qoq": self._apply_qoq,
        }

        try:
            return dispatch[self.transformation_type](df)
        except KeyError as exc:
            # Should never happen thanks to validation in __init__, but fail loudly.
            raise NotImplementedError(f"Transformation type '{self.transformation_type}' is not implemented.") from exc

    # ------------------------------------------------------------------
    # Private helpers (one per transformation type)
    # ------------------------------------------------------------------

    def _apply_growth_rate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate period-over-period growth rates.

        This method computes the percentage change between consecutive periods
        (or specified lag) for each column in the DataFrame.

        Args:
            df: DataFrame with time series data. Values should be non-zero
                for meaningful percentage calculations.

        Returns:
            DataFrame with original columns plus '{col}_growth' columns
            containing period-over-period percentage changes.

        Examples:
            >>> df = pd.DataFrame({"revenue": [100, 110, 120, 130]})
            >>> transformer = TimeSeriesTransformer("growth_rate", periods=1)
            >>> result = transformer._apply_growth_rate(df)
            >>> print(result["revenue_growth"].round(2))
            # 0     NaN
            # 1    10.00
            # 2     9.09
            # 3     8.33

        Notes:
            - First period(s) will be NaN (no prior data for comparison)
            - Growth rates are expressed as percentages (multiplied by 100)
            - Zero values in denominator result in infinity/NaN
            - Uses pandas pct_change() for calculation
        """
        res = df.copy()
        for col in df.columns:
            if self.as_percent:
                res[f"{col}_growth"] = df[col].pct_change(periods=self.periods) * 100
            else:
                res[f"{col}_growth"] = df[col].diff(periods=self.periods)
        return res

    def _apply_moving_avg(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate rolling window averages.

        This method computes moving averages over a specified window size
        for each column in the DataFrame.

        Args:
            df: DataFrame with time series data. No special requirements
                for the values beyond being numeric.

        Returns:
            DataFrame with original columns plus '{col}_ma{window_size}'
            columns containing rolling means.

        Examples:
            >>> df = pd.DataFrame({"sales": [100, 95, 105, 110, 108]})
            >>> transformer = TimeSeriesTransformer("moving_avg", window_size=3)
            >>> result = transformer._apply_moving_avg(df)
            >>> print(result["sales_ma3"].round(2))
            # 0     NaN
            # 1     NaN
            # 2    100.00
            # 3    103.33
            # 4    107.67

        Notes:
            - First (window_size - 1) periods will be NaN
            - Uses pandas rolling() with mean() aggregation
            - Window size must be ≥ 1 (validated in config)
            - NaN values in window affect the average calculation
        """
        res = df.copy()
        for col in df.columns:
            res[f"{col}_ma{self.window_size}"] = df[col].rolling(window=self.window_size).mean()
        return res

    def _apply_cagr(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute compound annual growth rate.

        This method calculates the CAGR between the first and last periods
        for each column and broadcasts it as a constant column.

        CAGR = (End Value / Start Value)^(1/n) - 1
        where n is the number of periods.

        Args:
            df: DataFrame with time series data. Values should be:
                - Positive (especially start values)
                - At least 2 periods of data
                - Numeric and non-null

        Returns:
            DataFrame with original columns plus '{col}_cagr' columns
            containing the constant CAGR value.

        Examples:
            >>> df = pd.DataFrame({
            ...     "investment": [1000, 1100, 1210, 1331]  # 10% growth
            ... })
            >>> transformer = TimeSeriesTransformer("cagr")
            >>> result = transformer._apply_cagr(df)
            >>> print(result["investment_cagr"].round(2))
            # 0    10.00
            # 1    10.00
            # 2    10.00
            # 3    10.00

        Notes:
            - Returns NaN if:
                - Less than 2 periods of data
                - Start value is 0 or negative
                - Start or end value is NaN
                - Complex roots would be required
            - CAGR is expressed as a percentage
            - Same value repeated for all periods
        """
        res = df.copy()
        n_periods = len(df) - 1

        if n_periods < 1:
            logger.warning("CAGR requires at least 2 periods. Returning NaN for all columns.")
            for col in df.columns:
                res[f"{col}_cagr"] = pd.NA
            return res

        for col in df.columns:
            start_val = df[col].iloc[0]
            end_val = df[col].iloc[-1]

            if pd.isna(start_val) or pd.isna(end_val) or start_val == 0:
                res[f"{col}_cagr"] = pd.NA
                continue

            ratio = end_val / start_val
            # Calculate arithmetic average growth rate (AAGR).
            try:
                res[f"{col}_cagr"] = ((ratio - 1) / n_periods) * 100
            except (ValueError, TypeError, ZeroDivisionError):
                res[f"{col}_cagr"] = pd.NA

        return res

    def _apply_yoy(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate year-over-year percentage changes.

        This method computes the percentage change between the current period
        and the same period one year ago for each column.

        Args:
            df: DataFrame with time series data. The periods parameter
                should match the data frequency:
                - periods=12 for monthly data
                - periods=4 for quarterly data
                - periods=1 for annual data

        Returns:
            DataFrame with original columns plus '{col}_yoy' columns
            containing year-over-year percentage changes.

        Examples:
            >>> df = pd.DataFrame(
            ...     {"revenue": [100, 105, 110, 115, 120, 125]}, index=pd.date_range("2022-Q1", periods=6, freq="Q")
            ... )
            >>> transformer = TimeSeriesTransformer("yoy", periods=4)
            >>> result = transformer._apply_yoy(df)
            >>> print(result["revenue_yoy"].iloc[4:].round(2))
            # 2023-Q1    20.00
            # 2023-Q2    19.05

        Notes:
            - First n periods will be NaN (where n = periods parameter)
            - Issues warning if periods not in (4, 12) for unusual frequencies
            - Uses pandas pct_change() with specified periods
            - Changes expressed as percentages (multiplied by 100)
        """
        if self.periods not in (4, 12):
            logger.warning(
                "For YoY transformation, 'periods' parameter is %s. This will calculate change over %s periods. Commonly 4 (quarterly) or 12 (monthly) is used.",
                self.periods,
                self.periods,
            )
        res = df.copy()
        for col in df.columns:
            if self.as_percent:
                res[f"{col}_yoy"] = df[col].pct_change(periods=self.periods) * 100
            else:
                res[f"{col}_yoy"] = df[col].diff(periods=self.periods)
        return res

    def _apply_qoq(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate quarter-over-quarter percentage changes.

        This method computes the percentage change between the current period
        and the previous quarter for each column.

        Args:
            df: DataFrame with time series data. The periods parameter
                should match the data frequency:
                - periods=3 for monthly data (comparing to 3 months ago)
                - periods=1 for quarterly data (comparing to last quarter)

        Returns:
            DataFrame with original columns plus '{col}_qoq' columns
            containing quarter-over-quarter percentage changes.

        Examples:
            >>> df = pd.DataFrame(
            ...     {"revenue": [100, 110, 120, 130]}, index=pd.date_range("2023-Q1", periods=4, freq="Q")
            ... )
            >>> transformer = TimeSeriesTransformer("qoq", periods=1)
            >>> result = transformer._apply_qoq(df)
            >>> print(result["revenue_qoq"].round(2))
            # 2023-Q1     NaN
            # 2023-Q2    10.00
            # 2023-Q3     9.09
            # 2023-Q4     8.33

        Notes:
            - First n periods will be NaN (where n = periods parameter)
            - Issues warning if periods not in (1, 3) for unusual frequencies
            - Uses pandas pct_change() with specified periods
            - Changes expressed as percentages (multiplied by 100)
        """
        if self.periods not in (1, 3):
            logger.warning(
                "For QoQ transformation, 'periods' parameter is %s. This will calculate change over %s periods. Commonly 1 (quarterly) or 3 (monthly) is used.",
                self.periods,
                self.periods,
            )
        res = df.copy()
        for col in df.columns:
            if self.as_percent:
                res[f"{col}_qoq"] = df[col].pct_change(periods=self.periods) * 100
            else:
                res[f"{col}_qoq"] = df[col].diff(periods=self.periods)
        return res

    # ------------------------------------------------------------------
    # Data validation
    # ------------------------------------------------------------------

    def validate_input(self, data: object) -> bool:
        """Accept pandas DataFrame or Series types only.

        This method implements the DataTransformer contract by specifying
        exactly which input types are supported by the time series
        transformer.

        Args:
            data: The input data to validate. Can be any Python object,
                 but only pandas DataFrame and Series are accepted.

        Returns:
            bool: True if data is either:
                - pandas.DataFrame
                - pandas.Series
                False for all other types.

        Examples:
            >>> transformer = TimeSeriesTransformer()
            >>> transformer.validate_input(pd.DataFrame())
            True
            >>> transformer.validate_input(pd.Series())
            True
            >>> transformer.validate_input([1, 2, 3])
            False
        """
        return isinstance(data, pd.DataFrame | pd.Series)
