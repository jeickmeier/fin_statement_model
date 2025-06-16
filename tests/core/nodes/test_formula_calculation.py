"""Standalone tests for :class:`fin_statement_model.core.nodes.calculation_nodes.FormulaCalculationNode`.

Validates that the SimpleEval-powered formula evaluation supports:

1. The ``//`` (floor-division) operator.
2. Proper error handling when a formula evaluates to a non-numeric result.
"""

from __future__ import annotations

import pytest

from fin_statement_model.core.errors import CalculationError
from fin_statement_model.core.nodes.base import Node
from fin_statement_model.core.nodes.calculation_nodes import FormulaCalculationNode


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

    calc_node = FormulaCalculationNode(
        "floor_div", inputs={"a": node_a, "b": node_b}, formula="a // b"
    )
    result = calc_node.calculate("2023")

    assert result == float(10 // 3)


def test_invalid_constant_type_raises() -> None:
    """Formulas that evaluate to non-numeric results must raise CalculationError."""

    # Use FormulaCalculationNode and expect CalculationError wrapped
    calc_node = FormulaCalculationNode("bad_const", inputs={}, formula="'foo'")

    with pytest.raises(CalculationError):
        _ = calc_node.calculate("2023")
