# Graph Module

The `fin_statement_model.core.graph` module provides the foundational graph engine for the Financial Statement Model library. It enables the construction, mutation, traversal, and evaluation of directed graphs representing financial statement items, calculations, and metrics.

---

## 🚀 Public API: Quick Start & Core Features

The **public API** is designed for ease of use and covers the most common workflows. All you need is the `Graph` class:

```python
from fin_statement_model.core.graph import Graph
```

### Basic Example

```python
# Initialize a graph with two periods
g = Graph(periods=["2023", "2024"])

# Add data nodes
g.add_financial_statement_item("Revenue", {"2023": 100.0, "2024": 120.0})
g.add_financial_statement_item("COGS", {"2023": 50.0, "2024": 60.0})

# Add a calculation node (formula-based)
g.add_calculation(
    name="GrossProfit",
    input_names=["Revenue", "COGS"],
    operation_type="formula",
    formula="input_0 - input_1",
    formula_variable_names=["input_0", "input_1"]
)

# Calculate a value
print(g.calculate("GrossProfit", "2023"))  # 50.0

# Update a value and recalculate
g.manipulator.set_value("COGS", "2023", 55.0)
print(g.calculate("GrossProfit", "2023"))  # 45.0

# Inspect dependencies and validate graph
print(g.traverser.get_dependencies("GrossProfit"))  # ['Revenue', 'COGS']
print(g.traverser.validate())  # []

# Add a scenario adjustment (what-if analysis)
g.add_adjustment("Revenue", "2023", 10.0, reason="Scenario boost")
print(g.get_adjusted_value("Revenue", "2023"))  # 110.0
```

### Most Common Methods
- `add_financial_statement_item(name, values)` — Add a data node
- `add_calculation(...)` — Add a calculation node (formula or metric)
- `calculate(node_name, period)` — Compute a value
- `add_adjustment(...)` / `get_adjusted_value(...)` — Scenario/what-if analysis
- `traverser.get_dependencies(node_name)` — Inspect dependencies
- `traverser.validate()` — Check for cycles or missing nodes

---

## 🧑‍💻 Advanced Usage & Extension Points

For power users, contributors, or those building custom workflows, the graph module exposes a rich set of advanced features and extension points. These are available via the `Graph` object, but also through direct use of manipulators, traversers, mix-ins, and service classes.

### Advanced Graph Manipulation
- **GraphManipulator** (`g.manipulator`):
  - Low-level add/remove/replace/set operations on nodes
  - Direct cache management
  - Example:
    ```python
    g.manipulator.remove_node("COGS")
    g.manipulator.clear_all_caches()
    ```

### Structural & Dependency Inspection
- **GraphTraverser** (`g.traverser`):
  - Topological sort: `g.traverser.topological_sort()`
  - Cycle detection: `g.traverser.detect_cycles()`
  - Breadth-first search: `g.traverser.breadth_first_search("Revenue")`
  - Dependency graph: `g.traverser.get_dependency_graph()`

### Adjustments & Scenario Analysis
- Add, remove, and list adjustments for scenario modeling:
  - `g.add_adjustment(...)`, `g.remove_adjustment(adj_id)`, `g.list_all_adjustments()`
  - Filter by scenario, tags, or user

### Extending the Graph: Mix-ins & Services
- **Mix-ins** (in `components/`):
  - Compose new graph types or extend with custom logic
  - Example: subclass `Graph` and add your own mix-in for custom validation
- **Services** (in `services/`):
  - Use or replace `CalculationEngine`, `PeriodService`, or `AdjustmentService` for advanced behaviors

### Full Module Structure

| Component / Service      | Responsibility / Features                                                      |
|-------------------------|--------------------------------------------------------------------------------|
| `GraphBaseMixin`        | Core state, constructor, and helpers shared by all mix-ins                      |
| `NodeOpsMixin`          | Node creation, update, replacement, and value-setting                          |
| `CalcOpsMixin`          | Calculation node helpers, metric management, calculation cache                  |
| `AdjustmentMixin`       | Discretionary adjustment API and helpers (scenario/what-if modeling)            |
| `MergeReprMixin`        | Graph merging logic and developer-friendly `__repr__`                           |
| `TraversalMixin`        | Read-only traversal, validation, and dependency inspection                      |
| `CalculationEngine`     | Orchestrates node calculations and manages calculation cache                    |
| `PeriodService`         | Manages unique, sorted periods and period validation                            |
| `AdjustmentService`     | Encapsulates adjustment storage and application logic                           |
| `GraphManipulator`      | Unified interface for all *write* operations (add/remove/replace/set/clear)     |
| `GraphTraverser`        | Read-only utilities for dependency inspection, traversal, validation, cycles     |

---

## 📚 API Reference

- **Graph**: `fin_statement_model.core.graph.graph.Graph`
- **GraphManipulator**: `fin_statement_model.core.graph.manipulator.GraphManipulator`
- **GraphTraverser**: `fin_statement_model.core.graph.traverser.GraphTraverser`
- **Mix-ins**: See `fin_statement_model.core.graph.components`
- **Services**: See `fin_statement_model.core.graph.services`

For detailed method descriptions, see the docstrings in each module and class. The codebase is fully documented with Google-style docstrings and doctest examples for all major features. 