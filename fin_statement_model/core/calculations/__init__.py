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
    ...     def __init__(self, value):
    ...         self._value = value
    ...
    ...     def calculate(self, period):
    ...         return self._value
    >>> nodes = [MockNode(10), MockNode(20)]
    >>> calc = AdditionCalculation()
    >>> calc.calculate(nodes, "2023Q4")
    30.0
    >>> CalcClass = Registry.get("AdditionCalculation")
    >>> calc2 = CalcClass()
    >>> calc2.calculate(nodes, "2023Q4")
    30.0
"""

from fin_statement_model.core.node_factory import NodeFactory as _NodeFactory
from fin_statement_model.core.node_factory.registries import (
    CalculationAliasRegistry as _CalcRegistry,
    calc_alias,
)

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

# Alias mapping used by Graph APIs → Calculation classes
calc_alias("addition")(AdditionCalculation)
calc_alias("subtraction")(SubtractionCalculation)
calc_alias("multiplication")(MultiplicationCalculation)
calc_alias("division")(DivisionCalculation)
calc_alias("weighted_average")(WeightedAverageCalculation)
calc_alias("custom_formula")(CustomFormulaCalculation)
calc_alias("formula")(FormulaCalculation)

# ---------------------------------------------------------------------------
# Ensure NodeFactory alias mapping is kept in sync
# ---------------------------------------------------------------------------
# ``NodeFactory`` takes a snapshot of the alias registry at import time.  If it
# was imported *before* the calculations package finished registering its
# aliases the mapping may be stale which leads to look-ups such as
# ``Graph.change_calculation_method(..., "addition")`` failing at runtime.  To
# guard against this we always (re-)populate the mapping *after* the official
# registrations above.

# Overwrite the snapshot with the current registry content so any aliases added
# later (including by extensions) are reflected immediately.
_NodeFactory._calculation_methods = {alias: cls.__name__ for alias, cls in _CalcRegistry.items()}

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
