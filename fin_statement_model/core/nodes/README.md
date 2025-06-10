# fin_statement_model.core.nodes

This package provides the building blocks for the financial statement model graph. Nodes represent data points, calculations, statistics, and forecasts on financial statement items.

## Overview of Node Types

### Base Node
- **Node** (abstract): Defines the interface for all nodes:
  - `calculate(period: str) -> float`
  - `to_dict() -> dict`
  - Optional: `clear_cache()`, `get_dependencies()`

### Data Nodes
- **FinancialStatementItemNode**: Leaf node storing raw financial data for named periods.

### Calculation Nodes
- **CalculationNode**: Delegates computation to a `Calculation` object.
- **FormulaCalculationNode**: Evaluates string formulas (e.g., `"rev - cost"`).
- **CustomCalculationNode**: Invokes a Python callable on input node values.

### Statistical Nodes
- **YoYGrowthNode**: Computes year-over-year growth: `(current - prior)/prior`.
- **MultiPeriodStatNode**: Applies a statistical function (mean, stdev, etc.) over multiple periods.
- **TwoPeriodAverageNode**: Averages values from two specified periods.

### Forecast Nodes
- **ForecastNode** (abstract): Base class for projecting future values from historical data.
- **FixedGrowthForecastNode**: Applies a constant growth rate each period.
- **CurveGrowthForecastNode**: Uses a list of growth rates, one per forecast period.
- **StatisticalGrowthForecastNode**: Samples growth rates from a distribution (e.g., Monte Carlo).
- **CustomGrowthForecastNode**: Calls a user-supplied function to compute growth factors.
- **AverageValueForecastNode**: Projects the historical average forward.
- **AverageHistoricalGrowthForecastNode**: Projects using the average historical growth rate.

### Registry & Helpers
- **standard_node_registry**: Global registry of canonical node names and their metadata.
- **is_calculation_node(node)**: Helper to detect nodes that compute (vs. store) values.

## Getting Started: Basic Usage

```python
from fin_statement_model.core.nodes import (
    FinancialStatementItemNode,
    FormulaCalculationNode,
    YoYGrowthNode,
    FixedGrowthForecastNode,
    is_calculation_node,
)

# 1. Create a data node
revenue = FinancialStatementItemNode('revenue', {'2022': 1000.0, '2023': 1200.0})

# 2. Use a formula node: gross profit = revenue - COGS
cogs = FinancialStatementItemNode('cogs', {'2022': 400.0, '2023': 500.0})
gp = FormulaCalculationNode('gross_profit', inputs={'rev': revenue, 'cost': cogs}, formula='rev - cost')
print(gp.calculate('2023'))  # 700.0

# 3. Compute YoY growth
yoy = YoYGrowthNode('revenue_yoy', input_node=revenue, prior_period='2022', current_period='2023')
print(round(yoy.calculate(), 2))  # 0.20 (20%)

# 4. Forecast revenue at 5% growth
forecast = FixedGrowthForecastNode(revenue, '2023', ['2024', '2025'], 0.05)
print(round(forecast.calculate('2025'), 2))  # ~1381.58

# 5. Check if a node performs calculation
print(is_calculation_node(revenue))  # False
print(is_calculation_node(gp))       # True
```

## Adding a New Node Type

1. **Create the Node Class**
   - Add a new file under `core/nodes/`, e.g. `my_custom_node.py`.
   - Define a class inheriting `Node`.
   - Implement at minimum:
     - `calculate(self, period: str) -> float`
     - `to_dict(self) -> dict`
     - `@staticmethod from_dict_with_context(data, context) -> YourNode`
   - Override `get_dependencies()` if your node depends on other nodes.
   - Override `clear_cache()` if your node caches results.

2. **Integrate into the Package**
   - Import your node in `core/nodes/__init__.py`.
   - Add the class name to the `__all__` list.

3. **Register as a Calculation Node (optional)**
   - If your node should be recognized as a calculation node, update `is_calculation_node` doc or logic as needed.

4. **Write Tests**
   - Create a test file under `tests/core/nodes/`, e.g. `test_my_custom_node.py`.
   - Ensure ≥80% coverage, include edge cases, and validate serialization.

5. **Lint, Format, Type-Check, and Test**
   ```bash
   black . && ruff . && mypy .
   pytest --cov=fin_statement_model
   ```

Following these steps ensures consistency, discoverability, and maintainability of new node types in the financial statement model library. 