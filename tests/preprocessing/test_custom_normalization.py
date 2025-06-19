"""Tests custom normalisation method registration and execution."""

from __future__ import annotations

import pandas as pd

from fin_statement_model.preprocessing.transformers import NormalizationTransformer


def winsorize(df: pd.DataFrame, _transformer: NormalizationTransformer) -> pd.DataFrame:
    """Clip values outside 5th/95th percentile."""
    res = df.copy()
    low = 0.05
    high = 0.95
    for col in res.columns:
        lower = res[col].quantile(low)
        upper = res[col].quantile(high)
        res[col] = res[col].clip(lower, upper)
    return res


def test_custom_normalization_registration_and_usage():
    NormalizationTransformer.register_custom_method(
        "winsorize", winsorize, overwrite=True
    )

    df = pd.DataFrame({"value": [1, 2, 3, 4, 100]})
    transformer = NormalizationTransformer(normalization_type="winsorize")
    result = transformer.transform(df)

    # Ensure outlier 100 was clipped
    assert result["value"].iloc[-1] < 100
