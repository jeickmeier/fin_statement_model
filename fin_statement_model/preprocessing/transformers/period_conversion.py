"""Provide the PeriodConversionTransformer for converting between financial reporting periods.

This module defines the transformer for aggregating higher-frequency data to lower-frequency periods
and calculating trailing metrics such as trailing twelve months (TTM). Supported conversions include:
quarterly_to_annual, monthly_to_quarterly, monthly_to_annual, and quarterly_to_ttm.
"""

from __future__ import annotations

from collections.abc import Callable
import logging
from typing import TYPE_CHECKING, Any, ClassVar, cast
import warnings

import pandas as pd

from fin_statement_model.core.errors import DataValidationError
from fin_statement_model.preprocessing.base_transformer import DataTransformer
from fin_statement_model.preprocessing.config import (
    ConversionType,
    PeriodConversionConfig,
)
from fin_statement_model.preprocessing.periods import Period, resample_to_period

if TYPE_CHECKING:
    from collections.abc import Callable

# Configure logging
logger = logging.getLogger(__name__)


class PeriodConversionTransformer(DataTransformer):
    """Transformer for converting between different financial reporting periods.

    This transformer aggregates financial data from higher-frequency periods
    (e.g., monthly, quarterly) to lower-frequency periods (e.g., quarterly, annual)
    or calculates trailing metrics like TTM (Trailing Twelve Months).

    Supported conversion types:
        - **quarterly_to_annual**: Aggregate 4 quarters into annual data
        - **monthly_to_quarterly**: Aggregate 3 months into quarterly data
        - **monthly_to_annual**: Aggregate 12 months into annual data
        - **quarterly_to_ttm**: Calculate trailing twelve months from quarterly data

    Input Data Requirements:
        - Data must have a DatetimeIndex or an index convertible to datetime
        - The index should represent the period-end dates
        - Data frequency should match the conversion type (e.g., quarterly data
          for quarterly_to_annual conversion)

    Aggregation Methods:
        - **sum**: Total values (default) - use for flow items like revenue, expenses
        - **mean**: Average values - use for rates, ratios, or average balances
        - **last**: Take last value - use for balance sheet items (point-in-time)
        - **first**: Take first value - use for opening balances
        - **max/min**: Maximum/minimum values - use for peak/trough analysis

    Examples:
        Convert quarterly revenue to annual totals:

        >>> import pandas as pd
        >>> from fin_statement_model.preprocessing.transformers import PeriodConversionTransformer
        >>>
        >>> # Quarterly revenue and expense data
        >>> quarterly_data = pd.DataFrame(
        ...     {"revenue": [100, 110, 120, 130, 140, 150, 160, 170], "expenses": [80, 85, 90, 95, 100, 105, 110, 115]},
        ...     index=pd.date_range("2022-03-31", periods=8, freq="Q"),
        ... )
        >>>
        >>> # Convert to annual data (sum 4 quarters)
        >>> annual_converter = PeriodConversionTransformer(conversion_type="quarterly_to_annual", aggregation="sum")
        >>> annual_data = annual_converter.transform(quarterly_data)
        >>> print(annual_data)
        #       revenue  expenses
        # 2022      460       350
        # 2023      620       430

        Convert monthly balance sheet to quarterly (taking last value):

        >>> # Monthly balance sheet data
        >>> monthly_bs = pd.DataFrame(
        ...     {"total_assets": [1000, 1020, 1050, 1080, 1100, 1150], "total_equity": [600, 610, 620, 630, 640, 650]},
        ...     index=pd.date_range("2023-01-31", periods=6, freq="M"),
        ... )
        >>>
        >>> # Convert to quarterly, taking last month's value
        >>> quarterly_converter = PeriodConversionTransformer(
        ...     conversion_type="monthly_to_quarterly", aggregation="last"
        ... )
        >>> quarterly_bs = quarterly_converter.transform(monthly_bs)
        >>> print(quarterly_bs)
        #                  total_assets  total_equity
        # (2023, 1)              1050           620
        # (2023, 2)              1150           650

        Calculate trailing twelve months (TTM) from quarterly data:

        >>> # Quarterly earnings data
        >>> quarterly_earnings = pd.DataFrame(
        ...     {"net_income": [25, 30, 35, 40, 45, 50, 55, 60]}, index=pd.date_range("2022-03-31", periods=8, freq="Q")
        ... )
        >>>
        >>> # Calculate TTM (rolling 4-quarter sum)
        >>> ttm_converter = PeriodConversionTransformer(conversion_type="quarterly_to_ttm", aggregation="sum")
        >>> ttm_data = ttm_converter.transform(quarterly_earnings)
        >>> print(ttm_data.iloc[3:])  # First 3 periods will be NaN
        #             net_income
        # 2023-03-31       130.0
        # 2023-06-30       150.0
        # 2023-09-30       170.0
        # 2023-12-31       190.0
        # 2024-03-31       210.0

    Note:
        - The resulting index format depends on the conversion type
        - Annual conversions group by year (integer index)
        - Quarterly conversions group by (year, quarter) tuple
        - TTM conversions maintain the original datetime index
        - Ensure your aggregation method matches the financial item type
    """

    # All valid conversion types
    CONVERSION_TYPES: ClassVar[list[str]] = [t.value for t in ConversionType]

    def __init__(
        self,
        conversion_type: str | ConversionType = ConversionType.QUARTERLY_TO_ANNUAL,
        aggregation: str = "sum",
        *,
        config: PeriodConversionConfig | None = None,
    ):
        """Initialize the period conversion transformer.

        Args:
            conversion_type: Type of period conversion to apply. Can be either
                a string or ConversionType enum value:
                - 'quarterly_to_annual': Convert 4 quarters to 1 year
                - 'monthly_to_quarterly': Convert 3 months to 1 quarter
                - 'monthly_to_annual': Convert 12 months to 1 year
                - 'quarterly_to_ttm': Calculate trailing twelve months
            aggregation: How to aggregate data within each period:
                - 'sum': Add up all values (default) - for flow items
                - 'mean': Calculate average - for rates/ratios
                - 'last': Take last value - for balance sheet items
                - 'first': Take first value - for opening balances
                - 'max': Take maximum value
                - 'min': Take minimum value
                - 'std': Calculate standard deviation
                - 'count': Count non-null values
            config: Optional PeriodConversionConfig object containing configuration.
                If provided, overrides other parameters.

        Raises:
            ValueError: If conversion_type is invalid.

        Examples:
            >>> # Annual totals from quarterly data
            >>> converter = PeriodConversionTransformer("quarterly_to_annual", "sum")
            >>>
            >>> # Quarter-end balances from monthly data
            >>> converter = PeriodConversionTransformer("monthly_to_quarterly", "last")
            >>>
            >>> # TTM revenue from quarterly data
            >>> converter = PeriodConversionTransformer("quarterly_to_ttm", "sum")
        """
        if config is not None and aggregation != "sum":
            warnings.warn(
                "Both 'config' and individual kwargs supplied to PeriodConversionTransformer; the Pydantic config takes precedence.",
                UserWarning,
                stacklevel=2,
            )

        if config is not None:
            conversion_type = config.conversion_type or conversion_type
            aggregation = config.aggregation or aggregation

        # Normalize enum to string
        ctype = conversion_type.value if isinstance(conversion_type, ConversionType) else conversion_type
        if ctype not in self.CONVERSION_TYPES:
            raise ValueError(f"Invalid conversion type: {ctype}. Must be one of {self.CONVERSION_TYPES}")
        self.conversion_type = ctype
        self.aggregation = aggregation

        super().__init__(config.model_dump() if config else None)

    def transform(self, data: pd.DataFrame | pd.Series[Any]) -> pd.DataFrame | pd.Series[Any]:
        """Transform data by converting between period types.

        Args:
            data: DataFrame with time-based data to convert. Must have either:
                - A DatetimeIndex
                - An index containing date/time strings parsable by pd.to_datetime
                - Period labels that can be converted to datetime

                The data frequency should match the source period type (e.g.,
                quarterly data for 'quarterly_to_annual' conversion).

        Returns:
            DataFrame with converted periods:
            - For annual conversions: Index will be years (integers)
            - For quarterly conversions: Index will be (year, quarter) tuples
            - For TTM conversions: Original datetime index is preserved

            All columns are aggregated according to the specified method.

        Raises:
            TypeError: If data is not a pandas DataFrame or Series.
            ValueError: If index cannot be converted to datetime or if
                aggregation='sum' is used with 'quarterly_to_ttm' and a
                different aggregation method is specified.

        Examples:
            >>> # Convert quarterly data to annual
            >>> df = pd.DataFrame(
            ...     {"revenue": [100, 110, 120, 130], "costs": [60, 65, 70, 75]},
            ...     index=["2023-Q1", "2023-Q2", "2023-Q3", "2023-Q4"],
            ... )
            >>>
            >>> converter = PeriodConversionTransformer("quarterly_to_annual")
            >>> annual = converter.transform(df)
            >>> print(annual)
            #       revenue  costs
            # 2023      460    270
        """
        if not isinstance(data, pd.DataFrame | pd.Series):
            raise TypeError("Period conversion requires a pandas DataFrame or Series")

        return super().transform(data)

    def _transform_impl(self, data: pd.DataFrame | pd.Series[Any]) -> pd.DataFrame | pd.Series[Any]:
        """Apply the period conversion transformation.

        This is the core implementation method that handles both DataFrame
        and Series inputs by converting Series to single-column DataFrames,
        applying the period conversion, and converting back if needed.

        Args:
            data: The data to transform. Can be either:
                - pandas.DataFrame: For multi-column period conversion
                - pandas.Series: For single-column period conversion

        Returns:
            The transformed data in the same format as the input
            (DataFrame → DataFrame, Series → Series).

        Raises:
            DataValidationError: If data is not a DataFrame or Series.
            ValueError: If period conversion fails due to:
                - Invalid index format
                - Unsupported aggregation method for TTM
                - Other conversion-specific issues

        Examples:
            >>> transformer = PeriodConversionTransformer(conversion_type="quarterly_to_annual", aggregation="sum")
            >>> df = pd.DataFrame(
            ...     {"revenue": [100, 110, 120, 130], "costs": [60, 65, 70, 75]},
            ...     index=pd.date_range("2023-01-01", periods=4, freq="Q"),
            ... )
            >>> result = transformer._transform_impl(df)
            >>> series = pd.Series(
            ...     [100, 110, 120, 130], index=pd.date_range("2023-01-01", periods=4, freq="Q"), name="revenue"
            ... )
            >>> result_series = transformer._transform_impl(series)
        """
        if not isinstance(data, pd.DataFrame | pd.Series):
            raise DataValidationError(
                "Period conversion requires a pandas DataFrame or Series",
                validation_errors=[f"Got type: {type(data).__name__}"],
            )

        df, was_series = self._coerce_to_dataframe(data)
        result_df = self._convert_periods(df)
        if was_series:
            return result_df.iloc[:, 0]
        return result_df

    def _convert_periods(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply period conversion to a DataFrame.

        This method implements the core period conversion logic by:
        1. Ensuring the index is in datetime format
        2. Dispatching to the appropriate conversion method
        3. Handling any conversion-specific requirements

        Args:
            df: DataFrame to convert. Must have:
                - An index that can be converted to datetime
                - Data frequency matching the source period type
                - Numeric columns for aggregation

        Returns:
            Converted DataFrame with:
                - New period-based index (format depends on conversion)
                - Original column names preserved
                - Values aggregated according to configuration

        Raises:
            ValueError: If:
                - DataFrame index cannot be converted to datetime
                - TTM conversion is requested with unsupported aggregation
            NotImplementedError: If conversion_type is not supported

        Examples:
            >>> df = pd.DataFrame(
            ...     {"revenue": [100, 110, 120, 130], "costs": [60, 65, 70, 75]},
            ...     index=["2023-Q1", "2023-Q2", "2023-Q3", "2023-Q4"],
            ... )
            >>> transformer = PeriodConversionTransformer("quarterly_to_annual")
            >>> result = transformer._convert_periods(df)
            >>> print(result)
            #       revenue  costs
            # 2023      460    270

        Notes:
            - The output index format varies by conversion type:
                - Annual: Integer year (e.g., 2023)
                - Quarterly: (year, quarter) tuple (e.g., (2023, 1))
                - TTM: Original datetime preserved
            - Aggregation method should match the financial metric type:
                - Flow measures (revenue): Use 'sum'
                - Point-in-time (balance sheet): Use 'last'
                - Rates/ratios: Consider 'mean'
        """
        df_copy = self._ensure_datetime_index(df)

        dispatch: dict[str, Callable[[pd.DataFrame], pd.DataFrame]] = {
            ConversionType.QUARTERLY_TO_ANNUAL.value: self._quarterly_to_annual,
            ConversionType.MONTHLY_TO_QUARTERLY.value: self._monthly_to_quarterly,
            ConversionType.MONTHLY_TO_ANNUAL.value: self._monthly_to_annual,
            ConversionType.QUARTERLY_TO_TTM.value: self._quarterly_to_ttm,
        }

        try:
            return dispatch[self.conversion_type](df_copy)
        except KeyError as exc:
            raise NotImplementedError(f"Conversion type '{self.conversion_type}' is not implemented.") from exc

    def _ensure_datetime_index(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return *df* with a DatetimeIndex, converting if required.

        This helper method ensures the DataFrame has a proper datetime index
        by attempting to convert string-based or period-based indices to
        datetime format.

        Args:
            df: DataFrame whose index needs to be in datetime format.
                The index can be:
                - Already a DatetimeIndex (no conversion needed)
                - String dates (e.g., '2023-01-31', '2023-Q1')
                - Period labels that pandas can parse

        Returns:
            DataFrame with DatetimeIndex, preserving the original data

        Raises:
            ValueError: If the index cannot be converted to datetime format

        Examples:
            >>> df = pd.DataFrame({"value": [1, 2]}, index=["2023-01", "2023-02"])
            >>> transformer = PeriodConversionTransformer()
            >>> result = transformer._ensure_datetime_index(df)
            >>> isinstance(result.index, pd.DatetimeIndex)
            True

        Notes:
            - The method attempts to use pd.to_datetime for conversion
            - Logs debug message on successful conversion
            - Logs exception details if conversion fails
            - Returns a copy of the DataFrame to avoid modifying the original
        """
        if isinstance(df.index, pd.DatetimeIndex):
            return df

        df_conv = df.copy()
        try:
            df_conv.index = pd.to_datetime(df_conv.index)
            logger.debug("Successfully converted DataFrame index to DatetimeIndex.")
        except Exception as exc:
            logger.exception(
                "Failed to convert DataFrame index to DatetimeIndex. Ensure index contains standard date/time strings or is already a DatetimeIndex."
            )
            raise ValueError("Index must be convertible to datetime for period conversion") from exc
        else:
            return df_conv

    def _quarterly_to_annual(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate 4 quarters into annual periods using configured aggregation.

        This method converts quarterly data to annual by:
        1. Grouping data by year
        2. Applying the configured aggregation method
        3. Returning a DataFrame with integer year index

        Args:
            df: DataFrame with quarterly data (DatetimeIndex)

        Returns:
            DataFrame with annual data and integer year index

        Examples:
            >>> df = pd.DataFrame(
            ...     {"revenue": [100, 110, 120, 130]}, index=pd.date_range("2023-01-01", periods=4, freq="Q")
            ... )
            >>> transformer = PeriodConversionTransformer("quarterly_to_annual")
            >>> result = transformer._quarterly_to_annual(df)
            >>> print(result)
            #       revenue
            # 2023      460
        """
        return cast("pd.DataFrame", resample_to_period(df, Period.YEAR, aggregation=self.aggregation))

    def _monthly_to_quarterly(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate 3 months into quarterly periods.

        This method converts monthly data to quarterly by:
        1. Resampling to quarterly frequency
        2. Applying the configured aggregation method
        3. Converting the index to (year, quarter) tuples

        Args:
            df: DataFrame with monthly data (DatetimeIndex)

        Returns:
            DataFrame with quarterly data and (year, quarter) tuple index

        Examples:
            >>> df = pd.DataFrame(
            ...     {"value": [10, 20, 30, 40, 50, 60]}, index=pd.date_range("2023-01-31", periods=6, freq="M")
            ... )
            >>> transformer = PeriodConversionTransformer("monthly_to_quarterly")
            >>> result = transformer._monthly_to_quarterly(df)
            >>> print(result)
            #              value
            # (2023, 1)      60
            # (2023, 2)     150
        """
        resampled = cast("pd.DataFrame", resample_to_period(df, Period.QUARTER, aggregation=self.aggregation))
        # Convert DatetimeIndex to (year, quarter) tuples for backward-compatibility.
        resampled.index = pd.Index([(ts.year, ts.quarter) for ts in resampled.index])
        return resampled

    def _monthly_to_annual(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate monthly data into annual periods.

        This method converts monthly data to annual by:
        1. Grouping data by year
        2. Applying the configured aggregation method
        3. Returning a DataFrame with integer year index

        Args:
            df: DataFrame with monthly data (DatetimeIndex)

        Returns:
            DataFrame with annual data and integer year index

        Examples:
            >>> df = pd.DataFrame(
            ...     {"value": [10, 20, 30, 40, 50, 60]}, index=pd.date_range("2023-01-31", periods=6, freq="M")
            ... )
            >>> transformer = PeriodConversionTransformer("monthly_to_annual")
            >>> result = transformer._monthly_to_annual(df)
            >>> print(result)
            #       value
            # 2023    210
        """
        return cast("pd.DataFrame", resample_to_period(df, Period.YEAR, aggregation=self.aggregation))

    def _quarterly_to_ttm(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute trailing-twelve-months (rolling 4-quarter sum).

        This method calculates TTM values by:
        1. Creating a 4-quarter rolling window
        2. Summing values within each window
        3. Preserving the original datetime index

        Args:
            df: DataFrame with quarterly data (DatetimeIndex)

        Returns:
            DataFrame with TTM values and original datetime index.
            The first 3 quarters will be NaN (insufficient data for TTM).

        Raises:
            ValueError: If aggregation method is not 'sum'
                (TTM requires summing quarters)

        Examples:
            >>> df = pd.DataFrame(
            ...     {"revenue": [100, 110, 120, 130, 140, 150]}, index=pd.date_range("2023-01-01", periods=6, freq="Q")
            ... )
            >>> transformer = PeriodConversionTransformer("quarterly_to_ttm")
            >>> result = transformer._quarterly_to_ttm(df)
            >>> print(result.iloc[3:])  # Skip first 3 NaN periods
            #             revenue
            # 2023-12-31    460.0
            # 2024-03-31    500.0
            # 2024-06-30    540.0

        Notes:
            - Only 'sum' aggregation is supported (TTM is always a sum)
            - First 3 quarters will be NaN (need 4 quarters for TTM)
            - Original datetime index is preserved
        """
        if self.aggregation != "sum":
            raise ValueError("QUARTERLY_TO_TTM currently supports only 'sum' aggregation.")
        return df.rolling(window=4, min_periods=4).sum()

    def validate_input(self, data: object) -> bool:
        """Accept pandas DataFrame or Series.

        This method implements the DataTransformer contract by specifying
        exactly which input types are supported by the period conversion
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
            >>> transformer = PeriodConversionTransformer()
            >>> transformer.validate_input(pd.DataFrame())
            True
            >>> transformer.validate_input(pd.Series())
            True
            >>> transformer.validate_input([1, 2, 3])
            False
        """
        return isinstance(data, pd.DataFrame | pd.Series)
