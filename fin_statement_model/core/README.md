# fin_statement_model.core

The **core** package is the foundation of the *Financial Statement Model* library.
It offers the graph engine, node hierarchy, calculation strategies, metric
registry, helpers, and utilities on which all other packages depend.  Nothing in
`core/` imports from higher-level layers (e.g. `statements`, `io`, `extensions`).

---

## Package structure

| Path / Sub-package | Responsibility |
|--------------------|----------------|
| `graph/` | Directed-graph engine; building, traversing, validating, and mutating financial statement graphs. Exposes `Graph`, `GraphManipulator`, and `GraphTraverser`. |
| `nodes/` | All node implementations.  Includes raw data nodes, calculation nodes, statistical nodes, forecast nodes, and helpers such as `is_calculation_node`. |
| `metrics/` | YAML-driven metric system: definitions, registry, calculation helpers, and interpretation utilities. |
| `adjustments/` | API for discretionary adjustments (adds, multipliers, replacements) used in scenario analysis; includes models, manager, analytics, and helpers. |
| `node_factory.py` | Central factory for creating node instances programmatically or from dictionaries. |
| `errors.py` | Exception hierarchy rooted at `FinancialModelError` for consistent error handling. |
| `config/` (optional helpers) | Lightweight accessors for configuration values (e.g., default forecast growth). |

---

## Quick-start example

```python
from fin_statement_model.core import Graph

# 1 — initialise an empty graph with two historical periods
graph = Graph(periods=["2023", "2024"])

# 2 — add raw data nodes
graph.add_financial_statement_item("Revenue", {"2023": 1_000.0, "2024": 1_200.0})
graph.add_financial_statement_item("COGS",    {"2023":   600.0, "2024":   720.0})

# 3 — create a calculation node (gross profit = revenue − COGS)
gross_profit = graph.add_calculation(
    name="GrossProfit",
    input_names=["Revenue", "COGS"],
    operation_type="subtraction",  # maps to SubtractionCalculation strategy
)
print(graph.calculate("GrossProfit", "2024"))  # 480.0

# 4 — register a metric node using the built-in metric registry
#    (requires required inputs to be present in the graph)
metric_node = graph.add_metric("current_ratio")
print(graph.calculate(metric_node.name, "2024"))

# 5 — project revenue three years forward at 5 % growth
forecast = graph.add_calculation(
    name="RevenueForecast",
    input_names=["Revenue"],
    operation_type="formula",  # via NodeFactory we can use a formula strategy
    formula="input_0 * 1.05",  # simple inline growth for demo purposes
    formula_variable_names=["input_0"],
)
print(graph.calculate("RevenueForecast", "2024"))  # 1 260.0
```

This short script shows how the *core* APIs mesh together:

1.   **Graph** orchestrates everything and caches results.
2.   **FinancialStatementItemNode** instances store the raw data.
3.   **CalculationNode** (created via `add_calculation`) is usually a
     `FormulaCalculationNode` generated on-the-fly – no external registry is
     required anymore.
4.   **Metric nodes** build on the same mechanism but pull formulas from the
     YAML-based metric registry.
5.   The graph can be extended further with forecasts, statistical nodes, and
     discretionary adjustments for scenario analysis.

> 🔎  See individual sub-package READMEs or docstrings for deeper dives into each
> component. 