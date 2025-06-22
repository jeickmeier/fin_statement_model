import pytest

from fin_statement_model.core.calculations import (
    AdditionCalculation,
    SubtractionCalculation,
    MultiplicationCalculation,
    DivisionCalculation,
    WeightedAverageCalculation,
    CustomFormulaCalculation,
)
from fin_statement_model.core.errors import CalculationError, StrategyError


class DummyNode:  # Minimal stand-in for Node API
    def __init__(self, value: float):
        self._value = value

    def calculate(self, period: str) -> float:  # noqa: D401 – imperative style
        return self._value


PERIOD = "2023"


def test_addition() -> None:
    calc = AdditionCalculation()
    nodes = [DummyNode(1), DummyNode(2), DummyNode(3)]
    assert calc.calculate(nodes, PERIOD) == 6


def test_subtraction() -> None:
    calc = SubtractionCalculation()
    nodes = [DummyNode(10), DummyNode(3), DummyNode(2)]
    assert calc.calculate(nodes, PERIOD) == 5  # 10 – (3+2)


def test_multiplication() -> None:
    calc = MultiplicationCalculation()
    nodes = [DummyNode(2), DummyNode(5)]
    assert calc.calculate(nodes, PERIOD) == 10


def test_division() -> None:
    calc = DivisionCalculation()
    nodes = [DummyNode(100), DummyNode(5), DummyNode(2)]
    assert calc.calculate(nodes, PERIOD) == 10  # 100 / (5*2)


def test_division_by_zero_raises() -> None:
    calc = DivisionCalculation()
    nodes = [DummyNode(10), DummyNode(0)]

    with pytest.raises(CalculationError):
        calc.calculate(nodes, PERIOD)


def test_weighted_average_equal_weights() -> None:
    calc = WeightedAverageCalculation()
    nodes = [DummyNode(10), DummyNode(20), DummyNode(30)]
    assert calc.calculate(nodes, PERIOD) == 20


def test_weighted_average_custom_weights() -> None:
    calc = WeightedAverageCalculation(weights=[0.5, 0.3, 0.2])
    nodes = [DummyNode(10), DummyNode(20), DummyNode(30)]
    assert calc.calculate(nodes, PERIOD) == pytest.approx(17.0)


def test_weighted_average_bad_weights() -> None:
    calc = WeightedAverageCalculation(weights=[0.5, 0.5])
    nodes = [DummyNode(10), DummyNode(20), DummyNode(30)]
    with pytest.raises(StrategyError):
        calc.calculate(nodes, PERIOD)


def test_custom_formula() -> None:
    def simple_sum(d: dict[str, float]) -> float:
        return d["input_0"] + d["input_1"]

    calc = CustomFormulaCalculation(simple_sum)
    nodes = [DummyNode(3), DummyNode(7)]
    assert calc.calculate(nodes, PERIOD) == 10
