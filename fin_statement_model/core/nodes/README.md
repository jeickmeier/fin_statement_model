# fin_statement_model.core.nodes

This package provides the building blocks for the financial statement model graph. Nodes represent data points, calculations, statistics, and forecasts on financial statement items.

## Features
- Abstract base class for all node types (`Node`)
- Data nodes for storing raw financial data
- Calculation nodes for formulas, custom logic, and delegated calculations
- Statistical nodes for time-series analysis (growth, averages, statistics)
- Forecast nodes for projecting future values
- Standard node registry for canonical names and metadata
- Helper utilities for node introspection and validation

## Google-Style Docstrings
All public classes and methods use Google-style docstrings, including:
- 1-line imperative summary
- Args/Returns sections with blank lines before each
- Working doctest examples
- Clear description of parameters, return values, and exceptions

## Basic Usage
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

## Advanced Features
- **Custom Calculation Nodes**: Use Python callables for bespoke logic (not serializable).
- **Multi-Period Statistics**: Compute mean, stdev, or custom stats over periods.
- **Forecasting**: Project values using fixed, curve, statistical, or custom growth.
- **Node Serialization**: All nodes support `to_dict()` for serialization and a unified `from_dict(cls, data, context=None)` classmethod for deserialization. Nodes with dependencies (e.g., calculation, forecast, stat nodes) require a `context` mapping of node names to node objects. Data nodes ignore `context`. Nodes using custom Python callables (e.g., `CustomCalculationNode`, `CustomGrowthForecastNode`, `StatisticalGrowthForecastNode`) cannot be deserialized automatically and will raise `NotImplementedError`.
- **Standard Node Registry**: Use `standard_node_registry` to validate, resolve, and list canonical node names and categories.

### Example: Multi-Period Stat Node (with round-trip serialization)
```python
from fin_statement_model.core.nodes import FinancialStatementItemNode, MultiPeriodStatNode
import statistics

data = {'Q1': 10, 'Q2': 12, 'Q3': 11, 'Q4': 13}
sales = FinancialStatementItemNode('sales', data)
avg = MultiPeriodStatNode('avg_sales', input_node=sales, periods=['Q1','Q2','Q3','Q4'], stat_func=statistics.mean)
d = avg.to_dict()
# Round-trip serialization (works for built-in stat functions)
avg2 = MultiPeriodStatNode.from_dict(d, {'sales': sales})
print(avg2.calculate())  # 11.5
# For custom stat functions, manual reconstruction is required.
```

### Example: Using the Standard Node Registry
```python
from fin_statement_model.core.nodes import standard_node_registry

# Validate a node name
is_valid, msg = standard_node_registry.validate_node_name('revenue')
print(is_valid, msg)  # True, 'revenue' is a standard node name

# Resolve alternate name to standard
print(standard_node_registry.get_standard_name('sales'))  # 'revenue'

# List all balance sheet asset nodes
print(standard_node_registry.list_standard_names('balance_sheet_assets'))
```

## Serialization/Deserialization Contract

All node types implement:
- `to_dict(self) -> dict`: Serialize the node to a dictionary.
- `from_dict(cls, data: dict, context: dict[str, Node] | None = None) -> Node`: Classmethod to deserialize a node from a dictionary. For nodes with dependencies, `context` must map node names to node objects. Data nodes ignore `context`.

### Round-trip Example (Data Node)
```python
from fin_statement_model.core.nodes import FinancialStatementItemNode
node = FinancialStatementItemNode('revenue', {'2022': 1000.0, '2023': 1200.0})
d = node.to_dict()
node2 = FinancialStatementItemNode.from_dict(d)
assert node2.calculate('2023') == 1200.0
```

### Round-trip Example (Calculation Node)
```python
from fin_statement_model.core.nodes import FinancialStatementItemNode, CalculationNode
class SumCalculation:
    def calculate(self, inputs, period):
        return sum(node.calculate(period) for node in inputs)
node_a = FinancialStatementItemNode('a', {'2023': 10})
node_b = FinancialStatementItemNode('b', {'2023': 20})
sum_node = CalculationNode('sum_ab', inputs=[node_a, node_b], calculation=SumCalculation())
d = sum_node.to_dict()
sum_node2 = CalculationNode.from_dict(d, {'a': node_a, 'b': node_b})
assert sum_node2.calculate('2023') == 30.0
```

### Round-trip Example (Forecast Node)
```python
from fin_statement_model.core.nodes import FinancialStatementItemNode, FixedGrowthForecastNode
revenue = FinancialStatementItemNode('revenue', {'2022': 100, '2023': 110})
forecast = FixedGrowthForecastNode(revenue, '2023', ['2024', '2025'], 0.05)
d = forecast.to_dict()
forecast2 = FixedGrowthForecastNode.from_dict(d, {'revenue': revenue})
assert round(forecast2.calculate('2025'), 2) == 121.28
```

### Caveats for Custom/Callable Nodes
- Nodes using custom Python callables (e.g., `CustomCalculationNode`, `CustomGrowthForecastNode`, `StatisticalGrowthForecastNode`) **cannot be deserialized automatically** and will raise `NotImplementedError` if `from_dict` is called. Manual reconstruction is required for these node types.

## Best Practices
- Always use standard node names where possible for compatibility.
- Use Google-style docstrings for all new node types and methods.
- Write tests for all new node types (see `tests/core/nodes/`).
- Use `clear_cache()` on calculation/forecast nodes if input data changes.

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

## See Also
- [Standard Node Registry](./standard_nodes_defn/README.md)
- [Node API Reference](../html/fin_statement_model/core/nodes/index.html) 