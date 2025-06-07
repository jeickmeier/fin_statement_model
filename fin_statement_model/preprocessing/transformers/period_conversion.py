"""Financial data transformers for the Financial Statement Model.

This module provides the PeriodConversionTransformer for converting between period types:
quarterly_to_annual, monthly_to_quarterly, monthly_to_annual, and quarterly_to_ttm.
"""

import logging
import pandas as pd
from typing import Optional, Union, ClassVar

from fin_statement_model.preprocessing.base_transformer import DataTransformer
from fin_statement_model.preprocessing.config import (
    ConversionType,
    PeriodConversionConfig,
)
from fin_statement_model.core.errors import DataValidationError

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
        >>> quarterly_data = pd.DataFrame({
        ...     'revenue': [100, 110, 120, 130, 140, 150, 160, 170],
        ...     'expenses': [80, 85, 90, 95, 100, 105, 110, 115]
        ... }, index=pd.date_range('2022-03-31', periods=8, freq='Q'))
        >>>
        >>> # Convert to annual data (sum 4 quarters)
        >>> annual_converter = PeriodConversionTransformer(
        ...     conversion_type='quarterly_to_annual',
        ...     aggregation='sum'
        ... )
        >>> annual_data = annual_converter.transform(quarterly_data)
        >>> print(annual_data)
        #       revenue  expenses
        # 2022      460       350
        # 2023      620       430

        Convert monthly balance sheet to quarterly (taking last value):

        >>> # Monthly balance sheet data
        >>> monthly_bs = pd.DataFrame({
        ...     'total_assets': [1000, 1020, 1050, 1080, 1100, 1150],
        ...     'total_equity': [600, 610, 620, 630, 640, 650]
        ... }, index=pd.date_range('2023-01-31', periods=6, freq='M'))
        >>>
        >>> # Convert to quarterly, taking last month's value
        >>> quarterly_converter = PeriodConversionTransformer(
        ...     conversion_type='monthly_to_quarterly',
        ...     aggregation='last'
        ... )
        >>> quarterly_bs = quarterly_converter.transform(monthly_bs)
        >>> print(quarterly_bs)
        #                  total_assets  total_equity
        # (2023, 1)              1050           620
        # (2023, 2)              1150           650

        Calculate trailing twelve months (TTM) from quarterly data:

        >>> # Quarterly earnings data
        >>> quarterly_earnings = pd.DataFrame({
        ...     'net_income': [25, 30, 35, 40, 45, 50, 55, 60]
        ... }, index=pd.date_range('2022-03-31', periods=8, freq='Q'))
        >>>
        >>> # Calculate TTM (rolling 4-quarter sum)
        >>> ttm_converter = PeriodConversionTransformer(
        ...     conversion_type='quarterly_to_ttm',
        ...     aggregation='sum'
        ... )
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
        conversion_type: Union[
            str, ConversionType
        ] = ConversionType.QUARTERLY_TO_ANNUAL,
        aggregation: str = "sum",
        config: Optional[PeriodConversionConfig] = None,
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
            >>> converter = PeriodConversionTransformer('quarterly_to_annual', 'sum')
            >>>
            >>> # Quarter-end balances from monthly data
            >>> converter = PeriodConversionTransformer('monthly_to_quarterly', 'last')
            >>>
            >>> # TTM revenue from quarterly data
            >>> converter = PeriodConversionTransformer('quarterly_to_ttm', 'sum')
        """
        super().__init__(config.model_dump() if config else None)
        # Normalize enum to string
        if isinstance(conversion_type, ConversionType):
            ctype = conversion_type.value
        else:
            ctype = conversion_type
        if ctype not in self.CONVERSION_TYPES:
            raise ValueError(
                f"Invalid conversion type: {ctype}. Must be one of {self.CONVERSION_TYPES}"
            )
        self.conversion_type = ctype
        self.aggregation = aggregation

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
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
            TypeError: If data is not a pandas DataFrame.
            ValueError: If index cannot be converted to datetime or if
                aggregation='sum' is used with 'quarterly_to_ttm' and a
                different aggregation method is specified.

        Examples:
            >>> # Convert quarterly data to annual
            >>> df = pd.DataFrame({
            ...     'revenue': [100, 110, 120, 130],
            ...     'costs': [60, 65, 70, 75]
            ... }, index=['2023-Q1', '2023-Q2', '2023-Q3', '2023-Q4'])
            >>>
            >>> converter = PeriodConversionTransformer('quarterly_to_annual')
            >>> annual = converter.transform(df)
            >>> print(annual)
            #       revenue  costs
            # 2023      460    270
        """
        # Ensure we have a DataFrame
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Period conversion requires a pandas DataFrame")

        return super().transform(data)

    def _transform_impl(
        self, data: Union[pd.DataFrame, pd.Series]
    ) -> Union[pd.DataFrame, pd.Series]:
        """Apply the period conversion transformation.

        Args:
            data: The data to transform.

        Returns:
            The transformed data.

        Raises:
            DataValidationError: If data is not a DataFrame or Series.
            ValueError: If conversion fails.
        """
        if not isinstance(data, pd.DataFrame | pd.Series):
            raise DataValidationError(
                "Period conversion requires a pandas DataFrame or Series",
                validation_errors=[f"Got type: {type(data).__name__}"],
            )

        # Handle Series by converting to DataFrame temporarily
        if isinstance(data, pd.Series):
            temp_df = data.to_frame()
            result_df = self._convert_periods(temp_df)
            return result_df.iloc[:, 0]  # Return as Series
        else:
            return self._convert_periods(data)

    def _convert_periods(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply period conversion to a DataFrame.

        Args:
            df: DataFrame to convert.

        Returns:
            Converted DataFrame.
        """
        df_copy = df.copy()

        # Try to convert index to datetime if it's not already
        if not isinstance(df_copy.index, pd.DatetimeIndex):
            try:
                df_copy.index = pd.to_datetime(df_copy.index)
                logger.debug("Successfully converted DataFrame index to DatetimeIndex.")
            except Exception as e:
                logger.exception(
                    "Failed to convert DataFrame index to DatetimeIndex. Ensure index contains standard date/time strings or is already a DatetimeIndex."
                )
                raise ValueError(
                    f"Index must be convertible to datetime for period conversion: {e}"
                )

        if self.conversion_type == ConversionType.QUARTERLY_TO_ANNUAL.value:
            # Group by year and aggregate
            return df_copy.groupby(df_copy.index.year).agg(self.aggregation)

        elif self.conversion_type == ConversionType.MONTHLY_TO_QUARTERLY.value:
            # Group by year and quarter
            return df_copy.groupby([df_copy.index.year, df_copy.index.quarter]).agg(
                self.aggregation
            )

        elif self.conversion_type == ConversionType.MONTHLY_TO_ANNUAL.value:
            # Group by year
            return df_copy.groupby(df_copy.index.year).agg(self.aggregation)

        elif self.conversion_type == ConversionType.QUARTERLY_TO_TTM.value:
            # Implement TTM as rolling sum with window=4 for quarterly data
            if self.aggregation == "sum":
                return df_copy.rolling(window=4, min_periods=4).sum()
            else:
                # For other aggregation methods, we need custom logic
                raise ValueError(
                    "QUARTERLY_TO_TTM conversion currently only supports 'sum' aggregation for TTM. "
                    "TTM typically represents the sum of the last 4 quarters for flow items like revenue."
                )
        else:
            raise NotImplementedError(
                f"Conversion type '{self.conversion_type}' is defined in ConversionType enum but not implemented in PeriodConversionTransformer."
            )
