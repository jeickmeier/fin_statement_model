# Calculations

The `fin_statement_model.core.calculations` package provides a flexible, extensible system for defining and applying calculation strategies to financial model nodes.

## Overview

- **Abstract base class:** `Calculation` defines the interface for all calculation strategies.
- **Built-in calculation types:**
  - `AdditionCalculation`: Sums input node values.
  - `SubtractionCalculation`: First input minus sum of the rest.
  - `MultiplicationCalculation`: Product of all input node values.
  - `DivisionCalculation`: First input divided by product of the rest.
  - `WeightedAverageCalculation`: Weighted or simple average of input node values.
  - `CustomFormulaCalculation`: User-supplied Python function for custom logic.
  - `FormulaCalculation`: Evaluates a mathematical formula string using named variables.
- **Global Registry:** Register and retrieve calculation classes by name.
- **Extensibility:** Easily add and register your own calculation types.

## Basic Usage

```python
from fin_statement_model.core.calculations import (
    AdditionCalculation, SubtractionCalculation, MultiplicationCalculation,
    DivisionCalculation, WeightedAverageCalculation, Registry
)

class MockNode:
    def __init__(self, value): self._value = value
    def calculate(self, period): return self._value

nodes = [MockNode(10), MockNode(20), MockNode(5)]

# Addition
add = AdditionCalculation()
print(add.calculate(nodes, '2023Q4'))  # 35.0

# Subtraction
sub = SubtractionCalculation()
print(sub.calculate(nodes, '2023Q4'))  # -15.0

# Multiplication
mul = MultiplicationCalculation()
print(mul.calculate(nodes, '2023Q4'))  # 1000.0

# Division
div = DivisionCalculation()
print(div.calculate([MockNode(100), MockNode(5), MockNode(2)], '2023Q4'))  # 10.0

# Weighted Average (equal weights by default)
wa = WeightedAverageCalculation()
print(wa.calculate(nodes, '2023Q4'))  # 11.666...

# Weighted Average (custom weights)
wa_custom = WeightedAverageCalculation(weights=[0.5, 0.3, 0.2])
print(wa_custom.calculate(nodes, '2023Q4'))  # 11.0

# Using the Registry
div_cls = Registry.get('DivisionCalculation')
div2 = div_cls()
print(div2.calculate([MockNode(100), MockNode(5), MockNode(2)], '2023Q4'))  # 10.0
```

## Advanced Usage

### Custom Python Formula

```python
from fin_statement_model.core.calculations import CustomFormulaCalculation

def gross_profit_margin(data):
    return (data['revenue'] - data['cogs']) / data['revenue'] * 100

class MockNode:
    def __init__(self, name, value): self.name = name; self._value = value
    def calculate(self, period): return self._value

nodes = [MockNode('revenue', 1000), MockNode('cogs', 600)]
calc = CustomFormulaCalculation(gross_profit_margin)
print(calc.calculate(nodes, '2023Q4'))  # 40.0
```

### Formula String Calculation

```python
from fin_statement_model.core.calculations import FormulaCalculation

class MockNode:
    def __init__(self, value): self._value = value
    def calculate(self, period): return self._value

nodes = [MockNode(10), MockNode(5)]
calc = FormulaCalculation('a + b * 2', ['a', 'b'])
print(calc.calculate(nodes, '2023Q4'))  # 20.0
```

## Extending: Adding a New Calculation Type

1. **Create a new class subclassing `Calculation`:**

```python
from fin_statement_model.core.calculations.calculation import Calculation
from fin_statement_model.core.nodes.base import Node
from fin_statement_model.core.errors import CalculationError

class DoubleCalculation(Calculation):
    """Custom calculation: doubles the value of the first input node."""
    def calculate(self, inputs: list[Node], period: str) -> float:
        if not inputs:
            raise CalculationError('DoubleCalculation requires at least one input')
        value = inputs[0].calculate(period)
        return value * 2
    @property
    def description(self) -> str:
        return 'Double First Input'
```

2. **Register the new calculation with the global registry:**

```python
from fin_statement_model.core.calculations.registry import Registry
Registry.register(DoubleCalculation)
```

3. **(Optional) Expose your class in `__init__.py`:**

```python
from .double_calculation import DoubleCalculation
__all__.append('DoubleCalculation')
```

After these steps, `DoubleCalculation` behaves like any other built-in calculation.

## Troubleshooting & FAQ

- **Q: I get a `KeyError` when using `Registry.get('MyCalculation')`.**
  - A: Make sure you registered your calculation class with `Registry.register(MyCalculation)` and that the class name matches exactly.

- **Q: My custom calculation fails with a type error.**
  - A: Ensure your `calculate` method returns a float and that all input nodes implement `calculate(period)`.

- **Q: How do I use node names in custom formulas?**
  - A: If your nodes have a `name` attribute, it will be used as the key in the data dictionary for `CustomFormulaCalculation`.

- **Q: Can I use more complex math in `FormulaCalculation`?**
  - A: Only basic arithmetic (+, -, *, /, unary -) is supported for safety. For advanced logic, use `CustomFormulaCalculation`.

---

This README describes the core calculation strategies and guides you on extending them with custom logic. 