"""Provide built-in forecast method implementations.

This module exports all built-in forecast methods available in the library.
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
