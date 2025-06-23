"""Foundation of *fin_statement_model* — graph engine, nodes, calculations, and more.

The **core** package is the foundational layer of the fin_statement_model library. It is intentionally self-contained (nothing here imports from `statements/`, `io/`, or `extensions/`). It provides the primitives that higher-level layers build upon, including the graph engine, node hierarchy, calculation strategies, metric registry, and core utilities.

Main Features:
    - Directed graph data structure for financial modeling (`Graph`, `GraphManipulator`, `GraphTraverser`).
    - Node system for representing raw data, calculations, statistics, and forecasts.
    - Calculation strategies and a global registry for arithmetic and formula logic.
    - YAML-driven metric definitions and interpretation helpers.
    - Models and managers for discretionary adjustments and scenario analysis.
    - Factory utilities for programmatic or YAML-based node creation.
    - Unified exception hierarchy rooted at `FinancialModelError`.

Example:
    >>> from fin_statement_model.core import Graph
    >>> g = Graph(periods=["2023", "2024"])
    >>> _ = g.add_financial_statement_item("Revenue", {"2023": 1000, "2024": 1200})
    >>> _ = g.add_financial_statement_item("COGS", {"2023": 600, "2024": 720})
    >>> g.add_calculation(
    ...     name="GrossProfit",
    ...     input_names=["Revenue", "COGS"],
    ...     operation_type="subtraction",
    ... )
    >>> g.calculate("GrossProfit", "2024")
    480.0

For a deeper dive into each component, advanced features, and extensibility, see `core/README.md`.
"""

from .calculations import (
    AdditionCalculation,
    DivisionCalculation,
    MultiplicationCalculation,
    SubtractionCalculation,
)
from .errors import (
    CalculationError,
    CircularDependencyError,
    ConfigurationError,
    DataValidationError,
    FinancialModelError,
    GraphError,
    NodeError,
    PeriodError,
    StatementError,
    StrategyError,
    TransformationError,
)
from .graph import Graph
from .node_factory import NodeFactory
from .nodes import (
    CalculationNode,
    CustomCalculationNode,
    FinancialStatementItemNode,
    FormulaCalculationNode,
    MultiPeriodStatNode,
    Node,
    TwoPeriodAverageNode,
    YoYGrowthNode,
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
