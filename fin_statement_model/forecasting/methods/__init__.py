"""Forecast method implementations.

This module contains all the built-in forecast methods available in the library.
"""

from .base import ForecastMethod, BaseForecastMethod
from .simple import SimpleForecastMethod
from .curve import CurveForecastMethod
from .statistical import StatisticalForecastMethod
from .average import AverageForecastMethod
from .historical_growth import HistoricalGrowthForecastMethod

__all__ = [
    "AverageForecastMethod",
    "BaseForecastMethod",
    "CurveForecastMethod",
    "ForecastMethod",
    "HistoricalGrowthForecastMethod",
    "SimpleForecastMethod",
    "StatisticalForecastMethod",
]
