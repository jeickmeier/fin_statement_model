"""Foundation of *fin_statement_model* — graph engine, nodes, calculations & more.

The **core** package is intentionally self-contained (nothing here imports from
`statements/`, `io/`, or `extensions/`).  It provides the primitives that
higher-level layers build upon.

Sub-packages / key modules:

* `graph/` – directed-graph data structure (`Graph`, `GraphManipulator`, `GraphTraverser`).
* `nodes/` – raw data, calculation, statistical and forecast nodes plus helpers.
* `calculations/` – strategy objects implementing arithmetic and formula logic, with a global `Registry`.
* `metrics/` – YAML-driven metric definitions, registry and interpretation helpers.
* `adjustments/` – models and manager for discretionary adjustments & scenario analysis.
* `node_factory.py` – convenience factory for programmatic or YAML-based node creation.
* `errors.py` – unified exception hierarchy rooted at `FinancialModelError`.

Example:

```python
from fin_statement_model.core import Graph

# Build a simple two-period graph
g = Graph(periods=["2023", "2024"])
_ = g.add_financial_statement_item("Revenue", {"2023": 1_000, "2024": 1_200})
_ = g.add_financial_statement_item("COGS",    {"2023":   600, "2024":   720})

# Add a calculation node: gross profit = revenue − COGS
g.add_calculation(
    name="GrossProfit",
    input_names=["Revenue", "COGS"],
    operation_type="subtraction",
)

# Fetch a built-in metric (requires additional inputs to be present)
# g.add_metric("current_ratio")

print(g.calculate("GrossProfit", "2024"))  # -> 480.0
```

Refer to `core/README.md` for a deeper dive into each component.
"""

from .node_factory import NodeFactory
from .graph import Graph
from .nodes import (
    Node,
    FinancialStatementItemNode,
    CalculationNode,
    YoYGrowthNode,
    MultiPeriodStatNode,
    FormulaCalculationNode,
    CustomCalculationNode,
    TwoPeriodAverageNode,
)
from .calculations import (
    AdditionCalculation,
    SubtractionCalculation,
    MultiplicationCalculation,
    DivisionCalculation,
)
from .errors import (
    FinancialModelError,
    ConfigurationError,
    CalculationError,
    NodeError,
    GraphError,
    DataValidationError,
    CircularDependencyError,
    PeriodError,
    StatementError,
    StrategyError,
    TransformationError,
)

__all__ = [
    "AdditionCalculation",
    "CalculationError",
    "CalculationNode",
    "CircularDependencyError",
    "ConfigurationError",
    "CustomCalculationNode",
    "DataValidationError",
    "DivisionCalculation",
    "FinancialModelError",
    "FinancialStatementItemNode",
    "FormulaCalculationNode",
    "Graph",
    "GraphError",
    "MultiPeriodStatNode",
    "MultiplicationCalculation",
    "Node",
    "NodeError",
    "NodeFactory",
    "PeriodError",
    "StatementError",
    "StrategyError",
    "SubtractionCalculation",
    "TransformationError",
    "TwoPeriodAverageNode",
    "YoYGrowthNode",
]
