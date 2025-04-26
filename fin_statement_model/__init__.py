"""finlib - A Python library for financial statement analysis and forecasting."""

__all__ = [
    "CalculationNode",
    "CurveGrowthForecastNode",
    "CustomGrowthForecastNode",
    "FinancialStatementGraph",
    "FinancialStatementItemNode",
    "FixedGrowthForecastNode",
    "ForecastNode",
    "Graph",
    "LLMClient",
    "LLMConfig",
    "MetricCalculationNode",
    "MultiPeriodStatNode",
    "Node",
    "StatisticalGrowthForecastNode",
    "YoYGrowthNode",
]

from .extensions.llm.llm_client import LLMClient, LLMConfig
from .core.graph import Graph
from .core.nodes import (
    Node,
    FinancialStatementItemNode,
    CalculationNode,
    MetricCalculationNode,
    YoYGrowthNode,
    MultiPeriodStatNode,
    ForecastNode,
    FixedGrowthForecastNode,
    CurveGrowthForecastNode,
    StatisticalGrowthForecastNode,
    CustomGrowthForecastNode,
)

# ensure our library-wide logging policy is applied immediately
from . import logging_config  # noqa: F401

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

__version__ = "0.1.0"  # Central version definition
