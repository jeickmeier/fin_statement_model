"""
Financial forecasting module for the fin_statement_model package.

This module provides classes for creating forecasts of financial values
based on historical data using various forecasting methods.
"""

from .forecasts import (
    ForecastNode,
    FixedGrowthForecastNode,
    CurveGrowthForecastNode,
    StatisticalGrowthForecastNode,
    CustomGrowthForecastNode,
    AverageValueForecastNode,
    AverageHistoricalGrowthForecastNode,
)

__all__ = [
    "ForecastNode",
    "FixedGrowthForecastNode",
    "CurveGrowthForecastNode",
    "StatisticalGrowthForecastNode",
    "CustomGrowthForecastNode",
    "AverageValueForecastNode",
    "AverageHistoricalGrowthForecastNode",
]
