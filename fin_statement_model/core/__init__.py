"""
Core components for the Financial Statement Model.

This package contains the core components for managing financial data and calculations.
"""

from .data_manager import DataManager
from .calculation_engine import CalculationEngine
from .node_factory import NodeFactory
from .graph import Graph
from .nodes import (
    Node,
    FinancialStatementItemNode,
    CalculationNode,
    AdditionCalculationNode,
    SubtractionCalculationNode,
    MultiplicationCalculationNode,
    DivisionCalculationNode,
    MetricCalculationNode,
    StrategyCalculationNode,
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
from .engine import CalculationEngine as CoreCalculationEngine
from .metrics import METRIC_DEFINITIONS
from .stats import YoYGrowthNode, MultiPeriodStatNode

# Import this last to avoid circular imports
from .financial_statement import FinancialStatementGraph

__all__ = [
    "DataManager",
    "CalculationEngine",
    "NodeFactory",
    "Graph",
    "Node",
    "FinancialStatementItemNode",
    "CalculationNode",
    "AdditionCalculationNode",
    "SubtractionCalculationNode",
    "MultiplicationCalculationNode",
    "DivisionCalculationNode",
    "MetricCalculationNode",
    "StrategyCalculationNode",
    "FinancialModelError",
    "ConfigurationError",
    "CalculationError",
    "NodeError",
    "GraphError",
    "DataValidationError",
    "CircularDependencyError",
    "PeriodError",
    "StatementError",
    "StrategyError",
    "ImportError",
    "ExportError",
    "TransformationError",
    "CoreCalculationEngine",
    "METRIC_DEFINITIONS",
    "YoYGrowthNode",
    "MultiPeriodStatNode",
    "FinancialStatementGraph",
]
