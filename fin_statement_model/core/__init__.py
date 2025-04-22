"""Core components for the Financial Statement Model.

This package forms the foundation of the library, providing the core infrastructure
for building, calculating, and managing financial models. It includes:

- Graph engine (`core.graph`): For representing financial relationships.
- Base node hierarchy (`core.nodes`): Abstract and concrete node types.
- Calculation engine (`calculation_engine.py`): For evaluating the graph.
- Metric registry and definitions (`core.metrics`): For managing financial metrics.
- Data management (`data_manager.py`): For handling financial data.
- Calculation strategies (`core.strategies`): Reusable calculation logic.
- Core utilities and exceptions (`errors.py`, `node_factory.py`).

This `core` package is designed to be self-contained and does not depend on
other higher-level packages like `statements`, `io`, or `forecasting`.
"""

from .data_manager import DataManager
from .calculation_engine import CalculationEngine
from .node_factory import NodeFactory
from .graph import Graph
from .nodes import (
    Node,
    FinancialStatementItemNode,
    MetricCalculationNode,
    StrategyCalculationNode,
    YoYGrowthNode,
    MultiPeriodStatNode,
    FormulaCalculationNode,
    CustomCalculationNode,
    TwoPeriodAverageNode,
)
from .strategies import (
    AdditionStrategy,
    SubtractionStrategy,
    MultiplicationStrategy,
    DivisionStrategy,
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
    ImportError,
    ExportError,
    TransformationError,
)

__all__ = [
    "AdditionStrategy",
    "CalculationEngine",
    "CalculationError",
    "CircularDependencyError",
    "ConfigurationError",
    "CustomCalculationNode",
    "DataManager",
    "DataValidationError",
    "DivisionStrategy",
    "ExportError",
    "FinancialModelError",
    "FinancialStatementItemNode",
    "FinancialStatementItemNode",
    "FormulaCalculationNode",
    "Graph",
    "GraphError",
    "ImportError",
    "MetricCalculationNode",
    "MultiPeriodStatNode",
    "MultiplicationStrategy",
    "Node",
    "NodeError",
    "NodeFactory",
    "PeriodError",
    "StatementError",
    "StrategyCalculationNode",
    "StrategyError",
    "SubtractionStrategy",
    "TransformationError",
    "TwoPeriodAverageNode",
    "YoYGrowthNode",
]
