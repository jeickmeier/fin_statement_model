"""Financial Statement Model library.

A comprehensive library for building and analyzing financial statement models
using a node-based graph structure.
"""

# Import key components at package level for easier access
from fin_statement_model.core.errors import FinancialModelError
from fin_statement_model.core.graph import Graph
from fin_statement_model.core.node_factory import NodeFactory
from fin_statement_model.core.nodes import (
    CalculationNode,
    CustomGrowthForecastNode,
    CurveGrowthForecastNode,
    FinancialStatementItemNode,
    FixedGrowthForecastNode,
    ForecastNode,
    MultiPeriodStatNode,
    Node,
    StatisticalGrowthForecastNode,
    YoYGrowthNode,
)

# Import configuration management
from fin_statement_model.config import get_config, update_config

# ensure our library-wide logging policy is applied immediately
from . import logging_config  # noqa: F401

__version__ = "0.2.0"

__all__ = [
    "CalculationNode",
    "CurveGrowthForecastNode",
    "CustomGrowthForecastNode",
    "FinancialModelError",
    "FinancialStatementItemNode",
    "FixedGrowthForecastNode",
    "ForecastNode",
    "Graph",
    "MultiPeriodStatNode",
    "Node",
    "NodeFactory",
    "StatisticalGrowthForecastNode",
    "YoYGrowthNode",
    "__version__",
    "get_config",
    "update_config",
]

# Core API Exports (ensure essential classes/functions are accessible)
# Example:
# from .core.graph import Graph
# from .core.nodes import Node, FinancialStatementItemNode
# from .core.calculation_engine import CalculationEngine
# from .statements.manager import StatementManager

# Placeholder: Explicitly list key public API components later.
# For now, just rely on sub-package __init__ files if they exist.
