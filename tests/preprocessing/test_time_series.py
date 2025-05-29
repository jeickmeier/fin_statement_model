"""Tests for the TimeSeriesTransformer."""

import pandas as pd
import pytest

from fin_statement_model.preprocessing.transformers.time_series import (
    TimeSeriesTransformer,
)
from fin_statement_model.preprocessing.config.enums import TransformationType


class TestTimeSeriesTransformer:
    """Test cases for TimeSeriesTransformer."""

    def test_cagr_with_zero_start_value(self):
        """Test CAGR calculation handles zero start values correctly."""
        df = pd.DataFrame(
            {
                "revenue": [0, 100, 200, 300],
                "costs": [50, 60, 70, 80],
            }
        )

        transformer = TimeSeriesTransformer(transformation_type=TransformationType.CAGR)

        result = transformer.transform(df)

        # Revenue CAGR should be pd.NA due to zero start value
        assert pd.isna(result["revenue_cagr"].iloc[-1])

        # Costs CAGR should be calculated normally
        # (80/50)^(1/3) - 1 = 0.1699... * 100 ≈ 16.99%
        assert not pd.isna(result["costs_cagr"].iloc[-1])
        assert abs(result["costs_cagr"].iloc[-1] - 16.99) < 0.1

    def test_cagr_with_negative_values(self):
        """Test CAGR calculation handles negative values correctly."""
        df = pd.DataFrame(
            {
                "profit": [-100, -50, 25, 100],  # Negative to positive
                "loss": [100, 50, -25, -100],  # Positive to negative
            }
        )

        transformer = TimeSeriesTransformer(transformation_type=TransformationType.CAGR)

        result = transformer.transform(df)

        # Both should result in pd.NA due to negative ratios with fractional exponents
        assert pd.isna(result["profit_cagr"].iloc[-1])
        assert pd.isna(result["loss_cagr"].iloc[-1])

    def test_cagr_with_insufficient_periods(self):
        """Test CAGR calculation with less than 2 periods."""
        df = pd.DataFrame(
            {
                "revenue": [100],  # Only one period
            }
        )

        transformer = TimeSeriesTransformer(transformation_type=TransformationType.CAGR)

        result = transformer.transform(df)

        # Should return pd.NA for insufficient periods
        assert pd.isna(result["revenue_cagr"].iloc[0])

    def test_yoy_with_custom_periods(self):
        """Test YoY transformation uses the periods parameter."""
        # Create quarterly data
        dates = pd.date_range("2020-01-01", periods=8, freq="QE")
        df = pd.DataFrame(
            {
                "revenue": [100, 110, 120, 130, 140, 150, 160, 170],
            },
            index=dates,
        )

        # Test with periods=4 (quarterly YoY)
        transformer = TimeSeriesTransformer(
            transformation_type=TransformationType.YOY, periods=4
        )

        result = transformer.transform(df)

        # First 4 periods should be NaN
        assert all(pd.isna(result["revenue_yoy"].iloc[:4]))

        # Fifth period should be (140-100)/100 * 100 = 40%
        assert abs(result["revenue_yoy"].iloc[4] - 40.0) < 0.01

    def test_qoq_with_custom_periods(self):
        """Test QoQ transformation uses the periods parameter."""
        # Create quarterly data
        dates = pd.date_range("2020-01-01", periods=4, freq="QE")
        df = pd.DataFrame(
            {
                "revenue": [100, 110, 120, 130],
            },
            index=dates,
        )

        # Test with periods=1 (quarterly QoQ)
        transformer = TimeSeriesTransformer(
            transformation_type=TransformationType.QOQ, periods=1
        )

        result = transformer.transform(df)

        # First period should be NaN
        assert pd.isna(result["revenue_qoq"].iloc[0])

        # Second period should be (110-100)/100 * 100 = 10%
        assert abs(result["revenue_qoq"].iloc[1] - 10.0) < 0.01

    def test_yoy_warning_for_unusual_periods(self):
        """Test that YoY logs warning for unusual period values."""
        df = pd.DataFrame(
            {
                "revenue": [100, 110, 120, 130],
            }
        )

        # Using periods=2 (unusual for YoY)
        transformer = TimeSeriesTransformer(
            transformation_type=TransformationType.YOY, periods=2
        )

        # Should not raise error, just log warning
        result = transformer.transform(df)
        assert "revenue_yoy" in result.columns

    def test_unimplemented_transformation_type(self):
        """Test that undefined transformation type raises NotImplementedError."""
        df = pd.DataFrame(
            {
                "revenue": [100, 110, 120, 130],
            }
        )

        transformer = TimeSeriesTransformer(
            transformation_type=TransformationType.GROWTH_RATE
        )

        # Manually set an invalid transformation type
        transformer.transformation_type = "invalid_transformation"

        with pytest.raises(
            NotImplementedError,
            match="Transformation type 'invalid_transformation' is defined in TransformationType enum but not implemented",
        ):
            transformer.transform(df)
