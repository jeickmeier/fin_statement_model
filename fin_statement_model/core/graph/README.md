# Graph Module

This directory contains the core graph implementation for the Financial Statement Model library.  The Graph API lets you build, mutate, traverse, and evaluate directed graphs of financial statement items and calculations.

## Key Classes

- **Graph**: Central orchestrator for constructing and evaluating graphs of financial data and metrics.
- **GraphManipulator**: Helper for structural mutations (adding/removing/replacing nodes, setting values, clearing caches).
- **GraphTraverser**: Read-only utilities for dependency inspection, traversal, validation, cycle detection, and topological sorting.

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