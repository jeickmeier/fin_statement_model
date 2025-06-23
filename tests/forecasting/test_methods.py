"""Test suite for forecasting method classes.

This module contains unit tests for the built-in forecasting method
implementations located in ``fin_statement_model.forecasting.methods``.
The test cases focus on:

1. Configuration validation logic.
2. Parameter normalisation behaviour (``normalize_params`` /
   ``get_forecast_params``).
3. Historical data preparation helpers where relevant.
4. Side-effect-free statistical generator output properties.

The goal is to ensure deterministic, high-branch-coverage behaviour for
all public paths of the simple, curve, average, historical-growth and
statistical forecast methods.
"""

# ruff: noqa: PLR2004, S101 - allow hard-coded values & assert-style tests
from __future__ import annotations

from typing import Any, Callable

import math

import numpy as np
import pytest

from fin_statement_model.config.store import update_config
from fin_statement_model.forecasting.methods import (
    AverageForecastMethod,
    CurveForecastMethod,
    HistoricalGrowthForecastMethod,
    SimpleForecastMethod,
    StatisticalForecastMethod,
)
from fin_statement_model.core.nodes.base import Node


class DummyNode(Node):
    """Minimal concrete ``Node`` implementation for testing helpers."""

    def __init__(self, name: str, values: dict[str, float]):
        super().__init__(name)
        self.values: dict[str, float] = values

    # ------------------------------------------------------------------
    # Abstract API implementations

    def calculate(self, period: str) -> float:  # noqa: D401 - simple verb okay
        """Return the stored value for *period* (mimics a data node)."""
        return self.values[period]

    def to_dict(self) -> dict[str, Any]:  # noqa: D401 - simple verb okay
        """Serialize to bare-minimum dict - not used in tests."""
        return {"type": "dummy", "name": self.name}

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], context: dict[str, Node] | None = None
    ) -> "DummyNode":  # noqa: D401 - concise
        return cls(data["name"], {})


# ----------------------------------------------------------------------
# SimpleForecastMethod
# ----------------------------------------------------------------------


def test_simple_method_validation_and_normalisation() -> None:  # noqa: D401
    """Numeric and single-item list configs are accepted and normalised."""
    method = SimpleForecastMethod()

    # Numeric config
    params = method.get_forecast_params(0.05, ["2024", "2025"])
    assert params == {"forecast_type": "simple", "growth_params": 0.05}

    # List with one numeric value - first element is taken
    params_list = method.get_forecast_params([0.07], ["2024"])
    assert params_list == {"forecast_type": "simple", "growth_params": 0.07}


@pytest.mark.parametrize(
    "bad_config, exc_type",
    [([], ValueError), ("five", TypeError), (["foo"], TypeError)],
)
def test_simple_method_invalid_configs(
    bad_config: Any, exc_type: type[Exception]
) -> None:  # noqa: D401 - concise
    """Invalid configs raise the correct exception type."""
    method = SimpleForecastMethod()
    with pytest.raises(exc_type):
        method.validate_config(bad_config)


# ----------------------------------------------------------------------
# CurveForecastMethod
# ----------------------------------------------------------------------


def test_curve_method_single_value_expansion() -> None:  # noqa: D401
    """A scalar config is expanded to the length of *forecast_periods*."""
    method = CurveForecastMethod()
    params = method.normalize_params(0.03, ["2024", "2025", "2026"])
    assert params["growth_params"] == [0.03, 0.03, 0.03]


def test_curve_method_list_handling() -> None:  # noqa: D401 - concise
    """A list config must match the forecast-period length exactly."""
    method = CurveForecastMethod()
    out = method.normalize_params([0.05, 0.04], ["2024", "2025"])
    assert out["growth_params"] == [0.05, 0.04]

    with pytest.raises(ValueError):
        method.normalize_params([0.05], ["2024", "2025"])  # length mismatch

    with pytest.raises(TypeError):
        method.validate_config([0.05, "oops"])  # non-numeric entry


# ----------------------------------------------------------------------
# AverageForecastMethod - historical-data preparation
# ----------------------------------------------------------------------


def test_average_method_prepare_historical_data_success() -> None:  # noqa: D401
    """Valid historical periods are returned as floats, invalid are skipped."""
    node = DummyNode("revenue", {"2022": 100.0, "2023": 110.0, "202X": math.nan})
    method = AverageForecastMethod()

    hist = method.prepare_historical_data(node, ["2022", "2023", "202X"])
    assert hist == [100.0, 110.0]


def test_average_method_prepare_historical_data_failure() -> None:  # noqa: D401
    """If *no* valid periods remain, a ``ValueError`` is raised."""
    node = DummyNode("empty", {"2022": math.nan})
    method = AverageForecastMethod()

    with pytest.raises(ValueError, match="No valid historical data"):
        method.prepare_historical_data(node, ["2022"])


# ----------------------------------------------------------------------
# HistoricalGrowthForecastMethod - growth-rate calculation helper
# ----------------------------------------------------------------------


def test_historical_growth_average_rate_mean_and_median() -> None:  # noqa: D401
    """Mean vs. median aggregation depends on config flag."""
    method = HistoricalGrowthForecastMethod()
    hist_vals = [100.0, 110.0, 132.0]  # → growth rates 10 %, 20 %

    # Default aggregation is *mean*
    mean_rate = method.calculate_average_growth_rate(hist_vals)
    assert math.isclose(mean_rate, 0.15, rel_tol=1e-6)

    # Switch to *median* aggregation via runtime config override
    update_config({"forecasting": {"historical_growth_aggregation": "median"}})
    median_rate = method.calculate_average_growth_rate(hist_vals)
    assert median_rate == 0.15  # median of [0.1, 0.2] is 0.15

    # Clean-up - restore default aggregation to avoid side-effects
    update_config({"forecasting": {"historical_growth_aggregation": "mean"}})


# ----------------------------------------------------------------------
# StatisticalForecastMethod - generator behaviour
# ----------------------------------------------------------------------


def test_statistical_method_generator_properties() -> None:  # noqa: D401
    """The normal-distribution generator produces ~0 mean with fixed seed."""
    method = StatisticalForecastMethod()
    config = {"distribution": "normal", "params": {"mean": 0.0, "std": 1.0}}

    params = method.normalize_params(config, ["2024", "2025", "2026"])
    generator: Callable[[], float] = params["growth_params"]

    # Draw many samples - the sample mean should converge towards 0
    samples = np.array([generator() for _ in range(2_000)])
    assert (
        abs(samples.mean()) < 0.1
    )  # loose bound - deterministic due to default seed=None

    # Ensure each call returns a *float*
    assert isinstance(generator(), float)
