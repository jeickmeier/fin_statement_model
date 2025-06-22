from __future__ import annotations

import math
import types
import pytest

from fin_statement_model.forecasting.methods.historical_growth import (
    HistoricalGrowthForecastMethod,
)
from fin_statement_model.core.nodes.base import Node


class _SimpleNode(Node):
    """Minimal concrete Node with deterministic *calculate* logic."""

    def __init__(self, name: str, values: dict[str, float]):
        super().__init__(name)
        self.values = values  # type: ignore[assignment]

    def calculate(self, period: str) -> float:  # noqa: D401
        return self.values.get(period, math.nan)

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name}

    @classmethod
    def from_dict(
        cls, data: dict[str, str], context: dict[str, Node] | None = None
    ) -> "_SimpleNode":  # noqa: D401
        return cls(data["name"], {})


@pytest.fixture()
def method() -> HistoricalGrowthForecastMethod:  # noqa: D401 – fixture
    return HistoricalGrowthForecastMethod()


def test_calculate_average_growth_rate_mean(
    monkeypatch: pytest.MonkeyPatch, method: HistoricalGrowthForecastMethod
) -> None:
    """Mean aggregation should be used by default."""

    # Ensure cfg returns 'mean' (the default branch)
    from fin_statement_model.forecasting import methods as _methods_pkg
    from fin_statement_model.forecasting.methods import historical_growth as hg_module

    # Patch cfg used inside the module
    monkeypatch.setattr(hg_module, "cfg", lambda path, *_, **__: "mean", raising=True)

    hist_values = [100.0, 110.0, 121.0]
    growth = method.calculate_average_growth_rate(hist_values)
    # 10% average growth -> 0.1
    assert growth == pytest.approx(0.10, rel=1e-6)


def test_calculate_average_growth_rate_median(
    monkeypatch: pytest.MonkeyPatch, method: HistoricalGrowthForecastMethod
) -> None:
    """Median aggregation branch should be exercised when specified via cfg."""

    monkeypatch.setattr(
        method.__class__, "internal_type", "average_growth", raising=False
    )  # no effect but keeps coverage honest

    from fin_statement_model.forecasting.methods import historical_growth as hg_module

    monkeypatch.setattr(hg_module, "cfg", lambda path, *_, **__: "median", raising=True)

    hist_values = [100.0, 150.0, 250.0]  # growth rates: 50%, 66.67% -> median 0.5833...
    growth = method.calculate_average_growth_rate(hist_values)
    expected_median = 0.5833333333333334  # approximate
    assert growth == pytest.approx(expected_median, rel=1e-6)


def test_prepare_historical_data_minimum_period_check(
    monkeypatch: pytest.MonkeyPatch, method: HistoricalGrowthForecastMethod
) -> None:
    """Less than *min_historical_periods* should raise a ValueError."""

    from fin_statement_model.forecasting.methods import historical_growth as hg_module

    # Set min_historical_periods to 3 for this test
    monkeypatch.setattr(
        hg_module,
        "cfg",
        lambda path, *_, **__: (
            3 if path == "forecasting.min_historical_periods" else None
        ),
        raising=True,
    )

    node = _SimpleNode("Revenue", {"2022": 100.0})  # Only one period available
    with pytest.raises(ValueError):
        method.prepare_historical_data(node, historical_periods=["2022", "2021"])


def test_prepare_historical_data_success(
    monkeypatch: pytest.MonkeyPatch, method: HistoricalGrowthForecastMethod
) -> None:
    """With enough valid periods the method should return the historical values list."""

    from fin_statement_model.forecasting.methods import historical_growth as hg_module

    monkeypatch.setattr(
        hg_module,
        "cfg",
        lambda path, *_, **__: (
            2 if path == "forecasting.min_historical_periods" else None
        ),
        raising=True,
    )

    node = _SimpleNode(
        "Revenue",
        {
            "2021": 90.0,
            "2022": 100.0,
            "2023": 110.0,
        },
    )

    result = method.prepare_historical_data(node, ["2021", "2022", "2023"])
    # Ensure chronological order and correctness
    assert result == [90.0, 100.0, 110.0]
