from __future__ import annotations

import pytest

from types import SimpleNamespace

from fin_statement_model.forecasting.forecaster import batch as batch_module


class _StubGraph:
    """Very small stub implementing only the attributes used in *batch_forecast_values*."""

    def __init__(self, periods: list[str]):
        self.periods = periods

    def get_node(self, name: str):  # noqa: D401 - simple stub
        return SimpleNamespace(name=name, values={})

    # ``nodes`` mapping used only in ForecastNodeError when a node is missing - keep minimal
    @property
    def nodes(self):  # noqa: D401 - property stub
        return {"dummy": None}


@pytest.fixture()
def _patch_internals(monkeypatch: pytest.MonkeyPatch):  # noqa: D401
    """Patch heavy dependencies of *batch_module* with lightweight stubs."""

    # 1. Stub *forecast_node_non_mutating*
    def _stub_forecast_node_non_mutating(*args, **kwargs):  # noqa: D401
        return {p: 42.0 for p in kwargs.get("forecast_periods", [])}

    monkeypatch.setattr(
        batch_module,
        "forecast_node_non_mutating",
        _stub_forecast_node_non_mutating,
        raising=True,
    )

    # 2. Stub *PeriodManager* helpers
    monkeypatch.setattr(
        batch_module.PeriodManager,
        "infer_historical_periods",
        staticmethod(lambda *_, **__: ["2022", "2023"]),
        raising=True,
    )
    monkeypatch.setattr(
        batch_module.PeriodManager,
        "determine_base_period",
        staticmethod(lambda *_, **__: "2023"),
        raising=True,
    )

    # 3. Stub *ForecastValidator.validate_forecast_config*
    monkeypatch.setattr(
        batch_module.ForecastValidator,
        "validate_forecast_config",
        staticmethod(lambda cfg: SimpleNamespace(method="simple")),
        raising=True,
    )

    # 4. Ensure cfg lookup returns sensible defaults
    monkeypatch.setattr(
        batch_module,
        "cfg",
        lambda path, *_, **__: (
            False if path == "forecasting.continue_on_error" else "simple"
        ),
        raising=True,
    )


def test_batch_forecast_success(_patch_internals):  # noqa: D401
    """Ensure successful batch forecasting returns results for each node."""
    graph = _StubGraph(["2022", "2023"])
    results = batch_module.batch_forecast_values(
        fsg=graph,
        node_names=["Revenue", "COGS"],
        forecast_periods=["2024"],
    )
    assert set(results.keys()) == {"Revenue", "COGS"}
    for res in results.values():
        assert res.values == {"2024": 42.0}
        assert res.base_period == "2023"


def test_batch_forecast_continue_on_error(_patch_internals):  # noqa: D401
    """If an exception occurs and *continue_on_error* is True, processing should continue."""

    # Replace stub to raise for a specific node
    def _raiser(*args, **kwargs):  # noqa: D401 - raise for COGS
        node_name = kwargs.get("node_name")
        if node_name == "COGS":
            raise RuntimeError("boom")
        return {p: 1.0 for p in kwargs.get("forecast_periods", [])}

    import importlib

    graph = _StubGraph(["2022"])

    # patch again within this test
    from pytest import MonkeyPatch

    mpatch = MonkeyPatch()
    mpatch.setattr(batch_module, "forecast_node_non_mutating", _raiser, raising=True)
    mpatch.setattr(
        batch_module,
        "cfg",
        lambda path, *_, **__: (
            True if path == "forecasting.continue_on_error" else "simple"
        ),
        raising=True,
    )

    results = batch_module.batch_forecast_values(
        fsg=graph,
        node_names=["Revenue", "COGS"],
        forecast_periods=["2024"],
    )

    # 'COGS' should be absent due to the raised error
    assert "COGS" not in results and "Revenue" in results

    mpatch.undo()
