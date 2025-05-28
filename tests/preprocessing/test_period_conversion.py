"""Tests for the PeriodConversionTransformer."""

import pandas as pd
import pytest

from fin_statement_model.preprocessing.transformers.period_conversion import (
    PeriodConversionTransformer,
)
from fin_statement_model.preprocessing.config.enums import ConversionType


class TestPeriodConversionTransformer:
    """Test cases for PeriodConversionTransformer."""

    def test_quarterly_to_ttm(self):
        """Test quarterly to TTM conversion."""
        # Create quarterly data
        dates = pd.date_range("2020-01-01", periods=8, freq="QE")
        df = pd.DataFrame(
            {
                "revenue": [100, 110, 120, 130, 140, 150, 160, 170],
                "costs": [50, 55, 60, 65, 70, 75, 80, 85],
            },
            index=dates,
        )

        transformer = PeriodConversionTransformer(
            conversion_type=ConversionType.QUARTERLY_TO_TTM, aggregation="sum"
        )

        result = transformer.transform(df)

        # First 3 quarters should be NaN (min_periods=4)
        assert pd.isna(result.iloc[0]["revenue"])
        assert pd.isna(result.iloc[1]["revenue"])
        assert pd.isna(result.iloc[2]["revenue"])

        # Fourth quarter should be sum of first 4 quarters
        assert result.iloc[3]["revenue"] == 460  # 100 + 110 + 120 + 130
        assert result.iloc[3]["costs"] == 230  # 50 + 55 + 60 + 65

        # Fifth quarter should be sum of quarters 2-5
        assert result.iloc[4]["revenue"] == 500  # 110 + 120 + 130 + 140
        assert result.iloc[4]["costs"] == 250  # 55 + 60 + 65 + 70

    def test_quarterly_to_ttm_non_sum_aggregation(self):
        """Test that non-sum aggregation raises ValueError for TTM."""
        df = pd.DataFrame(
            {"revenue": [100, 110, 120, 130]},
            index=pd.date_range("2020-01-01", periods=4, freq="QE"),
        )

        transformer = PeriodConversionTransformer(
            conversion_type=ConversionType.QUARTERLY_TO_TTM, aggregation="mean"
        )

        with pytest.raises(
            ValueError,
            match="QUARTERLY_TO_TTM conversion currently only supports 'sum' aggregation",
        ):
            transformer.transform(df)

    def test_invalid_index_conversion(self):
        """Test that invalid index raises appropriate error."""
        df = pd.DataFrame(
            {"revenue": [100, 110, 120, 130]},
            index=["invalid", "date", "strings", "here"],
        )

        transformer = PeriodConversionTransformer(
            conversion_type=ConversionType.QUARTERLY_TO_ANNUAL
        )

        with pytest.raises(ValueError, match="Index must be convertible to datetime"):
            transformer.transform(df)

    def test_unimplemented_conversion_type(self):
        """Test that using an undefined conversion type raises NotImplementedError."""
        # This test would only work if we manually set an invalid conversion type
        # after initialization, which shouldn't happen in normal usage
        df = pd.DataFrame(
            {"revenue": [100, 110, 120, 130]},
            index=pd.date_range("2020-01-01", periods=4, freq="QE"),
        )

        transformer = PeriodConversionTransformer(
            conversion_type=ConversionType.QUARTERLY_TO_ANNUAL
        )

        # Manually set an invalid conversion type to test the else clause
        transformer.conversion_type = "invalid_conversion_type"

        with pytest.raises(
            NotImplementedError,
            match="Conversion type 'invalid_conversion_type' is defined in ConversionType enum but not implemented",
        ):
            transformer.transform(df)
