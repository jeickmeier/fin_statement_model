"""Tests to ensure transformer constructors warn when both config and kwargs are supplied."""

from __future__ import annotations

import warnings

import pytest

from fin_statement_model.preprocessing.config import (
    NormalizationConfig,
    TimeSeriesConfig,
    PeriodConversionConfig,
)
from fin_statement_model.preprocessing.transformers import (
    NormalizationTransformer,
    TimeSeriesTransformer,
    PeriodConversionTransformer,
)


@pytest.mark.parametrize(
    "transformer_cls, cfg_obj, kwargs",
    [
        (
            NormalizationTransformer,
            NormalizationConfig(normalization_type="minmax"),
            {"reference": "revenue"},
        ),
        (
            TimeSeriesTransformer,
            TimeSeriesConfig(transformation_type="moving_avg", window_size=3),
            {"window_size": 5},
        ),
        (
            PeriodConversionTransformer,
            PeriodConversionConfig(conversion_type="quarterly_to_ttm"),
            {"aggregation": "mean"},
        ),
    ],
)
def test_constructor_warns_on_mixed_usage(transformer_cls, cfg_obj, kwargs):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        transformer_cls(config=cfg_obj, **kwargs)
        assert any(
            issubclass(warning.category, UserWarning) for warning in w
        ), "Expected UserWarning when config and kwargs are mixed"
