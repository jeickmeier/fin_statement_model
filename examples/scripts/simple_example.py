"""Simple example demonstrating the proper use of the financial statement model library.

This example shows the recommended approach for:
1. Loading financial data
2. Using statement configurations to define structure
3. Performing calculations and analysis
4. Working with metrics

The key principle: Use the high-level statement abstractions rather than
building graphs directly with core functionality.
"""

import logging
from pathlib import Path

from fin_statement_model.io import read_data
from fin_statement_model.statements import create_statement_dataframe
from fin_statement_model.core.metrics import (
    calculate_metric,
    interpret_metric,
    metric_registry,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    """Run a simple financial analysis example."""
    print("=" * 60)
    print("SIMPLE FINANCIAL STATEMENT MODEL EXAMPLE")
    print("=" * 60)

    # Step 1: Prepare your financial data
    # This could come from various sources (Excel, API, CSV, etc.)
    financial_data = {
        # Balance Sheet items
        "cash_equivalents": {"2021": 10000, "2022": 12000, "2023": 15000},
        "accounts_receivable": {"2021": 5000, "2022": 5500, "2023": 6000},
        "inventory": {"2021": 8000, "2022": 8500, "2023": 9000},
        "ppe": {"2021": 20000, "2022": 22000, "2023": 25000},
        "accounts_payable": {"2021": 3000, "2022": 3200, "2023": 3500},
        "long_term_debt": {"2021": 15000, "2022": 14000, "2023": 13000},
        "common_stock": {"2021": 10000, "2022": 10000, "2023": 10000},
        "retained_earnings": {"2021": 15000, "2022": 18300, "2023": 22500},
        # Income Statement items
        "revenue": {"2021": 50000, "2022": 55000, "2023": 60000},
        "cogs": {"2021": -30000, "2022": -32000, "2023": -35000},
        "operating_expenses": {"2021": -10000, "2022": -11000, "2023": -12000},
        "interest_expense": {"2021": -1500, "2022": -1400, "2023": -1300},
        "tax_expense": {"2021": -2125, "2022": -2650, "2023": -2925},
        # Additional items for metrics
        "total_assets": {"2021": 43000, "2022": 48000, "2023": 55000},
        "total_liabilities": {"2021": 18000, "2022": 17200, "2023": 16500},
        "total_equity": {"2021": 25000, "2022": 28300, "2023": 32500},
        "net_income": {"2021": 6375, "2022": 7950, "2023": 8775},
        "shares_outstanding": {"2021": 1000, "2022": 1000, "2023": 1000},
    }

    print("\nStep 1: Loading financial data...")
    # Load data into a graph using the dict reader
    graph = read_data(format_type="dict", source=financial_data)
    print(f"✓ Loaded data for periods: {graph.periods}")
    print(f"✓ Created {len(graph.nodes)} data nodes")

    # Step 2: Use statement configurations to define structure
    # For this example, we'll use the existing income statement config
    workspace_root = Path(__file__).resolve().parents[2]
    income_stmt_config = workspace_root / "examples/examples/income_statement.json"

    if income_stmt_config.exists():
        print("\nStep 2: Building statement structure...")
        try:
            # This will:
            # 1. Load and validate the statement configuration
            # 2. Build the statement structure
            # 3. Populate the graph with calculation nodes
            # 4. Generate a formatted dataframe
            income_df = create_statement_dataframe(
                graph=graph,
                config_path_or_dir=str(income_stmt_config),
                format_kwargs={
                    "should_apply_signs": True,
                    "number_format": ",.0f",
                },
            )

            print("✓ Statement structure built successfully")
            print("\nIncome Statement:")
            print(income_df.to_string(index=False))
        except Exception as e:
            logger.warning(f"Could not build full statement structure: {e}")
            print("⚠ Using simplified analysis instead")

    # Step 3: Calculate and analyze key metrics
    print("\nStep 3: Calculating financial metrics...")

    # Get all nodes as a dictionary for metric calculations
    data_nodes = {node.name: node for node in graph.nodes.values()}

    # Define metrics to calculate
    metrics_to_analyze = [
        "gross_profit_margin",
        "operating_margin",
        "net_profit_margin",
        "return_on_assets",
        "return_on_equity",
        "debt_to_equity_ratio",
        "current_ratio",
        "earnings_per_share",
    ]

    print("\nKey Financial Metrics (2023):")
    print("-" * 40)

    for metric_name in metrics_to_analyze:
        try:
            # Calculate the metric
            value = calculate_metric(metric_name, data_nodes, "2023")

            # Get metric definition and interpretation
            metric_def = metric_registry.get(metric_name)
            interpretation = interpret_metric(metric_def, value)

            # Format the value
            if "ratio" in metric_name or "margin" in metric_name:
                value_str = f"{value:.2f}%" if "margin" in metric_name else f"{value:.2f}"
            else:
                value_str = f"{value:,.2f}"

            # Get rating emoji
            rating = interpretation["rating"].upper()
            status = {"EXCELLENT": "🟢", "GOOD": "🟢", "FAIR": "🟡", "POOR": "🔴"}.get(rating, "⚪")

            print(f"{status} {metric_def.name}: {value_str} ({rating})")

        except Exception as e:
            print(f"❌ {metric_name}: Could not calculate - {str(e)[:50]}...")

    # Step 4: Show trend analysis
    print("\nStep 4: Trend Analysis (Revenue Growth):")
    print("-" * 40)

    try:
        revenue_node = graph.get_node("revenue")
        if revenue_node:
            revenue_values = revenue_node.get_values()
            years = sorted(revenue_values.keys())

            for i in range(1, len(years)):
                prev_year = years[i - 1]
                curr_year = years[i]
                prev_val = revenue_values[prev_year]
                curr_val = revenue_values[curr_year]

                growth = ((curr_val - prev_val) / prev_val) * 100
                print(f"{prev_year} → {curr_year}: {growth:.1f}% growth")
    except Exception as e:
        print(f"Could not perform trend analysis: {e}")

    print("\n" + "=" * 60)
    print("EXAMPLE COMPLETE")
    print("=" * 60)
    print("\nKey Takeaways:")
    print("• Use read_data() to load financial data from various sources")
    print("• Use create_statement_dataframe() to build proper statement structures")
    print("• Statement configurations automatically handle calculation nodes")
    print("• The metrics registry provides comprehensive financial analysis")
    print("• Always work with the high-level abstractions, not core directly")


if __name__ == "__main__":
    main()
