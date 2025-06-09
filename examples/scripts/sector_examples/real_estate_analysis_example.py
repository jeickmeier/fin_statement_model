"""Real Estate Investment Trust (REIT) Analysis Example.

This example demonstrates using specialized real estate metrics and calculations
for analyzing REIT financial performance.
"""

import logging
from pathlib import Path
import yaml

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import FinancialStatementItemNode
from fin_statement_model.statements.orchestration.orchestrator import (
    create_statement_dataframe,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_reit_financial_model() -> Graph:
    """Create a financial model for a REIT with specialized metrics."""
    graph = Graph()

    # === Income Statement Items ===
    income_items = {
        # Revenue
        "rental_income": {"2022": 50000000, "2023": 55000000},
        "property_management_fees": {"2022": 2500000, "2023": 2750000},
        "other_income": {"2022": 1000000, "2023": 1200000},
        # Operating Expenses
        "property_operating_expenses": {"2022": 18000000, "2023": 20000000},
        "property_management_expenses": {"2022": 3500000, "2023": 3850000},
        "general_admin_expenses": {"2022": 4000000, "2023": 4400000},
        "depreciation_expense": {"2022": 12000000, "2023": 13200000},
        # Other
        "interest_expense": {"2022": 8000000, "2023": 8500000},
        "gain_on_property_sales": {"2022": 2000000, "2023": 1500000},
    }

    # === Balance Sheet Items ===
    balance_sheet_items = {
        # Assets
        "investment_properties": {"2022": 600000000, "2023": 650000000},
        "accumulated_depreciation": {"2022": -120000000, "2023": -133200000},
        "cash": {"2022": 15000000, "2023": 18000000},
        "accounts_receivable": {"2022": 3000000, "2023": 3500000},
        # Liabilities
        "mortgages_payable": {"2022": 350000000, "2023": 380000000},
        "bonds_payable": {"2022": 50000000, "2023": 50000000},
        "accounts_payable": {"2022": 2000000, "2023": 2200000},
        # Equity
        "common_shares": {"2022": 100000000, "2023": 100000000},
        "preferred_shares": {"2022": 25000000, "2023": 25000000},
        "retained_earnings": {"2022": 70000000, "2023": 77300000},
        # Share count for per-share metrics
        "shares_outstanding": {"2022": 10000000, "2023": 10000000},
    }

    # === Cash Flow Items ===
    cash_flow_items = {
        "capital_expenditures": {"2022": 45000000, "2023": 50000000},
        "property_acquisitions": {"2022": 30000000, "2023": 35000000},
        "dividends_paid": {"2022": 22000000, "2023": 24000000},
    }

    # Add all items to graph
    for name, values in {
        **income_items,
        **balance_sheet_items,
        **cash_flow_items,
    }.items():
        node = FinancialStatementItemNode(name, values)
        graph.add_node(node)

    # Calculations and metrics will be created later via the statement
    # configuration processed by `create_statement_dataframe`.

    return graph


def analyze_reit_performance(graph: Graph, period: str = "2023") -> None:
    """Analyze REIT performance using specialized metrics."""
    logger.info("=== REIT Analysis Example ===\n")

    # Calculate key REIT metrics
    metrics_to_calculate = [
        ("net_operating_income", "Net Operating Income"),
        ("funds_from_operations", "Funds From Operations (FFO)"),
        ("ffo_per_share", "FFO per Share"),
    ]

    logger.info("Key REIT Metrics for 2023:")
    logger.info("-" * 40)

    for metric_id, display_name in metrics_to_calculate:
        try:
            value = graph.calculate(metric_id, period)

            # Format based on metric type
            if metric_id in ["net_operating_income", "funds_from_operations"]:
                logger.info(f"{display_name}: ${value:,.0f}")
            elif metric_id == "ffo_per_share":
                logger.info(f"{display_name}: ${value:.2f}")
            else:
                logger.info(f"{display_name}: {value:.2f}")

        except Exception:
            logger.exception(f"Could not calculate {display_name}")
            logger.info("")

    # Calculate additional real estate metrics using the helper function
    logger.info("Additional Analysis:")
    logger.info("-" * 40)

    # Cap Rate calculation (NOI / Property Value)
    try:
        noi = graph.calculate("net_operating_income", period)
        property_value = graph.calculate("investment_properties", period)
        cap_rate = (noi / property_value) * 100
        logger.info(f"Capitalization Rate: {cap_rate:.1f}%")

        if cap_rate < 4:
            logger.info("  → Low cap rate - properties may be overvalued")
        elif cap_rate > 8:
            logger.info(
                "  → High cap rate - good income yield but check property quality"
            )
        else:
            logger.info("  → Cap rate within typical range for quality properties")
    except Exception:
        logger.exception("Could not calculate cap rate")

    # Debt Service Coverage
    try:
        interest = graph.calculate("interest_expense", period)
        dscr = noi / abs(interest)  # Use absolute value since interest is negative
        logger.info(f"Debt Service Coverage Ratio: {dscr:.2f}x")

        if dscr < 1.2:
            logger.info("  → Low coverage - may struggle to service debt")
        elif dscr > 2.0:
            logger.info("  → Strong debt coverage")
        else:
            logger.info("  → Adequate debt coverage")
    except Exception:
        logger.exception("Could not calculate DSCR")

    # Growth analysis
    logger.info("\nGrowth Analysis:")
    logger.info("-" * 40)

    try:
        # NOI growth
        noi_2022 = graph.calculate("net_operating_income", "2022")
        noi_2023 = graph.calculate("net_operating_income", "2023")
        noi_growth = ((noi_2023 - noi_2022) / noi_2022) * 100
        logger.info(f"NOI Growth (2022-2023): {noi_growth:.1f}%")

        # FFO growth
        ffo_2022 = graph.calculate("funds_from_operations", "2022")
        ffo_2023 = graph.calculate("funds_from_operations", "2023")
        ffo_growth = ((ffo_2023 - ffo_2022) / ffo_2022) * 100
        logger.info(f"FFO Growth (2022-2023): {ffo_growth:.1f}%")
    except Exception:
        logger.exception("Could not calculate growth metrics")

    logger.info("\n=== Analysis Complete ===")


def main():
    """Run the REIT analysis example."""
    # Build the base graph with raw data nodes
    graph = create_reit_financial_model()

    # Load REIT statement configuration from YAML into memory
    config_path = (
        Path(__file__).resolve().parents[2] / "configs" / "reit_statement.yaml"
    )
    raw_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    raw_configs = {raw_config.get("id", "reit_statement"): raw_config}
    # Generate calculation nodes via statement orchestration
    create_statement_dataframe(graph, raw_configs)

    # Analyze performance using the populated graph
    analyze_reit_performance(graph)


if __name__ == "__main__":
    main()
