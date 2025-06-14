# Fin Statement Model

A pre-alpha library for building and analyzing financial statement models using a node-based graph structure.

## Configuration

Use the centralized configuration system to manage library settings at runtime:

```python
from fin_statement_model.config import update_config, cfg

# Override display settings
update_config({
    "display": {"default_units": "EUR Thousands", "scale_factor": 0.001}
})

# Access a specific value
print(cfg("display.default_units"))  # → 'EUR Thousands'
```

For more detailed configuration options and loading order, see the `fin_statement_model.config` subpackage.

## Quick-start

```python
from fin_statement_model.core.graph import Graph

# 1) Create a graph and add basic items
g = Graph(periods=["2023", "2024"])
g.add_financial_statement_item("Revenue", {"2023": 100.0, "2024": 120.0})
g.add_financial_statement_item("COGS", {"2023": 60.0, "2024": 70.0})

# 2) Build a calculation node using a built-in strategy (here: formula)
g.add_calculation(
    name="GrossProfit",
    input_names=["Revenue", "COGS"],
    operation_type="formula",  # could be "addition", "subtraction", etc.
    formula="input_0 - input_1",
    formula_variable_names=["input_0", "input_1"],
)

print(g.calculate("GrossProfit", "2023"))  # → 40.0

# 3) Apply discretionary adjustments
adj_id = g.add_adjustment(
    node_name="GrossProfit",
    period="2023",
    value=50.0,
    reason="Manager override",
    adj_type="REPLACEMENT",  # see AdjustmentType enum
)

print(g.get_adjusted_value("GrossProfit", "2023"))  # → 50.0

# 4) Merge another graph
other = Graph(periods=["2025"])
other.add_financial_statement_item("Revenue", {"2025": 150.0})
g.merge_from(other)
print(g.periods)  # ["2023", "2024", "2025"]
```

## Extensibility via Service Injection

The public `Graph` class is a thin façade over independent services:

* **CalculationEngine** – executes node calculations and manages the cache.
* **PeriodService** – deduplicates, sorts, and stores periods.
* **AdjustmentService** – stores and applies discretionary adjustments.
* **DataItemService** – CRUD helpers for financial-statement items.
* **MergeService** – graph-to-graph merge logic.
* **NodeRegistryService** – validates and registers nodes.
* **GraphIntrospector** – developer-friendly diagnostics (repr, cycle helper).

Each service can be swapped for a custom implementation:

```python
from fin_statement_model.core.graph import Graph

class DummyEngine:  # must respect CalculationEngine interface
    def __init__(**kwargs):
        ...

g = Graph(calc_engine_cls=DummyEngine)  # tests can inject mocks
```

Because the library is pre-alpha **no deprecation process is required** – breaking changes can be made freely between versions.

---
For full API docs see the HTML documentation in `html/` or browse the source – every public class and function has Google-style docstrings.
