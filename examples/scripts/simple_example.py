"""Simplified Financial Statement Model Example.

This example demonstrates the most straightforward way to use the library
for basic financial analysis tasks without complex configurations.
"""

import logging
import sys
from pathlib import Path

from fin_statement_model import get_config, update_config
from fin_statement_model.io import read_data
from fin_statement_model.statements import create_statement_dataframe
from fin_statement_model.core.metrics.registry import metric_registry
from fin_statement_model.core.metrics.models import MetricDefinition
from fin_statement_model.core.metrics import calculate_metric

# Set up logging before importing other modules
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)

# Get configuration
config = get_config()

# Configure logging using centralized config
# Note: This is now handled automatically by the library, but you can override
if config.logging.detailed:
    # The library already sets up logging based on config
    pass
else:
    # For this example, we'll ensure INFO level is set
    update_config({"logging": {"level": "INFO"}})

logger = logging.getLogger(__name__)

# Load metric definitions
metrics_dir = (
    Path(__file__).parent.parent.parent / "fin_statement_model" / "core" / "metrics" / "metric_defn"
)
if metrics_dir.exists():
    # Load metrics from all subdirectories
    for subdir in metrics_dir.iterdir():
        if subdir.is_dir():
            try:
                count = metric_registry.load_metrics_from_directory(subdir)
                logger.info(f"Loaded {count} metrics from {subdir.name}")
            except Exception as e:
                logger.warning(f"Failed to load metrics from {subdir}: {e}")

# Example configuration path (you would replace with your actual path)
INCOME_STATEMENT_CONFIG = Path(__file__).parent / "configs" / "income_statement.yaml"

# If config doesn't exist, provide a helpful error message
if not INCOME_STATEMENT_CONFIG.exists():
    logger.error(f"Configuration file not found: {INCOME_STATEMENT_CONFIG}")
    logger.error("Please ensure the income_statement.yaml file exists in the configs directory")
    sys.exit(1)

logger.info("=" * 60)
logger.info("SIMPLE FINANCIAL STATEMENT MODEL EXAMPLE")
logger.info("=" * 60)

# Sample data - in practice, you'd load from Excel/CSV/API
sample_data = {
    # Income Statement items with realistic values
    "Revenue": {"2022": 1000000, "2023": 1200000},
    "revenue": {"2022": 1000000, "2023": 1200000},  # Alias for metrics
    "COGS": {"2022": 600000, "2023": 700000},
    "cost_of_goods_sold": {"2022": 600000, "2023": 700000},  # Alias for metrics
    "R&D": {"2022": 100000, "2023": 120000},
    "SG&A": {"2022": 150000, "2023": 180000},
    "D&A": {"2022": 50000, "2023": 60000},
    "Interest Expense": {"2022": 20000, "2023": 25000},
    "Taxes": {"2022": 32500, "2023": 43750},
    # Add operating income and net income for metrics
    "operating_income": {"2022": 200000, "2023": 240000},
    "net_income": {"2022": 147500, "2023": 175250},
    # Balance Sheet items for ratio calculations
    "total_assets": {"2022": 2000000, "2023": 2500000},
    "current_assets": {"2022": 500000, "2023": 600000},
    "current_liabilities": {"2022": 300000, "2023": 350000},
    "total_liabilities": {"2022": 800000, "2023": 1000000},
    "total_debt": {"2022": 800000, "2023": 1000000},  # Alias for metrics
    "shareholders_equity": {"2022": 1200000, "2023": 1500000},
    "total_equity": {"2022": 1200000, "2023": 1500000},  # Alias for metrics
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
# The library now uses config defaults automatically!
try:
    logger.info("\nStep 2: Building statement structure...")

    # If scale factor is set, mention it
    if config.display.scale_factor != 1.0:
        logger.info(
            f"Note: Values will be scaled by {config.display.scale_factor} ({config.display.default_units})"
        )

    # Much cleaner - library uses config defaults internally
    income_df = create_statement_dataframe(
        graph=graph,
        config_path_or_dir=str(INCOME_STATEMENT_CONFIG),
        # Only specify overrides if needed, otherwise config defaults are used
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
    "gross_profit_margin",
    "operating_profit_margin",
    "net_profit_margin",
    "return_on_equity",
    "current_ratio",
    "debt_to_equity_ratio",
]

# Calculate and display metrics
logger.info("\nKey Financial Metrics (2023):")
logger.info("-" * 40)

# Prepare data nodes for metric calculations
# Get all nodes from the graph
data_nodes = graph.nodes  # Just use the nodes property directly

for metric_name in key_metrics:
    try:
        # Get metric definition
        metric_def: MetricDefinition = metric_registry.get(metric_name)

        # Calculate value using the helper function
        value = calculate_metric(metric_name, data_nodes, "2023")

        # Format based on metric type and config
        if "margin" in metric_name or metric_name == "return_on_equity":
            # Use percentage format from config
            value_str = (
                f"{value:.1f}%"  # Show value without * 100 since metric already returns percentage
            )
        else:
            # Use number format from config
            value_str = f"{value:.2f}"

        # Simple rating system
        if metric_name == "current_ratio":
            rating = "Good" if value > 1.5 else "Needs attention"
        elif metric_name == "debt_to_equity_ratio":
            rating = "Conservative" if value < 1.0 else "Leveraged"
        elif "margin" in metric_name or metric_name == "return_on_equity":
            rating = "Healthy" if value > 10 else "Review needed"  # For percentage metrics
        else:
            rating = "Healthy" if value > 0.1 else "Review needed"

        status = "✓" if rating in ["Good", "Conservative", "Healthy"] else "⚠"
        logger.info(f"{status} {metric_def.name}: {value_str} ({rating})")

    except:  # noqa: E722
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

        prev_revenue = graph.get_node("Revenue").get_value(prev_year)
        curr_revenue = graph.get_node("Revenue").get_value(curr_year)

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
logger.info("• The centralized config system controls formatting and display settings")
