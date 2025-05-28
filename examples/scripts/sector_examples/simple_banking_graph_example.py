"""Simplified Banking Graph Analysis Example.

This example demonstrates core functionalities of the financial statement model library
with a focus on banking data. It concisely shows:

1. Node name validation (simplified output).
2. Building a graph with pre-defined banking data nodes using statement configurations.
3. Basic graph structure check.
4. Calculation and analysis of key banking metrics using the metrics registry.
5. Brief exploration of the metrics registry capabilities.

This version is streamlined for easier understanding of fundamental concepts.
"""

import logging
from pathlib import Path
import tempfile
import yaml
from contextlib import suppress

from fin_statement_model.core.graph import Graph
from fin_statement_model.io.validation import UnifiedNodeValidator
from fin_statement_model.io import read_data
from fin_statement_model.statements import create_statement_dataframe
from fin_statement_model.core.metrics import (
    metric_registry,
    calculate_metric,
    interpret_metric,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def step_1_validate_node_names() -> dict[str, str]:
    """Step 1: Demonstrate node name validation for banking data."""
    print("=" * 60)
    print("STEP 1: NODE NAME VALIDATION (Simplified Output)")
    print("=" * 60)

    raw_banking_names = [
        "loans",
        "npl",
        "deposits",
        "allowance",
        "equity",
        "nii",
        "tier_1_capital",
        "rwa",
        "hqla",
        "net_charge_offs",
        "invalid_node_example",
    ]
    print(f"Raw node names: {raw_banking_names}")

    validator = UnifiedNodeValidator(auto_standardize=True, warn_on_non_standard=False)  # Quieter
    validation_results = validator.validate_batch(raw_banking_names)

    standardized_mapping = {}
    print("\nValidation Mapping (Original -> Standardized | Status):")
    for original, result in validation_results.items():
        status = "VALID" if result.is_valid else "INVALID/UNRECOGNIZED"
        print(f"  '{original}' -> '{result.standardized_name}' | {status}")
        if result.is_valid:
            standardized_mapping[original] = result.standardized_name

    # Count by category
    categories = {}
    for result in validation_results.values():
        categories[result.category] = categories.get(result.category, 0) + 1

    alternate_count = categories.get("alternate", 0)
    unrecognized_count = categories.get("custom", 0) + categories.get("invalid", 0)

    print(f"\nSummary: {alternate_count} alternates mapped, {unrecognized_count} unrecognized.")

    return standardized_mapping


def create_banking_statement_config() -> str:
    """Create a temporary banking statement configuration file."""
    banking_statement_config = {
        "id": "banking_statement",
        "name": "Banking Statement",
        "description": "Simplified banking statement for analysis",
        "metadata": {
            "type": "financial_statement",
            "version": "1.0.0",
            "display_options": {
                "sign_convention": "standard",
                "show_subtotals": True,
                "decimal_places": 0,
            },
        },
        "sections": [
            {
                "id": "assets_section",
                "name": "Assets",
                "description": "Banking assets",
                "items": [
                    {
                        "id": "total_loans",
                        "name": "Total Loans",
                        "node_id": "total_loans",
                        "description": "Total loan portfolio",
                        "sign_convention": "positive",
                    },
                    {
                        "id": "allowance_for_loan_losses",
                        "name": "Allowance for Loan Losses",
                        "node_id": "allowance_for_loan_losses",
                        "description": "Reserve for potential loan losses",
                        "sign_convention": "negative",
                    },
                    {
                        "id": "non_performing_loans",
                        "name": "Non-Performing Loans",
                        "node_id": "non_performing_loans",
                        "description": "Loans in default or close to default",
                        "sign_convention": "positive",
                    },
                    {
                        "id": "liquid_assets",
                        "name": "Liquid Assets",
                        "node_id": "liquid_assets",
                        "description": "Highly liquid assets",
                        "sign_convention": "positive",
                    },
                    {
                        "id": "total_assets",
                        "name": "Total Assets",
                        "node_id": "total_assets",
                        "description": "Total bank assets",
                        "sign_convention": "positive",
                    },
                ],
            },
            {
                "id": "liabilities_section",
                "name": "Liabilities",
                "description": "Banking liabilities",
                "items": [
                    {
                        "id": "total_deposits",
                        "name": "Total Deposits",
                        "node_id": "total_deposits",
                        "description": "Customer deposits",
                        "sign_convention": "positive",
                    }
                ],
            },
            {
                "id": "capital_section",
                "name": "Capital",
                "description": "Regulatory capital",
                "items": [
                    {
                        "id": "total_shareholders_equity",
                        "name": "Total Shareholders Equity",
                        "node_id": "total_shareholders_equity",
                        "description": "Total equity capital",
                        "sign_convention": "positive",
                    },
                    {
                        "id": "total_tier_1_capital",
                        "name": "Total Tier 1 Capital",
                        "node_id": "total_tier_1_capital",
                        "description": "Core regulatory capital",
                        "sign_convention": "positive",
                    },
                    {
                        "id": "common_equity_tier_1",
                        "name": "Common Equity Tier 1",
                        "node_id": "common_equity_tier_1",
                        "description": "Highest quality regulatory capital",
                        "sign_convention": "positive",
                    },
                    {
                        "id": "total_risk_weighted_assets",
                        "name": "Total Risk Weighted Assets",
                        "node_id": "total_risk_weighted_assets",
                        "description": "Risk-adjusted asset base",
                        "sign_convention": "positive",
                    },
                ],
            },
            {
                "id": "income_section",
                "name": "Income",
                "description": "Income statement items",
                "items": [
                    {
                        "id": "net_interest_income",
                        "name": "Net Interest Income",
                        "node_id": "net_interest_income",
                        "description": "Interest income minus interest expense",
                        "sign_convention": "positive",
                    },
                    {
                        "id": "total_non_interest_income",
                        "name": "Total Non-Interest Income",
                        "node_id": "total_non_interest_income",
                        "description": "Fee and other non-interest income",
                        "sign_convention": "positive",
                    },
                    {
                        "id": "total_non_interest_expense",
                        "name": "Total Non-Interest Expense",
                        "node_id": "total_non_interest_expense",
                        "description": "Operating expenses",
                        "sign_convention": "negative",
                    },
                    {
                        "id": "net_income",
                        "name": "Net Income",
                        "node_id": "net_income",
                        "description": "Bottom line profit",
                        "sign_convention": "positive",
                    },
                ],
            },
            {
                "id": "liquidity_section",
                "name": "Liquidity Metrics",
                "description": "Liquidity management data",
                "items": [
                    {
                        "id": "high_quality_liquid_assets",
                        "name": "High Quality Liquid Assets",
                        "node_id": "high_quality_liquid_assets",
                        "description": "HQLA for regulatory liquidity",
                        "sign_convention": "positive",
                    },
                    {
                        "id": "net_cash_outflows_30_days",
                        "name": "Net Cash Outflows (30 days)",
                        "node_id": "net_cash_outflows_30_days",
                        "description": "Expected net cash outflows",
                        "sign_convention": "positive",
                    },
                ],
            },
            {
                "id": "credit_quality_section",
                "name": "Credit Quality",
                "description": "Credit risk metrics",
                "items": [
                    {
                        "id": "net_charge_offs",
                        "name": "Net Charge-offs",
                        "node_id": "net_charge_offs",
                        "description": "Loans written off net of recoveries",
                        "sign_convention": "positive",
                    },
                    {
                        "id": "average_total_loans",
                        "name": "Average Total Loans",
                        "node_id": "average_total_loans",
                        "description": "Average loan balance for period",
                        "sign_convention": "positive",
                    },
                    {
                        "id": "average_earning_assets",
                        "name": "Average Earning Assets",
                        "node_id": "average_earning_assets",
                        "description": "Average interest-earning assets",
                        "sign_convention": "positive",
                    },
                    {
                        "id": "average_total_assets",
                        "name": "Average Total Assets",
                        "node_id": "average_total_assets",
                        "description": "Average total assets for period",
                        "sign_convention": "positive",
                    },
                    {
                        "id": "average_total_equity",
                        "name": "Average Total Equity",
                        "node_id": "average_total_equity",
                        "description": "Average equity for period",
                        "sign_convention": "positive",
                    },
                ],
            },
        ],
    }

    # Create a temporary file for the config
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(banking_statement_config, f)
        return f.name


def step_2_build_graph() -> tuple[Graph, str]:
    """Step 2: Build a graph with banking data nodes using statement functionality."""
    print("\n" + "=" * 60)
    print("STEP 2: BUILDING BANKING GRAPH (Using Statement Functionality)")
    print("=" * 60)

    # First, create the banking data
    banking_data = {
        "total_loans": {
            "2021": 45_000_000_000,
            "2022": 48_000_000_000,
            "2023": 52_000_000_000,
        },
        "allowance_for_loan_losses": {
            "2021": 675_000_000,
            "2022": 720_000_000,
            "2023": 780_000_000,
        },
        "non_performing_loans": {
            "2021": 450_000_000,
            "2022": 480_000_000,
            "2023": 520_000_000,
        },
        "total_deposits": {
            "2021": 52_000_000_000,
            "2022": 56_000_000_000,
            "2023": 60_000_000_000,
        },
        "total_shareholders_equity": {
            "2021": 6_500_000_000,
            "2022": 7_000_000_000,
            "2023": 7_500_000_000,
        },
        "net_interest_income": {
            "2021": 2_100_000_000,
            "2022": 2_300_000_000,
            "2023": 2_600_000_000,
        },
        "total_non_interest_income": {
            "2021": 800_000_000,
            "2022": 850_000_000,
            "2023": 900_000_000,
        },
        "total_non_interest_expense": {
            "2021": 1_800_000_000,
            "2022": 1_900_000_000,
            "2023": 2_000_000_000,
        },
        "total_tier_1_capital": {
            "2021": 5_500_000_000,
            "2022": 5_900_000_000,
            "2023": 6_300_000_000,
        },
        "common_equity_tier_1": {
            "2021": 5_200_000_000,
            "2022": 5_600_000_000,
            "2023": 6_000_000_000,
        },
        "total_risk_weighted_assets": {
            "2021": 42_000_000_000,
            "2022": 45_000_000_000,
            "2023": 48_000_000_000,
        },
        "high_quality_liquid_assets": {
            "2021": 12_000_000_000,
            "2022": 13_000_000_000,
            "2023": 14_000_000_000,
        },
        "net_cash_outflows_30_days": {
            "2021": 10_000_000_000,
            "2022": 10_500_000_000,
            "2023": 11_000_000_000,
        },
        "net_charge_offs": {
            "2021": 225_000_000,
            "2022": 240_000_000,
            "2023": 260_000_000,
        },
        "average_total_loans": {
            "2021": 44_000_000_000,
            "2022": 46_500_000_000,
            "2023": 50_000_000_000,
        },
        "average_earning_assets": {
            "2021": 58_000_000_000,
            "2022": 62_000_000_000,
            "2023": 66_000_000_000,
        },
        "average_total_assets": {
            "2021": 65_000_000_000,
            "2022": 70_000_000_000,
            "2023": 75_000_000_000,
        },
        "net_income": {"2021": 850_000_000, "2022": 950_000_000, "2023": 1_100_000_000},
        "average_total_equity": {
            "2021": 6_250_000_000,
            "2022": 6_750_000_000,
            "2023": 7_250_000_000,
        },
        "liquid_assets": {
            "2021": 15_000_000_000,
            "2022": 16_000_000_000,
            "2023": 17_000_000_000,
        },
        "total_assets": {
            "2021": 65_000_000_000,
            "2022": 70_000_000_000,
            "2023": 75_000_000_000,
        },
    }

    print("Loading banking data into graph...")
    # Create graph with data using the dict reader
    graph = read_data(format_type="dict", source=banking_data)
    print(f"Created graph with periods: {graph.periods}")

    # Create the statement configuration file
    config_path = create_banking_statement_config()
    print("Created banking statement configuration")

    # Use create_statement_dataframe to build the statement structure
    # This will populate the graph with any calculation nodes defined in the config
    print("Building statement structure...")
    try:
        _ = create_statement_dataframe(
            graph=graph,
            config_path_or_dir=config_path,
            format_kwargs={
                "should_apply_signs": True,
                "number_format": ",.0f",
            },
        )
        print("Statement structure built successfully")
    except Exception as e:
        logger.warning(f"Statement building encountered non-critical error: {e}")
        # Continue anyway as we mainly need the data nodes for metrics

    print(f"Total nodes in graph: {len(graph.nodes)}")

    return graph, config_path


def step_3_analyze_structure(graph: Graph) -> None:
    """Step 3: Basic graph structure check."""
    print("\n" + "=" * 60)
    print("STEP 3: GRAPH STRUCTURE CHECK")
    print("=" * 60)

    print("Graph Overview:")
    print(f"  Total data nodes: {len(graph.get_financial_statement_items())}")
    print(f"  Time periods: {graph.periods}")
    # Example: list a few nodes
    if graph.nodes:
        print(f"  First few nodes: {list(graph.nodes.keys())[:3]}...")
    print("\n✓ Graph structure check complete")


def analyze_key_banking_metrics(graph: Graph, period: str = "2023") -> None:
    """Calculate and analyze a few key banking metrics for a given period."""
    print("\n" + "=" * 60)
    print(f"STEP 4: KEY BANKING METRICS ANALYSIS (Period: {period})")
    print("=" * 60)

    data_nodes = {node.name: node for node in graph.nodes.values()}

    key_metrics_to_analyze = {
        "Asset Quality": [
            "non_performing_loan_ratio",
            "allowance_to_loans_ratio",
        ],
        "Capital Adequacy": [
            "common_equity_tier_1_ratio",
            "tier_1_capital_ratio",
        ],
        "Liquidity": [
            "liquidity_coverage_ratio",
            "loan_to_deposit_ratio",
        ],
        "Profitability": [
            "net_interest_margin",
            "return_on_assets_(banking)",
            "efficiency_ratio",
        ],
    }

    for category, metrics_in_category in key_metrics_to_analyze.items():
        print(f"\n--- {category} ---")
        for metric_name in metrics_in_category:
            try:
                value = calculate_metric(metric_name, data_nodes, period)
                metric_def = metric_registry.get(metric_name)
                interpretation = interpret_metric(metric_def, value)

                value_str = (
                    f"{value:.2f}%"
                    if "ratio" in metric_name or "margin" in metric_name
                    else f"{value:.2f}"
                )
                rating = interpretation["rating"].upper()
                status_icon = {
                    "EXCELLENT": "🟢",
                    "GOOD": "🟢",
                    "FAIR": "🟡",
                    "POOR": "🔴",
                    "CRITICAL": "🔴",
                }.get(rating, "⚪")

                print(f"  {status_icon} {metric_def.name}: {value_str} ({rating})")
            except Exception as e:
                print(f"  ❌ {metric_name}: Could not calculate - {str(e)[:70]}...")
    print("\n✓ Key metrics analysis complete.")


def explore_metrics_registry() -> None:
    """Step 5: Briefly explore the metrics registry capabilities."""
    print("\n" + "=" * 60)
    print("STEP 5: METRICS REGISTRY EXPLORATION (Simplified)")
    print("=" * 60)

    print(f"Total metrics in registry: {len(metric_registry)}")

    # Show a few categories and their metric counts
    print("\nExample Metric Categories:")
    all_categories = set(metric_registry.get(m).category for m in metric_registry.list_metrics())
    for i, category in enumerate(sorted(list(all_categories))):
        if i < 5:  # Show first 5 categories as an example
            count = sum(
                1
                for m in metric_registry.list_metrics()
                if metric_registry.get(m).category == category
            )
            print(f"  - {category}: {count} metrics")
        elif i == 5:
            print("  ... and more categories.")
            break

    # Show example metric definition
    example_metric_name = "non_performing_loan_ratio"
    print(f"\nExample Metric Definition ('{example_metric_name}'):")
    try:
        metric_def = metric_registry.get(example_metric_name)
        print(f"  Name: {metric_def.name}")
        print(f"  Description: {metric_def.description}")
        print(f"  Formula: {metric_def.formula}")
        print(f"  Inputs: {metric_def.inputs}")
    except Exception as e:
        print(f"  Error accessing metric '{example_metric_name}': {e}")
    print("\n✓ Metrics registry exploration complete.")


def main() -> None:
    """Run the simplified banking graph analysis example."""
    print("SIMPLIFIED BANKING GRAPH ANALYSIS EXAMPLE")
    print("Demonstrating core library features with banking data using statement functionality.")

    # Step 1: Node name validation
    step_1_validate_node_names()

    # Step 2: Build the graph using statement functionality
    graph, config_path = step_2_build_graph()

    # Step 3: Analyze structure
    step_3_analyze_structure(graph)

    # Step 4: Analyze Key Banking Metrics
    analyze_key_banking_metrics(graph, period="2023")

    # Step 5: Explore metrics registry
    explore_metrics_registry()

    # Clean up temporary config file
    with suppress(Exception):
        Path(config_path).unlink()

    print("\n" + "=" * 60)
    print("SIMPLIFIED EXAMPLE COMPLETE")
    print("=" * 60)
    print("\nKey Takeaways:")
    print("1. Node validation helps ensure data quality upfront.")
    print("2. Graphs should be built using statement configurations for proper structure.")
    print("3. Statement functionality automatically handles calculation nodes.")
    print("4. Key financial metrics are easily calculated using the registry.")
    print("5. Metric interpretations provide quick insights (e.g., ratings).")
    print("6. The registry offers a broad set of pre-defined metrics.")


if __name__ == "__main__":
    main()
