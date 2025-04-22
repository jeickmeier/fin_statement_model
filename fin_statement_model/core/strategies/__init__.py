"""Strategies module for the Financial Statement Model.

This module provides classes for implementing the Strategy Pattern for calculations
in the Financial Statement Model. It allows different calculation algorithms to be
defined, registered, and applied to financial data.
"""

from .strategy import (
    Strategy,
    AdditionStrategy,
    SubtractionStrategy,
    MultiplicationStrategy,
    DivisionStrategy,
    WeightedAverageStrategy,
    CustomFormulaStrategy,
)
from .registry import Registry

# Register strategies
Registry.register(AdditionStrategy)
Registry.register(SubtractionStrategy)
Registry.register(MultiplicationStrategy)
Registry.register(DivisionStrategy)
Registry.register(WeightedAverageStrategy)
Registry.register(CustomFormulaStrategy)

__all__ = [
    "AdditionStrategy",
    "CustomFormulaStrategy",
    "DivisionStrategy",
    "MultiplicationStrategy",
    "Registry",
    "Strategy",
    "SubtractionStrategy",
    "WeightedAverageStrategy",
]
