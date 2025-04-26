"""Unit tests for the StatementForecaster class in the statements forecasting module.
"""

import pytest
from fin_statement_model.statements.graph.financial_graph import FinancialStatementGraph

def test_simple_growth_forecast_mutates_graph() -> None:
    """Test that create_forecast with simple method mutates the graph node values correctly."""
    # Set up graph with historical periods and one item
    fsg = FinancialStatementGraph(periods=["2020", "2021", "2022"])
    fsg.add_financial_statement_item("item", {"2020": 100.0, "2021": 110.0, "2022": 121.0})

    # Forecast two periods at 10% growth
    forecast_periods = ["2023", "2024"]
    node_configs = {"item": {"method": "simple", "config": 0.1}}
    fsg.forecaster.create_forecast(forecast_periods, node_configs)

    # Verify forecasted values
    node = fsg.get_node("item")
    expected_2023 = 121.0 * 1.1
    expected_2024 = expected_2023 * 1.1
    assert pytest.approx(expected_2023) == node.values["2023"]
    assert pytest.approx(expected_2024) == node.values["2024"]


def test_forecast_value_does_not_mutate_graph() -> None:
    """Test that forecast_value does not mutate the original graph values or periods."""
    # Set up graph
    fsg = FinancialStatementGraph(periods=["2020", "2021", "2022"])
    fsg.add_financial_statement_item("item", {"2020": 100.0, "2021": 110.0, "2022": 121.0})

    # Snapshot original state
    original_periods = list(fsg.periods)
    original_values = dict(fsg.get_node("item").values)

    # Use forecast_value to compute without mutation
    forecast_periods = ["2023"]
    forecast_config = {"method": "simple", "config": 0.2}
    result = fsg.forecaster.forecast_value(
        node_name="item",
        forecast_periods=forecast_periods,
        forecast_config=forecast_config,
    )

    # Return value should match expected
    assert result == {"2023": pytest.approx(121.0 * 1.2)}

    # Graph state remains unchanged
    assert fsg.periods == original_periods
    assert dict(fsg.get_node("item").values) == original_values


def test_curve_growth_forecast() -> None:
    """Test that create_forecast with curve growth applies rate list correctly."""
    fsg = FinancialStatementGraph(periods=["2020", "2021", "2022"])
    fsg.add_financial_statement_item("item", {"2020": 100.0, "2021": 110.0, "2022": 121.0})

    forecast_periods = ["2023", "2024"]
    node_configs = {"item": {"method": "curve", "config": [0.05, 0.1]}}
    fsg.forecaster.create_forecast(forecast_periods, node_configs)

    node = fsg.get_node("item")
    assert pytest.approx(121.0 * 1.05) == node.values["2023"]
    assert pytest.approx(121.0 * 1.1) == node.values["2024"]
