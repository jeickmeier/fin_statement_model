"""Standard Node Definitions Package.

This package contains organized standard node definitions split into logical categories.
All definitions are automatically loaded into the standard_node_registry.
"""

import logging
from pathlib import Path

from fin_statement_model.core.nodes.standard_registry import standard_node_registry

logger = logging.getLogger(__name__)


def load_all_standard_nodes(base_path: Path | None = None) -> int:
    """Load all standard node definitions from organized YAML files.

    Args:
        base_path: Base path to the standard_nodes_defn directory. If None, uses default.

    Returns:
        Total number of nodes loaded.
    """
    if base_path is None:
        base_path = Path(__file__).parent

    total_loaded = 0

    # Define the organized node files to load
    node_files = [
        # Balance sheet nodes
        "balance_sheet/assets.yaml",
        "balance_sheet/liabilities.yaml",
        "balance_sheet/equity.yaml",
        # Income statement nodes
        "income_statement/revenue_costs.yaml",
        "income_statement/operating.yaml",
        "income_statement/non_operating.yaml",
        "income_statement/shares.yaml",
        # Cash flow nodes
        "cash_flow/operating.yaml",
        "cash_flow/investing.yaml",
        "cash_flow/financing.yaml",
        # Calculated items
        "calculated/profitability.yaml",
        "calculated/liquidity.yaml",
        "calculated/leverage.yaml",
        "calculated/valuation.yaml",
        # Market data
        "market_data/market_data.yaml",
        # Real estate nodes
        "real_estate/property_operations.yaml",
        "real_estate/reit_specific.yaml",
        "real_estate/debt_financing.yaml",
        # Banking nodes
        "banking/assets.yaml",
        "banking/liabilities.yaml",
        "banking/income_statement.yaml",
        "banking/regulatory_capital.yaml",
        "banking/off_balance_sheet.yaml",
    ]

    for file_path in node_files:
        full_path = base_path / file_path
        if full_path.exists():
            try:
                count = standard_node_registry.load_from_yaml_file(full_path)
                total_loaded += count
                logger.debug("Loaded %s nodes from %s", count, file_path)
            except (OSError, ValueError):
                logger.exception("Failed to load %s", file_path)
        else:
            logger.warning("Organized node file not found: %s", full_path)

    logger.info("Loaded %s total standard nodes from organized structure", total_loaded)
    return total_loaded


# Auto-load on import
try:
    load_all_standard_nodes()
except (OSError, ValueError) as exc:
    logger.warning("Failed to auto-load standard nodes: %s", exc)
