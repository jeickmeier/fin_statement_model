"""Provide forecasting capabilities for financial statement graphs.

This sub-module offers:
- Multiple forecast methods (simple, curve, statistical, average, historical_growth)
- Mutating and non-mutating forecast operations on graphs
- Extensible registry for custom forecast methods
- Utilities for period management and validation

Example:
    >>> from fin_statement_model.forecasting import StatementForecaster
    >>> forecaster = StatementForecaster(graph)
    >>>
    >>> # Mutating forecast - modifies the graph
    >>> forecaster.create_forecast(
    ...     forecast_periods=["2024", "2025"],
    ...     node_configs={
    ...         "revenue": {"method": "simple", "config": 0.05},
    ...         "costs": {"method": "curve", "config": [0.03, 0.04]}
    ...     }
    ... )
    >>>
    >>> # Non-mutating forecast - returns values without modifying graph
    >>> values = forecaster.forecast_value(
    ...     "revenue",
    ...     forecast_periods=["2024", "2025"],
    ...     forecast_config={"method": "simple", "config": 0.05}
    ... )
"""

# Main forecaster class
# Error classes
from .errors import (
    ForecastConfigurationError,
    ForecastingError,
    ForecastMethodError,
    ForecastNodeError,
    ForecastResultError,
)
from .forecaster import StatementForecaster

# Forecast methods
from .methods import (
    AverageForecastMethod,
    BaseForecastMethod,
    CurveForecastMethod,
    ForecastMethod,
    HistoricalGrowthForecastMethod,
    SimpleForecastMethod,
    StatisticalForecastMethod,
)

# Utilities
from .period_manager import PeriodManager

# Registry and strategies
from .strategies import (
    ForecastMethodRegistry,
    forecast_registry,
    get_forecast_method,
    register_forecast_method,
)

# Types
from .types import (
    ForecastConfig,
    ForecastMethodType,
    ForecastResult,
    StatisticalConfig,
)
from .validators import ForecastValidator

__all__ = [
    "AverageForecastMethod",
    "BaseForecastMethod",
    "CurveForecastMethod",
    "ForecastConfig",
    "ForecastConfigurationError",
    "ForecastMethod",
    "ForecastMethodError",
    "ForecastMethodRegistry",
    "ForecastMethodType",
    "ForecastNodeError",
    "ForecastResult",
    "ForecastResultError",
    "ForecastValidator",
    "ForecastingError",
    "HistoricalGrowthForecastMethod",
    "PeriodManager",
    "SimpleForecastMethod",
    "StatementForecaster",
    "StatisticalConfig",
    "StatisticalForecastMethod",
    "forecast_registry",
    "get_forecast_method",
    "register_forecast_method",
]
