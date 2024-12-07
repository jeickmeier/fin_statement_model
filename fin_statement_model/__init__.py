"""
finlib - A Python library for financial statement analysis and forecasting.
"""

from .graph import Graph
from .nodes import (Node, FinancialStatementItemNode, CalculationNode,
                    AdditionCalculationNode, SubtractionCalculationNode,
                    MultiplicationCalculationNode, DivisionCalculationNode,
                    MetricCalculationNode)
from .financial_statement import FinancialStatementGraph
from .forecasts import (ForecastNode, FixedGrowthForecastNode, CurveGrowthForecastNode,
                        StatisticalGrowForecastNode, CustomGrowForecastNode)
from .stats import YoYGrowthNode, MultiPeriodStatNode
from .metrics import METRIC_DEFINITIONS
from .builder import add_metric
