"""Organized Built-in Metrics Package.

This package contains financial metrics organized by analytical category for easier
maintenance and understanding. All metrics are automatically loaded into the
metric_registry when this package is imported.
"""

import logging
from pathlib import Path
from typing import Optional

from fin_statement_model.core.metrics.registry import metric_registry

logger = logging.getLogger(__name__)


def load_organized_metrics(base_path: Optional[Path] = None) -> int:
    """Load all metrics from the organized structure.

    Args:
        base_path: Base path to the builtin_organized directory. If None, uses default.

    Returns:
        Total number of metrics loaded.
    """
    if base_path is None:
        base_path = Path(__file__).parent

    total_loaded = 0

    # Define the organized metric files to load
    metric_files = [
        # Liquidity metrics
        "liquidity/ratios.yaml",
        "liquidity/working_capital.yaml",
        # Leverage metrics
        "leverage/debt_ratios.yaml",
        "leverage/net_leverage.yaml",
        # Coverage metrics
        "coverage/interest_coverage.yaml",
        "coverage/debt_service.yaml",
        # Profitability metrics
        "profitability/margins.yaml",
        "profitability/returns.yaml",
        # Efficiency metrics
        "efficiency/asset_turnover.yaml",
        "efficiency/component_turnover.yaml",
        # Valuation metrics
        "valuation/price_multiples.yaml",
        "valuation/enterprise_multiples.yaml",
        "valuation/yields.yaml",
        # Cash flow metrics
        "cash_flow/generation.yaml",
        "cash_flow/returns.yaml",
        # Growth metrics
        "growth/growth_rates.yaml",
        # Per share metrics
        "per_share/per_share_metrics.yaml",
        # Credit risk metrics
        "credit_risk/altman_scores.yaml",
        "credit_risk/warning_flags.yaml",
        # Advanced metrics
        "advanced/dupont_analysis.yaml",
        # Special calculated items
        "special/gross_profit.yaml",
        "special/net_income.yaml",
        "special/retained_earnings.yaml",
        # Real estate metrics
        "real_estate/operational_metrics.yaml",
        "real_estate/valuation_metrics.yaml",
        "real_estate/per_share_metrics.yaml",
        "real_estate/debt_metrics.yaml",
        # Banking metrics
        "banking/asset_quality.yaml",
        "banking/capital_adequacy.yaml",
        "banking/profitability.yaml",
        "banking/liquidity.yaml",
    ]

    # Collect unique parent directories from the metric files
    unique_directories = set()
    for file_path in metric_files:
        full_path = base_path / file_path
        if full_path.exists():
            unique_directories.add(full_path.parent)
        else:
            logger.warning(f"Organized metric file not found: {full_path}")

    # Load metrics from each unique directory
    for directory in unique_directories:
        try:
            # load_metrics_from_directory returns the count of metrics loaded
            metrics_count = metric_registry.load_metrics_from_directory(directory)
            total_loaded += metrics_count
            logger.debug(f"Loaded {metrics_count} metrics from {directory}")
        except Exception:
            logger.exception(f"Failed to load metrics from directory {directory}")

    logger.info(f"Loaded {total_loaded} total metrics from organized structure")
    return total_loaded


# Auto-load on import
try:
    load_organized_metrics()
except Exception as e:
    logger.warning(f"Failed to auto-load organized metrics: {e}")
