"""Calculations module for the Financial Statement Model.

This module provides classes for implementing the Calculation Pattern for calculations
in the Financial Statement Model. It allows different calculation algorithms to be
defined, registered, and applied to financial data.
"""

from .calculation import (
    AdditionCalculation,
    Calculation,
    CustomFormulaCalculation,
    DivisionCalculation,
    FormulaCalculation,
    MultiplicationCalculation,
    SubtractionCalculation,
    WeightedAverageCalculation,
)
from .registry import Registry

# Register calculations
Registry.register(AdditionCalculation)
Registry.register(SubtractionCalculation)
Registry.register(MultiplicationCalculation)
Registry.register(DivisionCalculation)
Registry.register(WeightedAverageCalculation)
Registry.register(CustomFormulaCalculation)
Registry.register(FormulaCalculation)

__all__ = [
    "AdditionCalculation",
    "Calculation",
    "CustomFormulaCalculation",
    "DivisionCalculation",
    "FormulaCalculation",
    "MultiplicationCalculation",
    "Registry",
    "SubtractionCalculation",
    "WeightedAverageCalculation",
]
