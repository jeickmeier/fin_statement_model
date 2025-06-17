"""Calculation strategies for the Financial Statement Model.

This package provides a flexible, extensible system for defining and applying calculation algorithms to financial model nodes. It includes:

- Abstract base class `Calculation` for all calculation strategies.
- Built-in calculation types:
    - AdditionCalculation: Sums input node values.
    - SubtractionCalculation: First input minus sum of the rest.
    - MultiplicationCalculation: Product of all input node values.
    - DivisionCalculation: First input divided by product of the rest.
    - WeightedAverageCalculation: Weighted or simple average of input node values.
    - CustomFormulaCalculation: User-supplied Python function for custom logic.
    - FormulaCalculation: Evaluates a mathematical formula string using named variables.
- A global `Registry` for registering and retrieving calculation classes by name.
- Extensibility: Users can define and register their own calculation types.

Example:
    >>> from fin_statement_model.core.calculations import AdditionCalculation, Registry
    >>> class MockNode:
    ...     def __init__(self, value): self._value = value
    ...     def calculate(self, period): return self._value
    >>> nodes = [MockNode(10), MockNode(20)]
    >>> calc = AdditionCalculation()
    >>> calc.calculate(nodes, '2023Q4')
    30.0
    >>> CalcClass = Registry.get('AdditionCalculation')
    >>> calc2 = CalcClass()
    >>> calc2.calculate(nodes, '2023Q4')
    30.0
"""

from .calculation import (
    Calculation,
    AdditionCalculation,
    SubtractionCalculation,
    MultiplicationCalculation,
    DivisionCalculation,
    WeightedAverageCalculation,
    CustomFormulaCalculation,
    FormulaCalculation,
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
