"""Financial data transformers for the Financial Statement Model.

This module provides the PeriodConversionTransformer for converting between period types:
quarterly_to_annual, monthly_to_quarterly, monthly_to_annual, and annual_to_ttm.
"""

import pandas as pd
from typing import Optional, Union, ClassVar

from fin_statement_model.preprocessing.base_transformer import DataTransformer
from fin_statement_model.preprocessing.types import PeriodConversionConfig
from fin_statement_model.preprocessing.enums import ConversionType

# Configure logging


class PeriodConversionTransformer(DataTransformer):
    """Transformer for converting between different period types.

    This transformer can convert:
    - Quarterly data to annual
    - Monthly data to quarterly or annual
    - Annual data to trailing twelve months (TTM)
    """

    # All valid conversion types
    CONVERSION_TYPES: ClassVar[list[str]] = [t.value for t in ConversionType]

    def __init__(
        self,
        conversion_type: Union[str, ConversionType] = ConversionType.QUARTERLY_TO_ANNUAL,
        aggregation: str = "sum",
        config: Optional[PeriodConversionConfig] = None,
    ):
        """Initialize the period conversion transformer.

        Args:
            conversion_type: Type of period conversion to apply (enum or string)
            aggregation: How to aggregate data (sum, mean, last, etc.)
            config: Optional transformer configuration
        """
        super().__init__(config)
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
            data: DataFrame with DatetimeIndex or period labels in the index

        Returns:
            DataFrame with transformed periods
        """
        # Ensure we have a DataFrame
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Period conversion requires a pandas DataFrame")

        # Try to convert index to datetime if it's not already
        if not isinstance(data.index, pd.DatetimeIndex):
            try:
                data = data.copy()
                data.index = pd.to_datetime(data.index, format="%Y-%m-%d")
            except Exception:
                raise ValueError("Index must be convertible to datetime for period conversion")

        if self.conversion_type == ConversionType.QUARTERLY_TO_ANNUAL.value:
            # Group by year and aggregate
            return data.groupby(data.index.year).agg(self.aggregation)

        elif self.conversion_type == ConversionType.MONTHLY_TO_QUARTERLY.value:
            # Group by year and quarter
            return data.groupby([data.index.year, data.index.quarter]).agg(self.aggregation)

        elif self.conversion_type == ConversionType.MONTHLY_TO_ANNUAL.value:
            # Group by year
            return data.groupby(data.index.year).agg(self.aggregation)

        elif self.conversion_type == ConversionType.ANNUAL_TO_TTM.value:
            # Implement TTM as rolling sum with window=4 for quarterly data
            if self.aggregation == "sum":
                return data.rolling(window=4).sum()
            else:
                # For other aggregation methods, we need custom logic
                raise ValueError("annual_to_ttm conversion only supports 'sum' aggregation")

        return data  # pragma: no cover
