"""Calculations module for the Financial Statement Model.

This module provides classes for implementing the Calculation Pattern for calculations
in the Financial Statement Model. It allows different calculation algorithms to be
defined, registered, and applied to financial data.
"""

from .calculation import (
    Calculation,
    AdditionCalculation,
    SubtractionCalculation,
    MultiplicationCalculation,
    DivisionCalculation,
    WeightedAverageCalculation,
    CustomFormulaCalculation,
)
from .registry import Registry

# Register calculations
Registry.register(AdditionCalculation)
Registry.register(SubtractionCalculation)
Registry.register(MultiplicationCalculation)
Registry.register(DivisionCalculation)
Registry.register(WeightedAverageCalculation)
Registry.register(CustomFormulaCalculation)

__all__ = [
    "AdditionCalculation",
    "Calculation",
    "CustomFormulaCalculation",
    "DivisionCalculation",
    "MultiplicationCalculation",
    "Registry",
    "SubtractionCalculation",
    "WeightedAverageCalculation",
]
