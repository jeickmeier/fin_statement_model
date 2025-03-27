"""
Calculations module for the Financial Statement Model.

This module provides classes for implementing the Strategy Pattern for calculations
in the Financial Statement Model. It allows different calculation algorithms to be
defined, registered, and applied to financial data.
"""

from .calculation_strategy import (
    CalculationStrategy,
    AdditionStrategy,
    SubtractionStrategy,
    MultiplicationStrategy,
    DivisionStrategy,
    WeightedAverageStrategy,
    CustomFormulaStrategy,
)
from .strategy_registry import CalculationStrategyRegistry

__all__ = [
    "CalculationStrategy",
    "AdditionStrategy",
    "SubtractionStrategy",
    "MultiplicationStrategy",
    "DivisionStrategy",
    "WeightedAverageStrategy",
    "CustomFormulaStrategy",
    "CalculationStrategyRegistry",
]
