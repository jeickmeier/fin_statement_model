from __future__ import annotations

"""Tests for PeriodConversionTransformer and period helper utilities."""

import pandas as pd
import pytest

from fin_statement_model.preprocessing.transformers.period_conversion import (
    PeriodConversionTransformer,
)
from fin_statement_model.preprocessing.periods import Period, resample_to_period
from fin_statement_model.core.errors import TransformationError


# ----------------------------------------------------------------------------
# Helper DataFrames
# ----------------------------------------------------------------------------


def _make_quarterly_df():
    return pd.DataFrame(
        {"val": [100, 110, 120, 130]},
        index=pd.date_range("2023-03-31", periods=4, freq="Q"),
    )


def _make_monthly_df():
    return pd.DataFrame(
        {"val": [10, 12, 14]}, index=pd.date_range("2023-01-31", periods=3, freq="M")
    )


# ----------------------------------------------------------------------------
# quarterly_to_annual sum
# ----------------------------------------------------------------------------


def test_quarterly_to_annual_sum() -> None:
    df_q = _make_quarterly_df()
    conv = PeriodConversionTransformer("quarterly_to_annual", aggregation="sum")
    out = conv.transform(df_q)
    # One annual row, value equal to sum of quarters; index is datetime year-end
    assert out.iloc[0, 0] == 460


def test_monthly_to_quarterly_last() -> None:
    df_m = _make_monthly_df()
    conv = PeriodConversionTransformer("monthly_to_quarterly", aggregation="last")
    out = conv.transform(df_m)
    # Index tuples (year, quarter)
    assert out.index[0] == (2023, 1)
    assert out.iloc[0, 0] == 14


def test_quarterly_to_ttm_invalid_agg() -> None:
    df_q = _make_quarterly_df()
    # aggregation other than sum should error
    with pytest.raises(TransformationError):
        PeriodConversionTransformer("quarterly_to_ttm", aggregation="mean").transform(
            df_q
        )


# ----------------------------------------------------------------------------
# resample_to_period utility
# ----------------------------------------------------------------------------


def test_resample_to_period_mean() -> None:
    df = pd.DataFrame(
        {"v": [1, 2, 3]}, index=pd.date_range("2023-01-31", periods=3, freq="M")
    )
    annual = resample_to_period(df, Period.YEAR, aggregation="mean")
    assert annual.iloc[0, 0] == pytest.approx(2.0)
