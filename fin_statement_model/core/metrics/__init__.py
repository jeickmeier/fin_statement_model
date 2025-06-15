"""Provide a comprehensive system for defining, calculating, and interpreting financial metrics.

This module defines:
- MetricDefinition: Pydantic model for metric definitions
- MetricRegistry: Registry for loading and managing metrics
- MetricInterpreter: System for interpreting metric values with ratings
- calculate_metric: Helper to calculate a metric by name
- interpret_metric: Convenience function to interpret a metric value
- Built-in metrics: 75+ professional financial metrics organized by category

The metrics are organized into logical categories:
- Liquidity: Current ratio, quick ratio, working capital analysis
- Leverage: Debt ratios, coverage ratios, capital structure
- Profitability: Margins, returns on assets/equity/capital
- Efficiency: Asset turnover, working capital efficiency
- Valuation: Price multiples, enterprise value ratios
- Cash Flow: Cash generation, cash returns, quality metrics
- Growth: Revenue, earnings, asset growth rates
- Credit Risk: Altman Z-scores, warning flags
- Advanced: DuPont analysis, specialized ratios
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fin_statement_model.core.nodes.base import Node

from .interpretation import MetricInterpreter, MetricRating, interpret_metric
from .models import MetricDefinition, MetricInterpretation
from .registry import MetricRegistry, metric_registry

logger = logging.getLogger(__name__)

# Load metrics from the organized structure by default
try:
    # Load from organized structure
    organized_path = Path(__file__).parent / "metric_defn"
    if organized_path.exists():
        logger.info("Loading metrics from organized structure")
        from .metric_defn import load_organized_metrics

        organized_count = load_organized_metrics()
        logger.info(
            f"Successfully loaded {organized_count} metrics from organized structure"
        )
    else:
        logger.warning("Organized metric structure not found - no metrics loaded")

except Exception:
    logger.exception("Failed to load built-in metrics from organized structure")


def calculate_metric(
    metric_name: str,
    data_nodes: dict[str, "Node"],
    period: str,
    node_name: str | None = None,
) -> float:
    """Calculate a metric value using the metric registry and data nodes.

    This helper function simplifies the common pattern of:
    1. Getting a metric definition from the registry
    2. Creating a FormulaCalculationNode with the appropriate inputs
    3. Calculating the result for a specific period

    Args:
        metric_name: Name of the metric in the registry (e.g., "debt_yield")
        data_nodes: Dictionary mapping node names to Node instances
        period: Time period for calculation (e.g., "2023")
        node_name: Optional name for the calculation node (defaults to metric_name)

    Returns:
        The calculated metric value as a float

    Raises:
        KeyError: If the metric is not found in the registry
        ValueError: If required input nodes are missing from data_nodes
        CalculationError: If the calculation fails

    Examples:
        >>> data_nodes = {
        ...     "net_operating_income": FinancialStatementItemNode("noi", {"2023": 1000000}),
        ...     "total_debt": FinancialStatementItemNode("debt", {"2023": 10000000})
        ... }
        >>> debt_yield = calculate_metric("debt_yield", data_nodes, "2023")
        >>> print(f"Debt Yield: {debt_yield:.1f}%")
        Debt Yield: 10.0%
    """
    # Import here to avoid circular imports
    from fin_statement_model.core.nodes.calculation_nodes import FormulaCalculationNode

    # Get metric definition from registry
    try:
        metric_def = metric_registry.get(metric_name)
    except KeyError:
        available_metrics = metric_registry.list_metrics()
        raise KeyError(  # noqa: B904
            f"Metric '{metric_name}' not found in registry. "
            f"Available metrics: {available_metrics[:10]}..."  # Show first 10
        )

    # Build input mapping for the formula
    inputs = {}
    missing_inputs = []

    for input_name in metric_def.inputs:
        if input_name in data_nodes:
            inputs[input_name] = data_nodes[input_name]
        else:
            missing_inputs.append(input_name)

    if missing_inputs:
        available_nodes = list(data_nodes.keys())
        raise ValueError(
            f"Missing required input nodes for metric '{metric_name}': {missing_inputs}. "
            f"Available nodes: {available_nodes}"
        )

    # Create calculation node
    calc_node_name = node_name or f"{metric_name}_calc"
    calc_node = FormulaCalculationNode(
        calc_node_name,
        inputs=inputs,
        formula=metric_def.formula,
        metric_name=metric_name,
        metric_description=metric_def.description,
    )

    # Calculate and return result
    return calc_node.calculate(period)


__all__ = [
    "MetricDefinition",
    "MetricInterpretation",
    "MetricInterpreter",
    "MetricRating",
    "MetricRegistry",
    "calculate_metric",
    "interpret_metric",
    "metric_registry",
]
