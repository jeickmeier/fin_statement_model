from __future__ import annotations

import types

import pytest

from types import SimpleNamespace

from fin_statement_model.forecasting.forecaster import node_forecast as nf_module
from fin_statement_model.core.nodes.base import Node


class _MiniNode(Node):
    def __init__(self, name: str, values: dict[str, float]):
        super().__init__(name)
        self.values = values  # type: ignore[assignment]

    def calculate(self, period: str) -> float:  # noqa: D401
        return self.values.get(period, 0.0)

    def to_dict(self):
        return {"name": self.name}

    @classmethod
    def from_dict(cls, data, context=None):  # noqa: D401
        return cls(data["name"], {})


class _StubGraph:
    def __init__(self):
        self.periods = ["2022"]
        self._nodes = {"Revenue": _MiniNode("Revenue", {"2022": 100.0})}

    def get_node(self, name: str):
        return self._nodes.get(name)

    @property
    def nodes(self):
        return self._nodes


@pytest.fixture()
def monkeypatched_env(monkeypatch: pytest.MonkeyPatch):  # noqa: D401
    """Patch heavy components inside node_forecast module."""

    # 1) Patch cfg helpers
    monkeypatch.setattr(nf_module, "cfg", lambda path, *_, **__: 0.0, raising=True)

    # 2) ForecastValidator methods become no-ops returning sensible defaults
    monkeypatch.setattr(
        nf_module.ForecastValidator,
        "validate_forecast_inputs",
        staticmethod(lambda *_, **__: None),
        raising=True,
    )
    monkeypatch.setattr(
        nf_module.ForecastValidator,
        "validate_node_for_forecast",
        staticmethod(lambda *_, **__: None),
        raising=True,
    )
    monkeypatch.setattr(
        nf_module.ForecastValidator,
        "validate_forecast_result",
        staticmethod(lambda *_, **__: None),
        raising=True,
    )

    # 3) validate_forecast_config returns SimpleNamespace with method="dummy" and config={}
    monkeypatch.setattr(
        nf_module.ForecastValidator,
        "validate_forecast_config",
        staticmethod(lambda cfg: SimpleNamespace(method="dummy", config={})),
        raising=True,
    )

    # 4) Patch strategies.get_forecast_method to return a minimal BaseForecastMethod impl
    class _DummyMethod(nf_module.BaseForecastMethod):
        @property
        def name(self):
            return "dummy"

        @property
        def internal_type(self):
            return "dummy"

        def validate_config(self, config):
            pass

        def normalize_params(self, config, forecast_periods):
            return {"forecast_type": "dummy", "growth_params": None}

    monkeypatch.setattr(
        nf_module, "get_forecast_method", lambda *_: _DummyMethod(), raising=True
    )

    # 5) Stub NodeFactory.create_forecast_node to return object with calculate→constant
    monkeypatch.setattr(
        nf_module.NodeFactory,
        "create_forecast_node",
        lambda *_, **__: SimpleNamespace(calculate=lambda period: 42.0),
        raising=True,
    )

    # 6) PeriodManager helpers
    monkeypatch.setattr(
        nf_module.PeriodManager,
        "infer_historical_periods",
        staticmethod(lambda *_: ["2022"]),
        raising=True,
    )
    monkeypatch.setattr(
        nf_module.PeriodManager,
        "determine_base_period",
        staticmethod(lambda *_, **__: "2022"),
        raising=True,
    )


def test_forecast_node_success(monkeypatched_env):  # noqa: D401
    g = _StubGraph()
    result = nf_module.forecast_node_non_mutating(
        g,
        node_name="Revenue",
        forecast_periods=["2023", "2024"],
        forecast_config={"method": "dummy", "config": {}},
    )
    assert result == {"2023": 42.0, "2024": 42.0}


def test_forecast_node_missing_node(monkeypatched_env):  # noqa: D401
    g = _StubGraph()
    with pytest.raises(nf_module.ForecastNodeError):
        nf_module.forecast_node_non_mutating(
            g, node_name="Missing", forecast_periods=["2023"]
        )


def test_calc_bad_value_and_clamp():
    bad = nf_module._calc_bad_value(bad_forecast_value=-1.0)
    assert bad == -1.0
    assert nf_module._clamp(float("nan"), True, -99.0) == -99.0
    assert nf_module._clamp(-5.0, False, -99.0) == -99.0
    assert nf_module._clamp(5.0, False, -99.0) == 5.0
