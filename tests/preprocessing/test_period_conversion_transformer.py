"""Unit tests for PeriodConversionTransformer after helper refactor."""

from __future__ import annotations

import pandas as pd

from fin_statement_model.preprocessing.transformers import PeriodConversionTransformer


def _quarterly_index(start: str, periods: int) -> pd.DatetimeIndex:
    return pd.date_range(start, periods=periods, freq="QE")


def test_quarterly_to_annual_sum() -> None:
    """Aggregating quarterly flow data to annual sum should add values."""
    df = pd.DataFrame(
        {
            "revenue": [1, 1, 1, 1],
        },
        index=_quarterly_index("2022-03-31", 4),
    )

    transformer = PeriodConversionTransformer("quarterly_to_annual", aggregation="sum")
    result = transformer.transform(df)

    # One year, value should be 4 at calendar year-end timestamp
    assert list(result.index) == [pd.Timestamp("2022-12-31")]
    assert result["revenue"].iloc[0] == 4


def test_monthly_to_quarterly_last() -> None:
    """Monthly balance-sheet data aggregated with 'last' should keep last month of quarter."""
    dates = pd.date_range("2023-01-31", periods=6, freq="ME")
    df = pd.DataFrame({"assets": range(6)}, index=dates)

    transformer = PeriodConversionTransformer(
        "monthly_to_quarterly", aggregation="last"
    )
    result = transformer.transform(df)

    # Expect two quarters (Q1, Q2)
    assert list(result.index) == [(2023, 1), (2023, 2)]
    # Q1 last month is March index 2 value 2
    assert result["assets"].iloc[0] == 2
