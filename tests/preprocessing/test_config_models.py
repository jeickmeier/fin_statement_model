"""Tests for preprocessing configuration Pydantic models with validation logic."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from fin_statement_model.preprocessing.config import (
    NormalizationConfig,
    TimeSeriesConfig,
)


def test_normalization_config_validation():
    # Should raise when reference missing for percent_of
    with pytest.raises(ValueError):
        NormalizationConfig(normalization_type="percent_of")

    # scale_by without scale_factor causes error
    with pytest.raises(ValueError):
        NormalizationConfig(normalization_type="scale_by")

    # Valid minmax config pass
    cfg = NormalizationConfig(normalization_type="minmax")
    assert cfg.normalization_type == "minmax"


def test_timeseries_moving_avg_requires_window():
    with pytest.raises(ValueError):
        TimeSeriesConfig(transformation_type="moving_avg")

    cfg = TimeSeriesConfig(transformation_type="moving_avg", window_size=3)
    assert cfg.window_size == 3


def test_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        NormalizationConfig(normalization_type="minmax", foo="bar")
