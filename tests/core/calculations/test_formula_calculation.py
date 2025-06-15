"""Tests for fin_statement_model.core.calculations.calculation.FormulaCalculation.

This module validates the new SimpleEval-powered formula evaluation path, in
particular:
1. Support for the ``//`` (floor-division) operator.
2. Proper error handling for formulas that evaluate to non-numeric results
   (e.g., string constants).
"""

from __future__ import annotations

import pytest

from fin_statement_model.core.calculations.calculation import FormulaCalculation
from fin_statement_model.core.errors import CalculationError
from fin_statement_model.core.nodes.base import Node


class ConstantNode(Node):
    """A simple test node that returns a constant value for any period."""

    def __init__(self, name: str, value: float):
        super().__init__(name)
        self._value = float(value)

    # ------------------------------------------------------------------
    # Node API
    # ------------------------------------------------------------------
    def calculate(self, period: str) -> float:
        return self._value

    def to_dict(self) -> dict[str, float]:
        return {"name": self.name, "value": self._value}


def test_floor_division_operator() -> None:
    """The ``//`` operator should perform floor division and return a float."""

    node_a = ConstantNode("a", 10)
    node_b = ConstantNode("b", 3)

    calc = FormulaCalculation("a // b", ["a", "b"])
    result = calc.calculate([node_a, node_b], "2023")

    assert result == float(10 // 3)


def test_invalid_constant_type_raises() -> None:
    """Formulas that evaluate to non-numeric results must raise CalculationError."""

    # Formula contains a bare string literal – evaluates to str
    calc = FormulaCalculation("'foo'", [])

    with pytest.raises(CalculationError):
        _ = calc.calculate([], "2023")
