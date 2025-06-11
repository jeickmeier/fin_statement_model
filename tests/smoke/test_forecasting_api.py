from fin_statement_model.core.graph.graph import Graph
from fin_statement_model.forecasting import StatementForecaster


def test_forecasting_api_simple() -> None:
    """Verify StatementForecaster.forecast_value returns expected length and dtype."""
    graph = Graph(periods=["2023"])
    graph.add_financial_statement_item("revenue", {"2023": 100.0})

    forecaster = StatementForecaster(graph)
    forecast_periods = ["2024", "2025", "2026", "2027"]

    results = forecaster.forecast_value(
        "revenue",
        forecast_periods=forecast_periods,
        forecast_config={"method": "simple", "config": 0.05},
    )

    assert list(results.keys()) == forecast_periods, "Forecast periods mismatch"
    for value in results.values():
        assert isinstance(value, float), "Forecast value is not a float"
        assert value > 0, "Forecast value should be positive"
