"""Core Node Implementations for the Financial Statement Model.

This package exports the base `Node` class and various concrete node types
used to build the financial model graph. These include:

- Data Nodes:
    - `FinancialStatementItemNode`: Stores raw numerical data for specific periods.

- Calculation Nodes:
    - `FormulaCalculationNode`: Calculates based on mathematical string formulas.
    - `CalculationNode`: Uses a calculation object for calculation logic.
    - `MetricCalculationNode`: Calculates based on registered metric definitions.
    - `CustomCalculationNode`: Uses arbitrary Python functions for calculation.

- Statistical Nodes:
    - `YoYGrowthNode`: Calculates year-over-year percentage growth.
    - `MultiPeriodStatNode`: Computes statistics (mean, stddev) over multiple periods.
    - `TwoPeriodAverageNode`: Calculates the average over two specific periods.

The `__all__` list defines the public API of this package.
"""

# Core node package public interface: re-export submodules
from .base import Node
from .item_node import FinancialStatementItemNode

# Imports from consolidated files
from .calculation_nodes import (
    FormulaCalculationNode,
    CalculationNode,
    MetricCalculationNode,
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
    "MetricCalculationNode",
    "MultiPeriodStatNode",
    "Node",
    "StatisticalGrowthForecastNode",
    "TwoPeriodAverageNode",
    "YoYGrowthNode",
]
