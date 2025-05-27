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
from pathlib import Path

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

# Load standard nodes - prefer organized structure, fallback to flat file
_nodes_loaded = False

if not _nodes_loaded:
    try:
        # First try to load from organized structure
        organized_path = Path(__file__).parent / "standard_nodes"
        if organized_path.exists() and (organized_path / "__init__.py").exists():
            logger.info("Loading standard nodes from organized structure")
            from .standard_nodes import load_all_standard_nodes

            organized_count = load_all_standard_nodes()
            logger.info(
                f"Successfully loaded {organized_count} standard nodes from organized structure"
            )
            _nodes_loaded = True
        else:
            # Fallback to flat structure if organized doesn't exist
            logger.info("Organized structure not found, loading from flat standard_nodes.yaml")
            flat_file = Path(__file__).parent / "standard_nodes.yaml"
            if flat_file.exists():
                flat_count = standard_node_registry.load_from_yaml(flat_file)
                logger.info(f"Successfully loaded {flat_count} standard nodes from flat file")
                _nodes_loaded = True
            else:
                logger.warning("No standard node files found in either organized or flat structure")

    except Exception:
        logger.exception("Failed to load standard nodes")
        # Try fallback to flat structure only if organized loading failed
        if not _nodes_loaded:
            try:
                flat_file = Path(__file__).parent / "standard_nodes.yaml"
                if flat_file.exists():
                    flat_count = standard_node_registry.load_from_yaml(flat_file)
                    logger.info(f"Fallback: loaded {flat_count} standard nodes from flat file")
                    _nodes_loaded = True
            except Exception:
                logger.exception("Fallback loading also failed")

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
]
