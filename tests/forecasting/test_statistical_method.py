from __future__ import annotations

import math
import pytest

from fin_statement_model.forecasting.methods.statistical import (
    StatisticalForecastMethod,
)


@pytest.fixture()
def method() -> StatisticalForecastMethod:
    return StatisticalForecastMethod()


def test_validate_config_success(method: StatisticalForecastMethod) -> None:
    cfg = {"distribution": "normal", "params": {"mean": 0.0, "std": 1.0}}
    method.validate_config(cfg)  # should not raise


def test_validate_config_errors(method: StatisticalForecastMethod):
    # Not a dict
    with pytest.raises(TypeError):
        method.validate_config("bad")  # type: ignore[arg-type]

    # Missing keys
    with pytest.raises(ValueError):
        method.validate_config({"distribution": "normal"})

    # Invalid params structure - any exception acceptable
    with pytest.raises(Exception):
        method.validate_config({"distribution": "uniform", "params": {"foo": 1}})


def test_normalize_params_generates_callable(
    method: StatisticalForecastMethod, monkeypatch
):
    # Fix RNG seed to deterministic value via cfg patch
    from fin_statement_model.forecasting.methods import statistical as stat_module

    monkeypatch.setattr(stat_module, "cfg", lambda path, *_, **__: 1234, raising=True)

    cfg = {"distribution": "uniform", "params": {"low": 0.0, "high": 1.0}}
    out = method.normalize_params(cfg, ["2024"])
    assert out["forecast_type"] == "statistical"
    gen = out["growth_params"]
    assert callable(gen)
    # Deterministic due to seeded RNG
    val = gen()
    # Ensure value within expected range
    assert 0.0 <= val <= 1.0
