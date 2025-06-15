"""Provide core node implementations for the financial statement model.

This package exports the `Node` base class and specialized node types for building
and evaluating financial statement graphs:

Data Nodes:
    - FinancialStatementItemNode: Store raw financial data for specific periods.

Calculation Nodes:
    - CalculationNode: Delegate value computation to a calculation object.
    - FormulaCalculationNode: Evaluate expression-based formulas.
    - CustomCalculationNode: Compute values using custom Python functions.

Statistical Nodes:
    - YoYGrowthNode: Compute year-over-year percentage growth.
    - MultiPeriodStatNode: Compute statistical measures (mean, stdev) over multiple periods.
    - TwoPeriodAverageNode: Compute the average between two periods.

Forecast Nodes:
    - ForecastNode: Base class for forecasting future values.
    - FixedGrowthForecastNode: Apply a constant growth rate.
    - CurveGrowthForecastNode: Apply period-specific growth rates.
    - StatisticalGrowthForecastNode: Draw growth from a distribution.
    - CustomGrowthForecastNode: Compute growth via a custom function.
    - AverageValueForecastNode: Project the historical average forward.
    - AverageHistoricalGrowthForecastNode: Apply average historical growth rate.

Also provides `standard_node_registry` and `is_calculation_node` helper.
"""

import logging

# Import all node classes using actual file names
from .base import Node
from .calculation_nodes import (
    CalculationNode,
    CustomCalculationNode,
    FormulaCalculationNode,
)
from .forecast_nodes import (
    AverageHistoricalGrowthForecastNode,
    AverageValueForecastNode,
    CurveGrowthForecastNode,
    CustomGrowthForecastNode,
    FixedGrowthForecastNode,
    ForecastNode,
    StatisticalGrowthForecastNode,
)
from .item_node import FinancialStatementItemNode

# Import standard registry
from .standard_registry import standard_node_registry
from .stats_nodes import (
    MultiPeriodStatNode,
    TwoPeriodAverageNode,
    YoYGrowthNode,
)

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
    """Determine if a node performs a calculated value.

    A node is considered a calculation node if it computes values rather than
    storing raw data. Calculation node types include:
    - CalculationNode
    - FormulaCalculationNode
    - CustomCalculationNode
    - ForecastNode and its subclasses
    - YoYGrowthNode
    - MultiPeriodStatNode
    - TwoPeriodAverageNode

    Args:
        node (Node): Node instance to check.

    Returns:
        bool: True if `node` performs a calculation; False otherwise.

    Examples:
        >>> from fin_statement_model.core.nodes import is_calculation_node, FinancialStatementItemNode, CalculationNode
        >>> data_node = FinancialStatementItemNode('rev', {'2023': 100})
        >>> is_calculation_node(data_node)
        False
        >>> calc_node = CalculationNode('sum', inputs=[data_node], calculation=...)
        >>> is_calculation_node(calc_node)
        True
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
