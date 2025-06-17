import math
import statistics
import pytest

from fin_statement_model.core.nodes.stats_nodes import (
    YoYGrowthNode,
    MultiPeriodStatNode,
    TwoPeriodAverageNode,
)
from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode


def test_yoy_growth_normal_and_division_by_zero():
    data = {"2022": 100.0, "2023": 120.0}
    node = FinancialStatementItemNode("rev", data)
    yoy = YoYGrowthNode("yoy", node, "2022", "2023")
    assert pytest.approx(yoy.calculate(), rel=1e-6) == 0.2

    # prior zero should result in NaN
    data_zero = {"2022": 0.0, "2023": 50.0}
    node_zero = FinancialStatementItemNode("rev0", data_zero)
    yoy_zero = YoYGrowthNode("yoy0", node_zero, "2022", "2023")
    result = yoy_zero.calculate()
    assert math.isnan(result)


def test_multi_period_stat_valid_and_edge_cases():
    # mean test with valid data
    data = {"Q1": 10, "Q2": 20, "Q3": 30}
    node = FinancialStatementItemNode("n", data)
    mean_node = MultiPeriodStatNode(
        "mean", node, ["Q1", "Q2", "Q3"], stat_func=statistics.mean
    )
    assert mean_node.calculate() == pytest.approx(statistics.mean([10, 20, 30]))

    # default stat_func is stdev with valid data
    stdev_node = MultiPeriodStatNode("stdev", node, ["Q1", "Q2", "Q3"])
    assert stdev_node.calculate() == pytest.approx(statistics.stdev([10, 20, 30]))

    # mean over missing values yields 0.0 (0.0 appended for each missing)
    empty_node = FinancialStatementItemNode("empty", {})
    mean_empty = MultiPeriodStatNode(
        "mean_empty", empty_node, ["X1", "X2"], stat_func=statistics.mean
    )
    assert mean_empty.calculate() == pytest.approx(0.0)

    # stdev requires >=2 points; with single period should return NaN
    single_node = FinancialStatementItemNode("single", {"Q1": 10})
    single_stdev = MultiPeriodStatNode(
        "single_stdev", single_node, ["Q1"], stat_func=statistics.stdev
    )
    assert math.isnan(single_stdev.calculate())


def test_two_period_average_and_non_numeric(monkeypatch):
    # normal case
    data = {"A": 5.0, "B": 15.0}
    node = FinancialStatementItemNode("n", data)
    avg = TwoPeriodAverageNode("avg", node, "A", "B")
    assert avg.calculate() == pytest.approx(10.0)

    # non-numeric input returns NaN
    class DummyNode(FinancialStatementItemNode):
        def calculate(self, period):
            return "not_a_number"

    dummy = DummyNode("d", {})
    avg_bad = TwoPeriodAverageNode("avg_bad", dummy, "A", "B")
    val_bad = avg_bad.calculate()
    assert math.isnan(val_bad)

    # missing period returns NaN for dummy node (non-numeric)
    avg_missing = TwoPeriodAverageNode("avg_missing", dummy, "A", "C")
    assert math.isnan(avg_missing.calculate())


def test_yoy_to_dict_and_from_dict():
    # Test serialization and deserialization for YoYGrowthNode
    data = {"2020": 100.0, "2021": 150.0}
    base = FinancialStatementItemNode("rev", data)
    yoy = YoYGrowthNode("yoy_test", base, "2020", "2021")
    d = yoy.to_dict()
    assert d["type"] == "yoy_growth"
    assert d["name"] == "yoy_test"
    assert d["input_node_name"] == "rev"
    assert d["prior_period"] == "2020"
    assert d["current_period"] == "2021"
    context = {"rev": base}
    new_yoy = YoYGrowthNode.from_dict(d, context)
    assert new_yoy.calculate() == pytest.approx((150.0 - 100.0) / 100.0)


def test_multi_period_stat_to_dict_and_from_dict():
    # Test serialization for MultiPeriodStatNode
    import statistics

    data = {"A": 1.0, "B": 2.0, "C": 3.0}
    node = FinancialStatementItemNode("n", data)
    stat = MultiPeriodStatNode(
        "stat_test", node, ["A", "B", "C"], stat_func=statistics.mean
    )
    d = stat.to_dict()
    assert d["type"] == "multi_period_stat"
    assert d["name"] == "stat_test"
    assert d["input_node_name"] == "n"
    assert d["periods"] == ["A", "B", "C"]
    assert d["stat_func_name"] == "mean"
    context = {"n": node}
    new_stat = MultiPeriodStatNode.from_dict(d, context)
    assert new_stat.calculate() == pytest.approx(stat.calculate())


def test_two_period_average_to_dict_and_from_dict():
    # Test serialization for TwoPeriodAverageNode
    data = {"X": 4.0, "Y": 6.0}
    node = FinancialStatementItemNode("n", data)
    avg = TwoPeriodAverageNode("avg_test", node, "X", "Y")
    d = avg.to_dict()
    assert d["type"] == "two_period_average"
    assert d["name"] == "avg_test"
    assert d["input_node_name"] == "n"
    assert d["period1"] == "X"
    assert d["period2"] == "Y"
    context = {"n": node}
    new_avg = TwoPeriodAverageNode.from_dict(d, context)
    assert new_avg.calculate() == pytest.approx(5.0)


def test_multi_period_stat_error_handling_and_stat_error():
    # Test error during value retrieval is handled and valid values used
    class ErrNode(FinancialStatementItemNode):
        def calculate(self, period):
            if period == "B":
                raise RuntimeError("fail")
            return 2.0

    err_node = ErrNode("err", {"A": 2.0})
    stat = MultiPeriodStatNode("sum_stat", err_node, ["A", "B"], stat_func=sum)
    # Only 'A' used, sum([2.0]) == 2.0
    assert stat.calculate() == pytest.approx(2.0)

    # Test stat_func raising an error leads to NaN
    def bad_stat(vals):
        raise ValueError("bad")

    stat_bad = MultiPeriodStatNode("bad_stat", err_node, ["A"], stat_func=bad_stat)
    assert math.isnan(stat_bad.calculate())
