from __future__ import annotations

import pandas as pd
import pytest

from fin_statement_model.preprocessing.periods import (
    Period,
    quarter_to_months,
    month_to_quarter,
    resample_to_period,
)


def test_period_enum_conversions():
    assert Period.MONTH.to_months == 1
    assert Period.QUARTER.to_years == 0.25
    assert Period.infer_from_offset("me") is Period.MONTH
    assert Period.infer_from_offset("qe") is Period.QUARTER
    with pytest.raises(ValueError):
        Period.infer_from_offset("w")


def test_quarter_month_helpers():
    months = quarter_to_months(2024, 3)
    # Expect June-ending quarter month list length 3
    assert len(months) == 3 and months[0].year == 2024

    ts = pd.Timestamp("2024-05-31")
    y, q = month_to_quarter(ts)
    assert (y, q) == (2024, 2)

    with pytest.raises(ValueError):
        quarter_to_months(2024, 5)


def test_resample_to_period_aggregations():
    idx = pd.date_range("2023-01-31", periods=12, freq="M")
    df = pd.DataFrame({"v": range(1, 13)}, index=idx)

    # Sum to year
    annual = resample_to_period(df, Period.YEAR, aggregation="sum")
    assert annual.iloc[0, 0] == sum(range(1, 13))

    # Mean quarterly
    quarterly = resample_to_period(df, Period.QUARTER, aggregation="mean")
    assert quarterly.iloc[0, 0] == pytest.approx((1 + 2 + 3) / 3)

    # Unsupported aggregation
    with pytest.raises(ValueError):
        resample_to_period(df, Period.MONTH, aggregation="median")
