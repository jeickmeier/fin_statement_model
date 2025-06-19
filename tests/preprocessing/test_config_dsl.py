"""Tests for fluent DSL classmethods of preprocessing config models."""

from __future__ import annotations


from fin_statement_model.preprocessing.config import (
    NormalizationConfig,
    TimeSeriesConfig,
    PeriodConversionConfig,
)


def test_normalization_dsl():
    cfg = NormalizationConfig.percent_of("revenue")
    assert cfg.normalization_type == "percent_of"
    assert cfg.reference == "revenue"

    cfg2 = NormalizationConfig.scale_by(1e-6)
    assert cfg2.scale_factor == 1e-6


def test_timeseries_dsl():
    cfg = TimeSeriesConfig.yoy()
    assert cfg.transformation_type == "yoy"
    assert cfg.periods == 4

    ma = TimeSeriesConfig.moving_avg(window_size=5)
    assert ma.window_size == 5
    assert ma.transformation_type == "moving_avg"


def test_period_conversion_dsl():
    pc = PeriodConversionConfig.monthly_to_quarterly(aggregation="last")
    assert pc.conversion_type == "monthly_to_quarterly"
    assert pc.aggregation == "last"
