from __future__ import annotations

"""Tests covering preprocessing utilities and NormalizationTransformer.

Focus areas:
1. ensure_dataframe happy path (DataFrame and Series) and error for wrong type.
2. NormalizationTransformer - percent_of, scale_by, custom function and error paths.
"""


import numpy as np
import pandas as pd
import pytest

from fin_statement_model.preprocessing.utils import ensure_dataframe
from fin_statement_model.preprocessing.transformers.normalization import (
    NormalizationTransformer,
)
from fin_statement_model.preprocessing.errors import NormalizationError
from fin_statement_model.core.errors import DataValidationError


# ----------------------------------------------------------------------------
# ensure_dataframe
# ----------------------------------------------------------------------------


def test_ensure_dataframe_variants() -> None:
    df_in = pd.DataFrame({"a": [1, 2]})
    df_out, was_series = ensure_dataframe(df_in)
    assert df_out is df_in and was_series is False

    ser = pd.Series([1, 2], name="x")
    df_from_series, was_series = ensure_dataframe(ser)
    assert isinstance(df_from_series, pd.DataFrame) and was_series is True
    assert list(df_from_series.columns) == ["x"]

    with pytest.raises(TypeError):
        ensure_dataframe([1, 2])  # type: ignore[arg-type]


# ----------------------------------------------------------------------------
# NormalizationTransformer - percent_of, scale_by, custom, error handling
# ----------------------------------------------------------------------------


def test_percent_of_normalization() -> None:
    df = pd.DataFrame(
        {
            "revenue": [100, 200],
            "cogs": [60, 120],
        }
    )
    norm = NormalizationTransformer(
        normalization_type="percent_of", reference="revenue"
    )
    out = norm.transform(df)
    # revenue should be 100%; cogs percentages 60%
    assert np.isclose(out.loc[0, "cogs"], 60.0)
    assert np.isclose(out.loc[1, "cogs"], 60.0)


def test_scale_by_normalization() -> None:
    df = pd.DataFrame({"val": [1000, 2000]})
    scaler = NormalizationTransformer(normalization_type="scale_by", scale_factor=0.1)
    out = scaler.transform(df)
    assert list(out["val"]) == [100.0, 200.0]


def test_custom_normalization_registration() -> None:
    def double(df_: pd.DataFrame, _t: NormalizationTransformer):  # noqa: D401
        return df_ * 2

    NormalizationTransformer.register_custom_method("double", double, overwrite=True)

    df = pd.DataFrame({"a": [1, 2]})
    custom = NormalizationTransformer(normalization_type="double")
    out = custom.transform(df)
    assert list(out["a"]) == [2, 4]


def test_normalization_error_cases() -> None:
    # Missing reference for percent_of
    with pytest.raises(NormalizationError):
        NormalizationTransformer(normalization_type="percent_of")

    # Missing scale_factor for scale_by
    with pytest.raises(NormalizationError):
        NormalizationTransformer(normalization_type="scale_by")

    # Passing non-DF/Series data raises DataValidationError via transform()
    norm = NormalizationTransformer(normalization_type="scale_by", scale_factor=1)
    with pytest.raises(DataValidationError):
        norm.transform({"a": 1})  # type: ignore[arg-type]
