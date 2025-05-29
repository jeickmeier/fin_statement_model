"""Simplified Financial Statement Model Example.

This example demonstrates the most straightforward way to use the library
for basic financial analysis tasks without complex configurations.
"""

import logging
import sys
from pathlib import Path

from fin_statement_model.io import read_data
from fin_statement_model.statements import create_statement_dataframe
from fin_statement_model.core.metrics.registry import metric_registry
from fin_statement_model.core.metrics.models import MetricDefinition

# Configure logging for visibility
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Example configuration path (you would replace with your actual path)
INCOME_STATEMENT_CONFIG = Path(__file__).parent / "configs" / "sample_income_statement.yaml"

# If config doesn't exist, use the full example instead
if not INCOME_STATEMENT_CONFIG.exists():
    from examples.scripts.med_example import main as run_full_example

    run_full_example()
    sys.exit()

logger.info("=" * 60)
logger.info("SIMPLE FINANCIAL STATEMENT MODEL EXAMPLE")
logger.info("=" * 60)

# Sample data - in practice, you'd load from Excel/CSV/API
sample_data = {
    # Income Statement items with realistic values
    "revenue": {"2022": 1000000, "2023": 1200000},
    "cost_of_revenue": {"2022": 600000, "2023": 700000},
    "operating_expenses": {"2022": 250000, "2023": 300000},
    "interest_expense": {"2022": 20000, "2023": 25000},
    "tax_expense": {"2022": 32500, "2023": 43750},
    # Balance Sheet items for ratio calculations
    "total_assets": {"2022": 2000000, "2023": 2500000},
    "current_assets": {"2022": 500000, "2023": 600000},
    "current_liabilities": {"2022": 300000, "2023": 350000},
    "total_liabilities": {"2022": 800000, "2023": 1000000},
    "shareholders_equity": {"2022": 1200000, "2023": 1500000},
    "inventory": {"2022": 150000, "2023": 180000},
    "accounts_receivable": {"2022": 120000, "2023": 150000},
    "accounts_payable": {"2022": 80000, "2023": 95000},
    # Additional items for comprehensive analysis
    "depreciation": {"2022": 50000, "2023": 60000},
    "capex": {"2022": 100000, "2023": 120000},
    "dividends": {"2022": 50000, "2023": 60000},
}

# Step 1: Load the data into a graph
logger.info("\nStep 1: Loading financial data...")
graph = read_data(format_type="dict", source=sample_data)

logger.info(f"✓ Loaded data for periods: {graph.periods}")
logger.info(f"✓ Created {len(graph.nodes)} data nodes")

# Step 2: Create statement DataFrame
# Note: This requires a proper config file. For demo purposes,
# we'll show the structure even if the config is missing
try:
    logger.info("\nStep 2: Building statement structure...")
    income_df = create_statement_dataframe(
        graph=graph,
        config_path_or_dir=str(INCOME_STATEMENT_CONFIG),
        format_kwargs={
            "number_format": ",.0f",
            "should_apply_signs": True,
        },
    )

    logger.info("✓ Statement structure built successfully")
    logger.info("\nIncome Statement:")
    logger.info(income_df.to_string(index=False))
except Exception:
    logger.warning("Could not load statement config")
    logger.warning("⚠ Using simplified analysis instead")

# Step 3: Calculate key financial metrics
logger.info("\nStep 3: Calculating financial metrics...")

# Define which metrics to calculate
key_metrics = [
    "gross_margin",
    "operating_margin",
    "net_margin",
    "roe",
    "current_ratio",
    "debt_to_equity",
]

# Calculate and display metrics
logger.info("\nKey Financial Metrics (2023):")
logger.info("-" * 40)

for metric_name in key_metrics:
    try:
        # Get metric definition
        metric_def: MetricDefinition = metric_registry.get_metric(metric_name)

        # Calculate value
        value = graph.calculate(metric_name, "2023")

        # Format based on metric type
        if "margin" in metric_name or metric_name == "roe":
            value_str = f"{value * 100:.1f}%"
        else:
            value_str = f"{value:.2f}"

        # Simple rating system
        if metric_name == "current_ratio":
            rating = "Good" if value > 1.5 else "Needs attention"
        elif metric_name == "debt_to_equity":
            rating = "Conservative" if value < 1.0 else "Leveraged"
        else:
            rating = "Healthy" if value > 0.1 else "Review needed"

        status = "✓" if rating in ["Good", "Conservative", "Healthy"] else "⚠"
        logger.info(f"{status} {metric_def.name}: {value_str} ({rating})")

    except Exception:
        logger.exception(f"❌ {metric_name}: Could not calculate")

# Step 4: Simple trend analysis
logger.info("\nStep 4: Trend Analysis (Revenue Growth):")
logger.info("-" * 40)

try:
    # Calculate year-over-year growth
    periods = sorted(graph.periods)
    for i in range(1, len(periods)):
        prev_year = periods[i - 1]
        curr_year = periods[i]

        prev_revenue = graph.get_node("revenue").get_value(prev_year)
        curr_revenue = graph.get_node("revenue").get_value(curr_year)

        growth = ((curr_revenue - prev_revenue) / prev_revenue) * 100
        logger.info(f"{prev_year} → {curr_year}: {growth:.1f}% growth")
except Exception:
    logger.exception("Could not perform trend analysis")

logger.info("\n" + "=" * 60)
logger.info("EXAMPLE COMPLETE")
logger.info("=" * 60)
logger.info("\nKey Takeaways:")
logger.info("• Use read_data() to load financial data from various sources")
logger.info("• Use create_statement_dataframe() to build proper statement structures")
logger.info("• Statement configurations automatically handle calculation nodes")
logger.info("• The metrics registry provides comprehensive financial analysis")
logger.info("• Always work with the high-level abstractions, not core directly")
