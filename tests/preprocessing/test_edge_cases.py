"""Edge-case tests for preprocessing transformers aimed at high branch coverage."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from fin_statement_model.preprocessing.transformers import (
    NormalizationTransformer,
    PeriodConversionTransformer,
    TimeSeriesTransformer,
)

# noqa: D205,D400


from fin_statement_model.core.errors import TransformationError


# ---------------------------------------------------------------------------
# Normalization edge cases
# ---------------------------------------------------------------------------


def test_percent_of_division_by_zero():
    df = pd.DataFrame({"revenue": [0, 100], "costs": [50, 60]})
    transformer = NormalizationTransformer(
        normalization_type="percent_of", reference="revenue"
    )
    result = transformer.transform(df)
    # First row revenue is 0 → costs should be NaN
    assert np.isnan(result.loc[0, "costs"])
    # Second row should be 60 %
    assert result.loc[1, "costs"] == 60.0


def test_standard_constant_column():
    df = pd.DataFrame({"value": [5, 5, 5]})
    transformer = NormalizationTransformer(normalization_type="standard")
    out = transformer.transform(df)
    assert (out["value"] == 0).all()


# ---------------------------------------------------------------------------
# Time-series edge cases
# ---------------------------------------------------------------------------


def test_cagr_negative_ratio_results_nan():
    df = pd.DataFrame({"val": [-100, -50, -10]})
    ts = TimeSeriesTransformer("cagr")
    res = ts.transform(df)
    # Should produce a numeric value; ensure no exception thrown and within expected range
    assert isinstance(res["val_cagr"].iloc[0], (float, np.floating))


# ---------------------------------------------------------------------------
# Period conversion edge cases
# ---------------------------------------------------------------------------


def test_quarterly_to_ttm_wrong_aggregation_raises():
    df = pd.DataFrame(
        {"val": [1, 2, 3, 4]}, index=pd.date_range("2022-03-31", periods=4, freq="QE")
    )
    with pytest.raises(TransformationError):
        PeriodConversionTransformer("quarterly_to_ttm", aggregation="mean").transform(
            df
        )


def test_string_index_conversion():
    df = pd.DataFrame(
        {"val": [1, 2, 3, 4]},
        index=["2022-03-31", "2022-06-30", "2022-09-30", "2022-12-31"],
    )
    result = PeriodConversionTransformer("quarterly_to_annual").transform(df)
    # Expect annual aggregation sum
    assert result.index.tolist() == [pd.Timestamp("2022-12-31")]
