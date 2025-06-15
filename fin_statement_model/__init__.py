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

# ---------------------------------------------------------------------------
# One-shot logging setup (single entry point for the whole library)
# ---------------------------------------------------------------------------

from fin_statement_model.core.logging import get_logger as _get_logger
from fin_statement_model.core.logging import setup_logging as _setup_logging

try:
    _cfg = get_config()
    _setup_logging(
        level=_cfg.logging.level,
        format_string=_cfg.logging.format,
        detailed=_cfg.logging.detailed,
        log_file_path=(
            str(_cfg.logging.log_file_path) if _cfg.logging.log_file_path else None
        ),
    )
except Exception as _err:  # noqa: BLE001
    import logging as _std_logging

    _std_logging.getLogger(__name__).debug(
        "Logging initialisation failed: %s", _err, exc_info=False
    )

# Expose a top-level package logger for convenience
logger = _get_logger(__name__)

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
