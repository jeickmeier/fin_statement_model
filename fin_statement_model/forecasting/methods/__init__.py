"""Built-in forecast method implementations for financial statement modeling.

This module exports all built-in forecast methods available in the library. These methods can be
used with the forecasting engine to generate future values for financial statement nodes.

Available methods:
    - SimpleForecastMethod: Constant growth rate for all periods.
    - CurveForecastMethod: Variable growth rates per period (list or single value).
    - AverageForecastMethod: Uses the historical average of available data.
    - HistoricalGrowthForecastMethod: Uses the average historical growth rate.
    - StatisticalForecastMethod: Samples from a statistical distribution (normal, uniform).

Example:
    >>> from fin_statement_model.forecasting.methods import SimpleForecastMethod, CurveForecastMethod
    >>> simple = SimpleForecastMethod()
    >>> curve = CurveForecastMethod()
    >>> simple.get_forecast_params(0.05, ["2024", "2025"])
    {'forecast_type': 'simple', 'growth_params': 0.05}
    >>> curve.get_forecast_params([0.05, 0.04], ["2024", "2025"])
    {'forecast_type': 'curve', 'growth_params': [0.05, 0.04]}
"""

from .average import AverageForecastMethod
from .base import BaseForecastMethod, ForecastMethod
from .curve import CurveForecastMethod
from .historical_growth import HistoricalGrowthForecastMethod
from .simple import SimpleForecastMethod
from .statistical import StatisticalForecastMethod

__all__ = [
    "AverageForecastMethod",
    "BaseForecastMethod",
    "CurveForecastMethod",
    "ForecastMethod",
    "HistoricalGrowthForecastMethod",
    "SimpleForecastMethod",
    "StatisticalForecastMethod",
]
