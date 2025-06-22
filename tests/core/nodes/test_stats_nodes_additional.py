from __future__ import annotations

import math
import statistics

import pytest

from fin_statement_model.core.nodes.stats_nodes import (
    YoYGrowthNode,
    MultiPeriodStatNode,
    TwoPeriodAverageNode,
)
from fin_statement_model.core.nodes.base import Node


class _DataNode(Node):
    def __init__(self, name: str, values: dict[str, float]):
        super().__init__(name)
        self.values = values  # type: ignore[assignment]

    def calculate(self, period: str) -> float:  # noqa: D401
        return self.values[period]

    def to_dict(self):
        return {"name": self.name}

    @classmethod
    def from_dict(cls, data, context=None):  # noqa: D401
        return cls(data["name"], {})


@pytest.fixture()
def sales_node():  # noqa: D401
    return _DataNode(
        "sales", {"2022": 100.0, "2023": 120.0, "Q1": 10.0, "Q2": 12.0, "Q3": 14.0}
    )


def test_yoy_growth_basic(sales_node):
    yoy = YoYGrowthNode(
        "growth", sales_node, prior_period="2022", current_period="2023"
    )
    assert yoy.calculate() == pytest.approx((120 - 100) / 100)
    assert yoy.get_dependencies() == ["sales"]


def test_yoy_growth_div_zero(sales_node):
    zero_node = _DataNode("zero", {"2022": 0.0, "2023": 50.0})
    yoy = YoYGrowthNode("g", zero_node, "2022", "2023")
    assert math.isnan(yoy.calculate())


def test_multi_period_stat_mean(sales_node):
    mp = MultiPeriodStatNode(
        "avg_sales",
        input_node=sales_node,
        periods=["Q1", "Q2", "Q3"],
        stat_func=statistics.mean,
    )
    assert mp.calculate() == pytest.approx((10 + 12 + 14) / 3)


def test_multi_period_stat_insufficient_values(sales_node):
    # stdev with single point should yield NaN
    mp = MultiPeriodStatNode(
        "std_single",
        input_node=sales_node,
        periods=["Q1"],
        stat_func=statistics.stdev,
    )
    assert math.isnan(mp.calculate())


def test_two_period_average(sales_node):
    avg = TwoPeriodAverageNode("avg", sales_node, "Q1", "Q2")
    assert avg.calculate() == pytest.approx((10 + 12) / 2)
