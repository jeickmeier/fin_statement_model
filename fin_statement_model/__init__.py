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
from fin_statement_model.config import get_config, update_config, reset_config

# ensure our library-wide logging policy is applied immediately
from . import logging_config  # noqa: F401

__version__ = "0.1.0"

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
    "reset_config",
    "update_config",
]

# --------------------------------------------------------------------------
# Optional Extensions (via entry points / importlib.metadata)
# --------------------------------------------------------------------------
# Extensions are optional modules that add functionality without modifying
# the core library. They might depend on heavy libraries (e.g., LLMs,
# ML frameworks) and should be lazy-loaded.
# Example entry point group: 'fin_statement_model.extensions.reporting'
# Expected interface: TBD (e.g., a class with specific methods)
# Note: Avoid hard imports from extensions into core/statements/io.
# Goal: Keep core library lean, allow users to install extras like:
# pip install fin-statement-model[openai]
# pip install fin-statement-model[reporting-tools]
# --------------------------------------------------------------------------


# Core API Exports (ensure essential classes/functions are accessible)
# Example:
# from .core.graph import Graph
# from .core.nodes import Node, FinancialStatementItemNode
# from .core.calculation_engine import CalculationEngine
# from .statements.manager import StatementManager

# Placeholder: Explicitly list key public API components later.
# For now, just rely on sub-package __init__ files if they exist.
