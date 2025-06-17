# fin_statement_model.core

The **core** package is the foundation of the *Financial Statement Model* library. It provides the graph engine, node hierarchy, calculation strategies, metric registry, helpers, and utilities on which all other packages depend. Nothing in `core/` imports from higher-level layers (e.g., `statements`, `io`, `extensions`).

---

## Table of Contents
- [Package Structure](#package-structure)
- [Basic Usage](#basic-usage)
- [Advanced Features](#advanced-features)
- [Error Handling](#error-handling)
- [Extensibility Quick Reference](#extensibility-quick-reference)
- [Design Principles](#design-principles)
- [Further Reading](#further-reading)

---

## Package Structure

| Path / Sub-package      | Responsibility                                                                                       |
|------------------------|-----------------------------------------------------------------------------------------------------|
| `graph/`               | Directed-graph engine; building, traversing, validating, and mutating financial statement graphs. Exposes `Graph`, `GraphManipulator`, and `GraphTraverser`. |
| `nodes/`               | All node implementations. Includes raw data nodes, calculation nodes, statistical nodes, forecast nodes, and helpers such as `is_calculation_node`. |
| `calculations/`        | Strategy objects that perform mathematical operations (addition, subtraction, formula evaluation, etc.) plus a global `Registry` for discovery. |
| `metrics/`             | YAML-driven metric system: definitions, registry, calculation helpers, and interpretation utilities.   |
| `adjustments/`         | API for discretionary adjustments (adds, multipliers, replacements) used in scenario analysis; includes models, manager, analytics, and helpers. |
| `node_factory/`        | Central factory for creating node instances programmatically or from dictionaries/configs.             |
| `errors.py`            | Exception hierarchy rooted at `FinStatementModelError` for consistent error handling.                 |
| `config/` (optional)   | Lightweight accessors for configuration values (e.g., default forecast growth).                       |

---

## Basic Usage

The core API is designed to be intuitive for both quick prototyping and advanced modeling. Here is a minimal example:

```python
from fin_statement_model.core import Graph

# 1 — Initialize an empty graph with two historical periods
graph = Graph(periods=["2023", "2024"])

# 2 — Add raw data nodes
graph.add_financial_statement_item("Revenue", {"2023": 1_000.0, "2024": 1_200.0})
graph.add_financial_statement_item("COGS",    {"2023":   600.0, "2024":   720.0})

# 3 — Create a calculation node (gross profit = revenue − COGS)
gross_profit = graph.add_calculation(
    name="GrossProfit",
    input_names=["Revenue", "COGS"],
    operation_type="subtraction",  # maps to SubtractionCalculation strategy
)
print(graph.calculate("GrossProfit", "2024"))  # 480.0

# 4 — Register a metric node using the built-in metric registry
#    (requires required inputs to be present in the graph)
# metric_node = graph.add_metric("current_ratio")
# print(graph.calculate(metric_node.name, "2024"))

# 5 — Project revenue three years forward at 5% growth
revenue_forecast = graph.add_calculation(
    name="RevenueForecast",
    input_names=["Revenue"],
    operation_type="formula",  # via NodeFactory we can use a formula strategy
    formula="input_0 * 1.05",  # simple inline growth for demo purposes
    formula_variable_names=["input_0"],
)
print(graph.calculate("RevenueForecast", "2024"))  # 1_260.0
```

---

## Advanced Features

### Extensible Node and Metric System
- **Node Types**: Easily define raw data, calculation, forecast, and statistical nodes. Custom node types can be added by subclassing base node classes in `core/nodes/`.
- **Metric Registry**: Register new metrics via YAML (`core/metrics/metric_defn/`) or Python classes. The registry supports both simple and complex metrics, and metrics can be referenced by name in the graph.
- **Calculation Strategies**: Add new calculation strategies by implementing and registering them in `core/calculations/`.

### Forecasting and Scenario Analysis
- **Forecast Nodes**: Implement custom forecasting logic by subclassing `ForecastNode` and overriding `forecast_value`.
- **Adjustments**: Use the `adjustments/` API to apply scenario-based changes (e.g., stress tests, what-if analysis) to any node or calculation.

### Data Ingestion and Interoperability
- **Node Factory**: Dynamically instantiate nodes from configuration files (YAML/JSON) or Python dicts using the `node_factory/` package.
- **No I/O in Core**: All I/O is handled outside of core, ensuring pure, testable logic.

---

## Error Handling

All exceptions inherit from `FinStatementModelError` (see `core/errors.py`), providing a consistent error model for downstream consumers. The main exception types include:
- `FinStatementModelError`: Base exception for all errors in the library.
- `GraphError`: Errors related to graph operations.
- `CalculationError`: Errors during calculation execution.
- `MetricError`: Errors related to metric definitions or registry.
- `NodeError`, `ConfigurationError`, and others for specific error cases.

---

## Extensibility Quick Reference

| Task                              | Preferred Location / API                               |
|-----------------------------------|--------------------------------------------------------|
| Add simple metric                 | `core/metrics/metric_defn/<category>/<metric_name>.yaml`             |
| Add complex metric/calculation    | `core/nodes/<name>_node.py` (if stateful), or strategy in `core/strategies/` |
| Add new calculation strategy      | `core/calculations/`                                   |
| Add data cleaning step            | `preprocessing/cleaning.py` (or similar module)        |
| Define statement structure        | `statements/definitions/<statement_type>.py` (or YAML) |

---

## Design Principles
- **Layered Architecture**: `core` is the only layer with no dependencies on other sub-packages. All other layers depend on `core`.
- **Extensibility**: New node types, metrics, and calculation strategies can be added without modifying core internals.
- **Performance**: Core uses `numpy` and `pandas` for efficient numerical operations.
- **Type Safety**: Full type annotations and strict mypy checking are enforced.
- **Testing**: 80%+ branch coverage is required for all core modules.

---

## Further Reading
- See sub-package READMEs or module docstrings for deeper dives into each component.
- For more advanced usage, including custom metric registration, scenario analysis, and integration with external data sources, see the documentation in the `docs/` directory or the `examples/` folder. 