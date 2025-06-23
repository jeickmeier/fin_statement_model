"""Unit tests for forecasting period management and validation utilities.

This module targets
``fin_statement_model.forecasting.period_manager.PeriodManager`` and
``fin_statement_model.forecasting.validators.ForecastValidator`` ensuring
robust handling of:

* Historical/forecast period inference and checks.
* Base-period selection logic with different config flags.
* Sequence validation and graph-period reconciliation helpers.
* Forecast configuration and result validation paths.

The tests rely on small stub objects so they are fully isolated from the
larger graph implementation.
"""

# ruff: noqa: PLR2004, S101 – allow hard-coded values & assert-style tests
from __future__ import annotations

from typing import Any

import pytest

from fin_statement_model.config.store import update_config
from fin_statement_model.core.nodes.base import Node
from fin_statement_model.forecasting.period_manager import PeriodManager
from fin_statement_model.forecasting.validators import (
    ForecastValidator,
    ForecastConfigurationError,
    ForecastMethodError,
    ForecastNodeError,
    ForecastResultError,
)
from fin_statement_model.forecasting.types import ForecastConfig


class DummyGraph:
    """Simple graph stub exposing *periods* and *add_periods*."""

    def __init__(self, periods: list[str]):
        self.periods: list[str] = periods
        self._added: list[str] = []

    # Mimic the graph API used by PeriodManager
    def add_periods(self, periods: list[str]) -> None:  # noqa: D401 – simple verb
        self.periods.extend(periods)
        self._added.extend(periods)


class DummyNode(Node):
    """Minimal data node with fixed period-value mapping."""

    def __init__(self, name: str, values: dict[str, float]):
        super().__init__(name)
        self.values = values

    def calculate(self, period: str) -> float:  # noqa: D401
        return self.values[period]

    def to_dict(self) -> dict[str, Any]:  # noqa: D401 – trivial
        return {"type": "dummy", "name": self.name}

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], context: dict[str, Node] | None = None
    ) -> "DummyNode":
        return cls(data["name"], {})


# ----------------------------------------------------------------------
# PeriodManager tests
# ----------------------------------------------------------------------


def test_infer_historical_periods_split_and_fallback() -> None:  # noqa: D401
    graph = DummyGraph(["2021", "2022", "2023"])

    # Standard split at first forecast period
    hist = PeriodManager.infer_historical_periods(graph, ["2023"])
    assert hist == ["2021", "2022"]

    # Forecast period not present → all graph periods considered historical
    hist_fallback = PeriodManager.infer_historical_periods(graph, ["2024"])
    assert hist_fallback == ["2021", "2022", "2023"]


def test_ensure_periods_exist_adds_missing() -> None:  # noqa: D401
    graph = DummyGraph(["2022"])
    missing = PeriodManager.ensure_periods_exist(
        graph, ["2022", "2023"], add_missing=True
    )
    assert missing == ["2023"]
    assert "2023" in graph.periods  # added

    # With add_missing=False a ValueError is raised
    graph2 = DummyGraph(["2022"])
    with pytest.raises(ValueError):
        PeriodManager.ensure_periods_exist(graph2, ["2022", "2023"], add_missing=False)


@pytest.mark.parametrize(
    "periods, expect_error",
    [(["2022", "2023"], False), ([], True), (["2022", "2022"], True)],
)
def test_validate_period_sequence(
    periods: list[str], expect_error: bool
) -> None:  # noqa: D401 – paramized
    if expect_error:
        with pytest.raises(ValueError):
            PeriodManager.validate_period_sequence(periods)
    else:
        PeriodManager.validate_period_sequence(periods)  # should not raise


def test_determine_base_period_strategy_variants() -> None:  # noqa: D401
    node = DummyNode("sales", {"2021": 90.0, "2022": 100.0})
    hist_periods = ["2021", "2022"]

    # Default strategy (preferred_then_most_recent) with preferred set
    base = PeriodManager.determine_base_period(
        node, hist_periods, preferred_period="2021"
    )
    assert base == "2021"

    # Switch to most_recent strategy via runtime config
    update_config({"forecasting": {"base_period_strategy": "most_recent"}})
    base_most_recent = PeriodManager.determine_base_period(node, hist_periods)
    assert base_most_recent == "2022"

    # last_historical strategy always picks last in *historical_periods*
    update_config({"forecasting": {"base_period_strategy": "last_historical"}})
    base_last = PeriodManager.determine_base_period(node, hist_periods)
    assert base_last == "2022"

    # Clean-up restore default config
    update_config(
        {"forecasting": {"base_period_strategy": "preferred_then_most_recent"}}
    )


# ----------------------------------------------------------------------
# ForecastValidator tests
# ----------------------------------------------------------------------


def test_validate_forecast_inputs_and_node_config() -> None:  # noqa: D401
    # Basic happy-path call – should not raise
    ForecastValidator.validate_forecast_inputs(["2021"], ["2022"])

    # Invalid node_configs type
    with pytest.raises(ForecastConfigurationError):
        ForecastValidator.validate_forecast_inputs(["2021"], ["2022"], node_configs=["bad"])  # type: ignore[arg-type]

    # Node-config validation – missing keys
    with pytest.raises(ValueError):
        ForecastValidator.validate_node_config("revenue", {})

    with pytest.raises(ValueError):
        ForecastValidator.validate_node_config("revenue", {"method": "simple"})

    # Unsupported method
    with pytest.raises(ValueError):
        ForecastValidator.validate_node_config(
            "revenue", {"method": "foo", "config": 1}
        )

    # Correct config should pass silently
    ForecastValidator.validate_node_config(
        "revenue", {"method": "simple", "config": 0.05}
    )


def test_validate_node_for_forecast_and_config_parsing() -> None:  # noqa: D401
    node = DummyNode("bad", {})
    # Missing values dict (simulate by deleting attribute)
    delattr(node, "values")
    with pytest.raises(ForecastNodeError):
        ForecastValidator.validate_node_for_forecast(node, "simple")

    # ForecastConfig parsing
    fc = ForecastValidator.validate_forecast_config({"method": "simple", "config": 0.1})
    assert isinstance(fc, ForecastConfig)

    with pytest.raises(ForecastMethodError):
        ForecastValidator.validate_forecast_config({"method": "unknown", "config": 0})


def test_validate_base_period_and_forecast_result() -> None:  # noqa: D401
    # Base-period validation
    with pytest.raises(ValueError):
        ForecastValidator.validate_base_period("2023", ["2021"], "rev")

    ForecastValidator.validate_base_period("2021", ["2021"], "rev")  # should pass

    # Forecast-result validation
    with pytest.raises(ForecastResultError):
        ForecastValidator.validate_forecast_result({"2024": "bad"}, ["2024"])  # type: ignore[arg-type]

    # Missing period
    with pytest.raises(ForecastResultError):
        ForecastValidator.validate_forecast_result({}, ["2024"])

    # Happy-path
    ForecastValidator.validate_forecast_result({"2024": 1.0}, ["2024"])  # no error
