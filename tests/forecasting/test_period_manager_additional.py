from __future__ import annotations

import pytest

from fin_statement_model.forecasting.period_manager import PeriodManager
from fin_statement_model.core.nodes.base import Node


class _DummyGraph:
    """A minimal graph-like object with *periods* and *add_periods*."""

    def __init__(self, periods: list[str]):
        self.periods = list(periods)

    def add_periods(self, new: list[str]) -> None:  # noqa: D401 – simple helper
        self.periods.extend(new)


class _SimpleNode(Node):
    """Minimal concrete Node implementation holding static values."""

    def __init__(self, name: str, values: dict[str, float]):
        super().__init__(name)
        self.values = values  # type: ignore[assignment]

    def calculate(self, period: str) -> float:  # noqa: D401
        return self.values.get(period, float("nan"))

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name}

    @classmethod
    def from_dict(
        cls, data: dict[str, str], context: dict[str, Node] | None = None
    ) -> "_SimpleNode":  # noqa: D401
        return cls(data["name"], {})


def test_infer_historical_periods_variants() -> None:
    """``infer_historical_periods`` should respect provided or inferred logic."""
    graph = _DummyGraph(["2022", "2023", "2024"])

    # 1. Provided periods override inference
    assert PeriodManager.infer_historical_periods(graph, ["2024"], ["2020"]) == [
        "2020",
    ]

    # 2. First forecast present → split before it
    assert PeriodManager.infer_historical_periods(graph, ["2024"]) == ["2022", "2023"]

    # 3. First forecast missing → use all existing periods
    graph2 = _DummyGraph(["2022", "2023"])
    assert PeriodManager.infer_historical_periods(graph2, ["2025"]) == ["2022", "2023"]


def test_validate_period_sequence_and_get_index() -> None:
    """Validate period sequence utilities including duplicate detection."""
    # Valid sequence passes
    PeriodManager.validate_period_sequence(["2021", "2022"])

    # Duplicate period should raise
    with pytest.raises(ValueError):
        PeriodManager.validate_period_sequence(["2021", "2021"])

    # Index retrieval
    assert PeriodManager.get_period_index("2022", ["2021", "2022", "2023"]) == 1


def test_ensure_periods_exist_behaviour() -> None:
    """Missing periods are optionally added or raise depending on *add_missing*."""
    graph = _DummyGraph(["2022"])

    # When *add_missing* is True (default) the period should be appended and returned
    added = PeriodManager.ensure_periods_exist(graph, ["2023"])
    assert "2023" in graph.periods and added == ["2023"]

    # When set to False, a missing period should raise
    graph2 = _DummyGraph(["2022"])
    with pytest.raises(ValueError):
        PeriodManager.ensure_periods_exist(graph2, ["2023"], add_missing=False)


def test_determine_base_period_with_unknown_strategy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unknown ``base_period_strategy`` should fall back to 'preferred_then_most_recent'."""

    # Patch cfg inside the module *namespace* to control return value
    from fin_statement_model.forecasting import period_manager as pm_module

    def _fake_cfg(path: str, *args, **kwargs):  # noqa: D401
        if path == "forecasting.base_period_strategy":
            return "some_unknown_strategy"
        return None

    monkeypatch.setattr(pm_module, "cfg", _fake_cfg, raising=True)

    node = _SimpleNode("Revenue", {"2022": 100.0, "2023": 110.0})
    base_period = PeriodManager.determine_base_period(
        node,
        historical_periods=["2022", "2023"],
        preferred_period="2020",  # ignored because not in *values*
    )
    # Expect fallback to the most recent available period ('2023')
    assert base_period == "2023"
