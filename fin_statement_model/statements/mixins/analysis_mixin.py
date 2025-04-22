"""Analysis mixin module for FinancialStatementGraph operations."""

from typing import Optional
import pandas as pd


class AnalysisOperationsMixin:
    """Mixin providing analysis methods for FinancialStatementGraph.

    - normalize_data
    - analyze_time_series
    - convert_periods.
    """

    def normalize_data(
        self,
        normalization_type: str = "percent_of",
        reference: Optional[str] = None,
        scale_factor: Optional[float] = None,
    ) -> pd.DataFrame:
        """Normalize the financial statement data."""
        df = self.to_dataframe()
        return self._transformation_service.normalize_data(
            df, normalization_type, reference, scale_factor
        )

    def analyze_time_series(
        self,
        transformation_type: str = "growth_rate",
        periods: int = 1,
        window_size: int = 3,
    ) -> pd.DataFrame:
        """Apply time series preprocessing to the financial data."""
        df = self.to_dataframe()
        return self._transformation_service.transform_time_series(
            df, transformation_type, periods, window_size
        )

    def convert_periods(
        self,
        conversion_type: str,
        aggregation: str = "sum",
    ) -> pd.DataFrame:
        """Convert data between different period types."""
        df = self.to_dataframe()
        return self._transformation_service.convert_periods(df, conversion_type, aggregation)
