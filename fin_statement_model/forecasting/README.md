# Forecasting Submodule — `fin_statement_model.forecasting`

The `forecasting` submodule provides robust, extensible tools for forecasting financial statement items using a variety of methods. It supports both simple and advanced forecasting workflows, batch operations, and custom method integration.

---

## Basic Usage

```python
from fin_statement_model.forecasting.controller import StatementForecaster
from fin_statement_model.forecasting.types import ForecastConfig

# Assume you have a FinancialStatementGraph instance (fsg) with nodes and data
forecaster = StatementForecaster(fsg)

# Forecast 'revenue' for 2024 and 2025 using a simple 5% growth
config = ForecastConfig(method="simple", config=0.05)
forecast = forecaster.forecast_value(
    node_name="revenue",
    forecast_periods=["2024", "2025"],
    forecast_config=config.model_dump(),
)
print(forecast)  # {'2024': 1050.0, '2025': 1102.5}
```

---

## Advanced Features

### 1. Custom Forecast Methods and Configurations

- Use built-in methods: `simple`, `curve`, `statistical`, `average`, `historical_growth`
- Pass method-specific configs (e.g., statistical parameters)

```python
from fin_statement_model.forecasting.types import ForecastConfig

# Statistical method example
stat_cfg = ForecastConfig(
    method="statistical",
    config={"distribution": "normal", "params": {"mean": 0.05, "std": 0.02}}
)
```

### 2. Batch/Multi-Node Forecasting

```python
results = forecaster.forecast_multiple(
    node_names=["revenue", "costs"],
    forecast_periods=["2024", "2025"],
    forecast_configs={
        "revenue": {"method": "simple", "config": 0.05},
        "costs": {"method": "curve", "config": {"points": [100, 110, 120]}}
    }
)
print(results["revenue"].get_value("2024"))
```

### 3. Validation and Error Handling

- All inputs and configs are validated using `ForecastValidator`.
- Errors are raised as subclasses of `ForecastingError` (see `errors.py`).
- Example:

```python
from fin_statement_model.forecasting.validators import ForecastValidator
from fin_statement_model.forecasting.errors import ForecastConfigurationError

try:
    ForecastValidator.validate_forecast_config({"method": "bad_method", "config": {}})
except ForecastConfigurationError as e:
    print("Config error:", e)
```

### 4. Extensibility

- Add new forecast methods by subclassing `BaseForecastMethod` and registering them.
- All method logic is modular and discoverable.

---

## API Overview

- **`StatementForecaster`**: Main entry point for forecasting operations (mutating and non-mutating)
- **`ForecastConfig`**: Pydantic model for method/config specification
- **`ForecastResult`**: Pydantic model for structured forecast results
- **`ForecastValidator`**: Static validation utilities for inputs, configs, and results
- **`ForecastingError`** and subclasses: Robust error handling for all forecast operations

All public classes and methods are documented with Google-style docstrings and include doctest examples. See the code for details.

---

## Type Safety & Error Classes

- All configs and results use Pydantic models for type safety and validation.
- Errors are raised as subclasses of `ForecastingError` (e.g., `ForecastNodeError`, `ForecastMethodError`).
- See `types.py` and `errors.py` for details.

---

## Configuration & Architecture Notes

- The forecasting layer is modular and extensible.
- Batch and single-node operations are both supported.
- All validation is centralized in `validators.py`.
- The codebase enforces Google-style docstrings and type annotations.
- The old monolithic `forecaster.py` has been replaced by a subpackage structure:
  - `controller.py` (main API)
  - `node_forecast.py` (per-node logic)
  - `batch.py` (batch/multi-node logic)
  - `methods/` (all built-in forecasting methods)
  - `types.py`, `validators.py`, `errors.py` (supporting types, validation, and error handling)

---

## Further Reading

- See the codebase and docstrings for detailed usage and examples.
- For more advanced scenarios, see the `examples/` directory and the API documentation. 