"""Financial Statement Model library.

A comprehensive library for building and analyzing financial statement models
using a node-based graph structure.
"""

# Import key components at package level for easier access
# Import configuration management
from fin_statement_model.config import get_config, update_config
from fin_statement_model.core.errors import FinancialModelError
from fin_statement_model.core.graph import Graph
from fin_statement_model.core.node_factory import NodeFactory
from fin_statement_model.core.nodes import (
    CalculationNode,
    CurveGrowthForecastNode,
    CustomGrowthForecastNode,
    FinancialStatementItemNode,
    FixedGrowthForecastNode,
    ForecastNode,
    MultiPeriodStatNode,
    Node,
    StatisticalGrowthForecastNode,
    YoYGrowthNode,
)
from fin_statement_model.templates.registry import TemplateRegistry

# ensure our library-wide logging policy is applied immediately
from . import logging_config

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
    "TemplateRegistry",
    "YoYGrowthNode",
    "__version__",
    "get_config",
    "logging_config",
    "update_config",
]

# Placeholder: explicit additional API re-exports can be added here later.
