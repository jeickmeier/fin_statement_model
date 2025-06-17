import pytest

from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode
from fin_statement_model.core.nodes.forecast_nodes import (
    FixedGrowthForecastNode,
    CurveGrowthForecastNode,
    StatisticalGrowthForecastNode,
    CustomGrowthForecastNode,
    AverageValueForecastNode,
    AverageHistoricalGrowthForecastNode,
)


def test_fixed_growth_forecast_node_and_roundtrip():
    base = FinancialStatementItemNode("x", {"2020": 100.0})
    fc = FixedGrowthForecastNode(base, "2020", ["2021", "2022"], growth_rate=0.1)
    # 2021: 100 *1.1 =110, 2022:110*1.1=121
    assert fc.calculate("2021") == pytest.approx(110.0)
    assert fc.calculate("2022") == pytest.approx(121.0)
    # invalid period
    with pytest.raises(ValueError):
        fc.calculate("2030")
    # to_dict and from_dict
    d = fc.to_dict()
    assert d["forecast_type"] == "simple"
    context = {"x": base}
    new_fc = FixedGrowthForecastNode.from_dict(d, context)
    assert new_fc.calculate("2022") == pytest.approx(121.0)


def test_curve_growth_forecast_node_and_roundtrip():
    base = FinancialStatementItemNode("y", {"2020": 50.0})
    rates = [0.2, 0.1]
    cc = CurveGrowthForecastNode(base, "2020", ["2021", "2022"], growth_rates=rates)
    # 2021: 50*1.2=60, 2022:60*1.1=66
    assert cc.calculate("2021") == pytest.approx(60.0)
    assert cc.calculate("2022") == pytest.approx(66.0)
    d = cc.to_dict()
    assert d["forecast_type"] == "curve"
    new_cc = CurveGrowthForecastNode.from_dict(d, {"y": base})
    assert new_cc.calculate("2022") == pytest.approx(66.0)


def test_average_value_forecast_node_and_roundtrip():
    data = {"2019": 80.0, "2020": 120.0}
    base = FinancialStatementItemNode("z", data)
    avg = AverageValueForecastNode(base, "2020", ["2021"])
    # avg historical = (80+120)/2 =100
    assert avg.calculate("2021") == pytest.approx(100.0)
    d = avg.to_dict()
    assert d["forecast_type"] == "average"
    new_avg = AverageValueForecastNode.from_dict(d, {"z": base})
    assert new_avg.calculate("2021") == pytest.approx(100.0)


def test_average_historical_growth_forecast_node_and_roundtrip():
    data = {"2018": 100.0, "2019": 150.0, "2020": 200.0}
    base = FinancialStatementItemNode("w", data)
    hist = AverageHistoricalGrowthForecastNode(base, "2020", ["2021", "2022"])
    # growth rates: (150-100)/100=0.5, (200-150)/150≈0.3333, avg≈0.4167
    expected_rate = (0.5 + (50.0 / 150.0)) / 2
    assert hist.avg_growth_rate == pytest.approx(expected_rate)
    # 2021:200*(1+rate)
    val1 = hist.calculate("2021")
    assert val1 == pytest.approx(200.0 * (1 + expected_rate))
    # 2022: val1*(1+rate)
    val2 = hist.calculate("2022")
    assert val2 == pytest.approx(val1 * (1 + expected_rate))
    d = hist.to_dict()
    assert d["forecast_type"] == "historical_growth"
    new_hist = AverageHistoricalGrowthForecastNode.from_dict(d, {"w": base})
    assert new_hist.calculate("2022") == pytest.approx(val2)


def test_statistical_and_custom_growth_forecast_errors_and_calculate():
    base = FinancialStatementItemNode("b", {"2000": 100.0})
    # statistical forecast
    stat = StatisticalGrowthForecastNode(
        base, "2000", ["2001"], distribution_callable=lambda: 0.05
    )
    # calculate should use growth factor 0.05
    assert stat.calculate("2001") == pytest.approx(100.0 * 1.05)
    with pytest.raises(NotImplementedError):
        StatisticalGrowthForecastNode.from_dict({}, {})

    # custom forecast
    custom = CustomGrowthForecastNode(
        base,
        "2000",
        ["2001"],
        growth_function=lambda period, prev_period, prev_value: 0.1,
    )
    assert custom.calculate("2001") == pytest.approx(100.0 * 1.1)
    with pytest.raises(NotImplementedError):
        CustomGrowthForecastNode.from_dict({}, {})
