# Forecasting Module

The Forecasting module provides tools for generating future values for financial statement graphs. It supports mutating and non-mutating operations, multiple forecasting methods, period management, and extensibility.

## Overview

- **Mutating forecasts** (`create_forecast`): Add forecast periods to the graph and update node values in-place.
- **Non-mutating forecasts** (`forecast_value`, `forecast_multiple`, `forecast_all`): Compute and return forecast values without modifying the graph.
- **Forecast methods**:
  - `simple` – constant growth rate
  - `curve` – variable growth rates per period
  - `statistical` – random sampling from distributions
  - `average` – historical average
  - `historical_growth` – average historical growth rate
- **Period management**: Infer and validate historical and forecast periods.
- **Registry**: Dynamically register and retrieve methods via `ForecastMethodRegistry` and convenience functions.
- **Validation**: Ensure inputs and results are valid via `ForecastValidator`.
- **Types & Errors**: Use Pydantic models (`ForecastConfig`, `ForecastResult`, `StatisticalConfig`) and custom exceptions for robust handling.

## Basic Usage

### Initialize Forecaster

```python
from fin_statement_model.forecasting import StatementForecaster

# Assume `graph` is your FinancialStatementGraph instance
forecaster = StatementForecaster(graph)
```

### Mutating Forecast

```python
forecaster.create_forecast(
    forecast_periods=["2024", "2025"],
    node_configs={
        "revenue": {"method": "simple", "config": 0.05},
        "costs": {"method": "curve", "config": [0.03, 0.04]},
    },
)
```

### Non-Mutating Forecast

```python
values = forecaster.forecast_value(
    "revenue",
    forecast_periods=["2024", "2025"],
    forecast_config={"method": "simple", "config": 0.05},
)
print(values)  # {'2024': 1050.0, '2025': 1102.5}
```

### Forecast Multiple Nodes

```python
results = forecaster.forecast_multiple(
    ["revenue", "costs"],
    ["2024", "2025"],
    forecast_configs={"revenue": {"method": "simple", "config": 0.05}},
)
print(results["revenue"].get_value("2024"))
```

## Adding a New Forecasting Method

1. **Create a new module** in `fin_statement_model/forecasting/methods`, e.g. `my_method.py`.
2. **Define your method** by subclassing `BaseForecastMethod`:

    ```python
    from typing import Any, Dict
    from fin_statement_model.core.nodes import Node
    from .base import BaseForecastMethod

    class MyForecastMethod(BaseForecastMethod):
        """Forecast using a custom strategy."""

        @property
        def name(self) -> str:
            return "my_method"

        @property
        def internal_type(self) -> str:
            return "my_method"

        def validate_config(self, config: Any) -> None:
            # Validate your config here
            ...

        def normalize_params(
            self, config: Any, forecast_periods: list[str]
        ) -> Dict[str, Any]:
            # Convert config to growth_params for the node factory
            return {"forecast_type": self.internal_type, "growth_params": ...}

        def prepare_historical_data(
            self, node: Node, historical_periods: list[str]
        ) -> list[float]:
            # Optional: implement if your method relies on historical data
            ...
    ```

3. **Register the method** at runtime:

    ```python
    from fin_statement_model.forecasting.strategies import register_forecast_method
    from fin_statement_model.forecasting.methods.my_method import MyForecastMethod

    register_forecast_method(MyForecastMethod())
    ```

4. **Use your method**:

    ```python
    forecaster.create_forecast(
        forecast_periods=["2024", "2025"],
        node_configs={"custom": {"method": "my_method", "config": {/* your params */}}},
    )
    ```

## Further Reference

- Explore the `fin_statement_model/forecasting/methods` folder for built-in implementations.
- Review `ForecastValidator` for input and result validation.
- Consult `ForecastMethodRegistry` and related helpers for advanced usage. 