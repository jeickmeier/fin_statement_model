# Calculations

The `fin_statement_model.core.calculations` package provides a suite of calculation strategies for financial model nodes.

## Functionality

- Defines the abstract `Calculation` base class.
- Implements built-in calculation types:
  - `AdditionCalculation`
  - `SubtractionCalculation`
  - `MultiplicationCalculation`
  - `DivisionCalculation`
  - `WeightedAverageCalculation`
  - `CustomFormulaCalculation`
  - `FormulaCalculation`
- Uses a global `Registry` to register and retrieve calculation classes by name.

## Basic Usage

```python
from fin_statement_model.core.calculations import AdditionCalculation, Registry

# Instantiate a calculation
calc = AdditionCalculation()
# Use nodes (must implement calculate(period) -> float)
result = calc.calculate([node_a, node_b, node_c], '2023Q4')
print(f'Sum: {result}')

# Retrieve calculation class by name and instantiate
CalcClass = Registry.get('AdditionCalculation')
calc2 = CalcClass()
result2 = calc2.calculate([node_a, node_b], '2023Q4')
print(f'Sum via registry: {result2}')
```

## Adding a New Calculation Type

1. Create a new class subclassing `Calculation` (in the same module or separate file):

```python
from fin_statement_model.core.calculations.calculation import Calculation
from fin_statement_model.core.nodes.base import Node
from fin_statement_model.core.errors import CalculationError

class DoubleCalculation(Calculation):
    '''Custom calculation: doubles the value of the first input node.'''

    def calculate(self, inputs: list[Node], period: str) -> float:
        if not inputs:
            raise CalculationError('DoubleCalculation requires at least one input')
        value = inputs[0].calculate(period)
        return value * 2

    @property
    def description(self) -> str:
        return 'Double First Input'
```

2. Register the new calculation with the global registry:

```python
from fin_statement_model.core.calculations.registry import Registry

Registry.register(DoubleCalculation)
```

3. (Optional) Import and expose your class in `fin_statement_model/core/calculations/__init__.py`:

```python
from .double_calculation import DoubleCalculation

__all__.append('DoubleCalculation')
```

After these steps, `DoubleCalculation` behaves like any other built-in calculation.

---

This README describes the core calculation strategies and guides you on extending them with custom logic. 