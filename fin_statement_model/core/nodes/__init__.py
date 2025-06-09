"""Core Node Implementations for the Financial Statement Model.

This package exports the base `Node` class and various concrete node types
used to build the financial model graph. These include:

- Data Nodes:
    - `FinancialStatementItemNode`: Stores raw numerical data for specific periods.

- Calculation Nodes:
    - `FormulaCalculationNode`: Calculates based on mathematical string formulas.
    - `CalculationNode`: Uses a calculation object for calculation logic.
    - `CustomCalculationNode`: Uses arbitrary Python functions for calculation.

- Statistical Nodes:
    - `YoYGrowthNode`: Calculates year-over-year percentage growth.
    - `MultiPeriodStatNode`: Computes statistics (mean, stddev) over multiple periods.
    - `TwoPeriodAverageNode`: Calculates the average over two specific periods.

- Forecast Nodes:
    - `ForecastNode`: Base class for forecasting nodes.
    - Various forecast implementations for different forecasting strategies.

Standard Node Registry:
The package also provides a registry of standardized node names for financial
statement items, ensuring consistency across models and enabling metrics to work properly.
Standard nodes are organized by category:
- Balance Sheet: Assets, liabilities, equity
- Income Statement: Revenue, expenses, profit measures
- Cash Flow: Operating, investing, financing activities
- Calculated Items: EBITDA, working capital, leverage measures
- Market Data: Stock price, market cap, per-share metrics
"""

import logging

# Import all node classes using actual file names
from .base import Node
from .item_node import FinancialStatementItemNode
from .calculation_nodes import (
    CalculationNode,
    FormulaCalculationNode,
    CustomCalculationNode,
)
from .stats_nodes import (
    YoYGrowthNode,
    MultiPeriodStatNode,
    TwoPeriodAverageNode,
)
from .forecast_nodes import (
    ForecastNode,
    FixedGrowthForecastNode,
    CurveGrowthForecastNode,
    StatisticalGrowthForecastNode,
    CustomGrowthForecastNode,
    AverageValueForecastNode,
    AverageHistoricalGrowthForecastNode,
)

# Import standard registry
from .standard_registry import standard_node_registry

logger = logging.getLogger(__name__)

# Initialize standard nodes from the organized definition directory
try:
    count = standard_node_registry.initialize_default_nodes()
    if count == 0:
        logger.warning(
            "No standard nodes were loaded. The registry is empty. "
            "This may cause issues with metrics and node validation."
        )
except Exception:
    logger.exception("Failed to initialize standard nodes")


def is_calculation_node(node: Node) -> bool:
    """Return True for nodes that represent computed/calculated values.

    Helper centralises the logic that previously lived in ``Node.has_calculation``
    implementations.  A node is considered a *calculation node* if it is an
    instance of one of the dedicated calculation-type classes (CalculationNode,
    ForecastNode, CustomCalculationNode) or of statistical helpers that derive
    directly from :class:`Node` but still compute a value (e.g.
    ``YoYGrowthNode``).

    Args:
        node: Any concrete :class:`~fin_statement_model.core.nodes.base.Node` instance.

    Returns:
        bool: ``True`` when *node* performs a calculation; otherwise ``False``.
    """
    return isinstance(
        node,
        (
            CalculationNode,
            ForecastNode,
            CustomCalculationNode,
            YoYGrowthNode,
            MultiPeriodStatNode,
            TwoPeriodAverageNode,
        ),
    )


__all__ = [
    "AverageHistoricalGrowthForecastNode",
    "AverageValueForecastNode",
    "CalculationNode",
    "CurveGrowthForecastNode",
    "CustomCalculationNode",
    "CustomGrowthForecastNode",
    "FinancialStatementItemNode",
    "FixedGrowthForecastNode",
    "ForecastNode",
    "FormulaCalculationNode",
    "MultiPeriodStatNode",
    "Node",
    "StatisticalGrowthForecastNode",
    "TwoPeriodAverageNode",
    "YoYGrowthNode",
    "standard_node_registry",
    "is_calculation_node",
]
