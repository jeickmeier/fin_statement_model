# Graph Module (v2)

> **Status:** Stable v2 implementation; legacy v1 removed.

This module implements the modular, test-friendly graph engine with a functional-core / imperative-shell design.

Key public entry points:
- `GraphFacade` (importable as `Graph`)
- `GraphManipulator`
- `GraphTraverser`

```text
fin_statement_model/core/graph/
├── api/        # Public façade & tracing
├── domain/     # Pure dataclasses (Node, Period, Adjustment)
├── engine/     # Immutable GraphState, pure GraphBuilder, CalculationEngine
├── services/   # Side-effecting helpers injected via ServiceContainer
└── impl/       # Thin imperative shell wiring everything together
```

## Guiding principles

| Principle                             | Expression in code                                                   |
|---------------------------------------|----------------------------------------------------------------------|
| Functional core, imperative shell     | `CalculationEngine` & `GraphState` are pure; IO lives in services    |
| Immutability at rest                  | `Node`, `Period`, `GraphState` are **frozen** dataclasses            |
| Explicit dependency injection         | `ServiceContainer` supplies collaborators                            |
| Small, cohesive modules               | ≤ 400 LOC per module, ≤ 2 public symbols                             |
| Observable & debuggable               | `CalcTrace` exposes timings & dependencies when `trace=True`         |

### Migration path

1. **Bootstrap** – directory scaffolding (**done ✅**)
2. **Domain layer** – immutable dataclasses *(WIP)*
3. **Engine** – builder, state, topo sort, calculator *(todo)*
4. **Services** – adjustments & periods *(todo)*
5. **Shell** – new `impl.graph.Graph` *(todo)*
6. **Facade** – thin public API *(todo)*
7. **Remove v1** – when tests & docs are ported *(future)*

---

*Last updated:* <!--DATE--> by automated scaffolding script.

## Key Public Classes

## Features

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