"""Unit tests for TimeSeriesTransformer helper-dispatched transformations.

These tests exercise the public behaviour of the transformer after the
refactor that extracted per-operation helpers.
"""

from __future__ import annotations

import pandas as pd
import pytest

from fin_statement_model.preprocessing.transformers import TimeSeriesTransformer


@pytest.fixture()
def sample_df() -> pd.DataFrame:
    """Return small time-series DataFrame for testing."""
    return pd.DataFrame(
        {
            "revenue": [100, 110, 121, 133.1],
            "costs": [50, 55, 60.5, 66.55],
        },
        index=pd.date_range("2023-01-31", periods=4, freq="ME"),
    )


def test_growth_rate(sample_df: pd.DataFrame) -> None:
    """Growth-rate columns should be added and contain pct values."""
    transformer = TimeSeriesTransformer("growth_rate", periods=1)
    result = transformer.transform(sample_df)

    for col in ["revenue", "costs"]:
        growth_col = f"{col}_growth"
        assert growth_col in result.columns
        # First value should be NaN; second should be 10 %
        assert pytest.approx(result[growth_col].iloc[1], rel=1e-3) == 10.0


def test_moving_average(sample_df: pd.DataFrame) -> None:
    """Moving-average columns should be added with correct window size."""
    transformer = TimeSeriesTransformer("moving_avg", window_size=2)
    result = transformer.transform(sample_df)

    assert "revenue_ma2" in result.columns
    # Third value is mean of 110 & 121 = 115.5
    assert pytest.approx(result["revenue_ma2"].iloc[2], rel=1e-3) == 115.5
