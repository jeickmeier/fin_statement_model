# Graph Module

This directory contains the core graph implementation for the Financial Statement Model library.  The Graph API lets you build, mutate, traverse, and evaluate directed graphs of financial statement items and calculations.

## Key Public Classes

| Class | Responsibility |
|-------|---------------|
| `Graph` | End-user façade that wires together all sub-services and exposes a friendly API for building and analysing models. |
| `GraphManipulator` | *Write* helper – add / remove / replace nodes, update values, clear caches. |
| `GraphTraverser` | *Read-only* helper – dependency inspection, cycle detection, topological sorts, etc. |

### Behind the scenes – service layer

The public classes delegate heavy lifting to a **service layer** of small, testable components:

* `CalculationEngine` – memoised value evaluation
* `PeriodService` – unique & sorted period management
* `AdjustmentService` – discretionary adjustments (audit, scenarios…)
* `DataItemService` – CRUD for `FinancialStatementItemNode`
* `MergeService` – graph-to-graph merging
* `GraphIntrospector` – developer-friendly diagnostics
* `NodeRegistryService` – central node-mapping & validation

These services are injected into `Graph` rather than imported directly, keeping the architecture modular and easier to test.

## Features

- Add and update financial statement items with time-series values.
- Define calculation nodes using built-in operations or custom formulas.
- Register and compute metrics from the registry (e.g., `current_ratio`).
- Manage periods automatically (deduplication and sorting).
- Apply and manage discretionary adjustments for scenario analysis.
- Mutate graph structure safely with automatic cache invalidation.
- Traverse and inspect graph structure: dependencies, successors, predecessors.
- Detect cycles and validate graph integrity.
- Perform topological sorts for ordered evaluations.

## Basic Usage

```python
from fin_statement_model.core.graph import Graph

# Initialize a graph with two periods
g = Graph(periods=["2023", "2024"])

# Add data nodes
g.add_financial_statement_item("Revenue", {"2023": 100.0, "2024": 120.0})
```                                 
   
# Add calculation node (formula-based)
```python
g.add_calculation(
    name="GrossProfit",
    input_names=["Revenue", "COGS"],
    operation_type="formula",
    formula="input_0 - input_1",
    formula_variable_names=["input_0", "input_1"]
)

# Perform calculations
print(g.calculate("GrossProfit", "2023"))  # 50.0

# Update COGS value via manipulator and recalculate
g.manipulator.set_value("COGS", "2023", 55.0)
print(g.calculate("GrossProfit", "2023"))  # 45.0

# Inspect dependencies and validate graph
print(g.traverser.get_dependencies("GrossProfit"))  # ['Revenue', 'COGS']
print(g.traverser.validate())  # []
```

## API Reference

- **Graph**: `fin_statement_model.core.graph.graph.Graph`
- **GraphManipulator**: `fin_statement_model.core.graph.manipulator.GraphManipulator`
- **GraphTraverser**: `fin_statement_model.core.graph.traverser.GraphTraverser`

For detailed method descriptions, see the docstrings in each module. 