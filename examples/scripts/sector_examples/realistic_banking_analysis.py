"""Realistic Banking Analysis Example.

This example demonstrates a practical approach to banking analysis using the
financial statement model library. It shows:

1. Loading banking data from a realistic source (simulated)
2. Automatic node name validation and standardization during data loading
3. Building a graph with validated data in one step
4. Comprehensive banking metrics analysis
5. Professional reporting and interpretation

This example is designed to be more concise and realistic compared to the
step-by-step educational example.
"""

import pandas as pd
from typing import Any
from fin_statement_model.core.graph import Graph
from fin_statement_model.io.node_name_validator import NodeNameValidator
from fin_statement_model.core.metrics import (
    metric_registry,
    calculate_metric,
    interpret_metric,
)


def load_banking_data() -> pd.DataFrame:
    """Simulate loading banking data from a real source.

    In practice, this would load from Excel, CSV, database, or API.

    Returns:
        DataFrame with banking data using realistic field names.
    """
    # Simulate data that might come from a bank's financial system
    # with non-standardized field names that map to standard registry names
    raw_data = {
        "metric_name": [
            # Asset items (using alternate names that map to standard names)
            "gross_loans",  # -> total_loans
            "npl",  # -> non_performing_loans
            "alll",  # -> allowance_for_loan_losses
            "net_charge_offs",  # standard name
            "total_assets",  # standard name
            "liquid_assets",  # standard name
            "hqla",  # -> high_quality_liquid_assets
            # Liability and equity items
            "deposits",  # -> total_deposits
            "stockholders_equity",  # -> total_shareholders_equity
            # Income statement items
            "nii",  # -> net_interest_income
            "non_interest_income",  # -> total_non_interest_income
            "non_interest_expense",  # -> total_non_interest_expense
            "net_income",  # standard name
            # Regulatory capital
            "tier_1_capital",  # -> total_tier_1_capital
            "cet1",  # -> common_equity_tier_1
            "rwa",  # -> total_risk_weighted_assets
            # Liquidity metrics
            "lcr_outflows",  # -> net_cash_outflows_30_days
            # Average balances for ratios (these need to be created as calculated nodes)
            "average_total_loans",  # standard name
            "average_total_assets",  # standard name
            "average_total_equity",  # standard name
            "average_earning_assets",  # standard name
        ],
        "2021": [
            45_000_000_000,  # gross_loans
            450_000_000,  # npl
            675_000_000,  # alll
            225_000_000,  # net_charge_offs
            65_000_000_000,  # total_assets
            15_000_000_000,  # liquid_assets
            12_000_000_000,  # hqla
            52_000_000_000,  # deposits
            6_500_000_000,  # stockholders_equity
            2_100_000_000,  # nii
            800_000_000,  # non_interest_income
            1_800_000_000,  # non_interest_expense
            850_000_000,  # net_income
            5_500_000_000,  # tier_1_capital
            5_200_000_000,  # cet1
            42_000_000_000,  # rwa
            10_000_000_000,  # lcr_outflows
            44_000_000_000,  # average_total_loans
            65_000_000_000,  # average_total_assets
            6_250_000_000,  # average_total_equity
            58_000_000_000,  # average_earning_assets
        ],
        "2022": [
            48_000_000_000,  # gross_loans
            480_000_000,  # npl
            720_000_000,  # alll
            240_000_000,  # net_charge_offs
            70_000_000_000,  # total_assets
            16_000_000_000,  # liquid_assets
            13_000_000_000,  # hqla
            56_000_000_000,  # deposits
            7_000_000_000,  # stockholders_equity
            2_300_000_000,  # nii
            850_000_000,  # non_interest_income
            1_900_000_000,  # non_interest_expense
            950_000_000,  # net_income
            5_900_000_000,  # tier_1_capital
            5_600_000_000,  # cet1
            45_000_000_000,  # rwa
            10_500_000_000,  # lcr_outflows
            46_500_000_000,  # average_total_loans
            70_000_000_000,  # average_total_assets
            6_750_000_000,  # average_total_equity
            62_000_000_000,  # average_earning_assets
        ],
        "2023": [
            52_000_000_000,  # gross_loans
            520_000_000,  # npl
            780_000_000,  # alll
            260_000_000,  # net_charge_offs
            75_000_000_000,  # total_assets
            17_000_000_000,  # liquid_assets
            14_000_000_000,  # hqla
            60_000_000_000,  # deposits
            7_500_000_000,  # stockholders_equity
            2_600_000_000,  # nii
            900_000_000,  # non_interest_income
            2_000_000_000,  # non_interest_expense
            1_100_000_000,  # net_income
            6_300_000_000,  # tier_1_capital
            6_000_000_000,  # cet1
            48_000_000_000,  # rwa
            11_000_000_000,  # lcr_outflows
            50_000_000_000,  # average_total_loans
            75_000_000_000,  # average_total_assets
            7_250_000_000,  # average_total_equity
            66_000_000_000,  # average_earning_assets
        ],
    }

    return pd.DataFrame(raw_data)


def load_and_validate_banking_data() -> tuple[Graph, dict[str, Any]]:
    """Load banking data and create a validated graph in one step.

    Returns:
        Tuple of (graph, validation_summary).
    """
    print("=" * 60)
    print("LOADING AND VALIDATING BANKING DATA")
    print("=" * 60)

    # Load raw data
    print("Loading banking data from source...")
    df = load_banking_data()
    print(f"Loaded {len(df)} data points across {len(df.columns) - 1} periods")

    # Set up validator
    validator = NodeNameValidator(
        strict_mode=False,
        auto_standardize=True,
        warn_on_non_standard=False,  # Reduce noise for demo
    )

    # Validate and standardize all node names
    print("\nValidating and standardizing node names...")
    raw_names = df["metric_name"].tolist()
    validation_results = validator.validate_batch(raw_names)

    # Create standardized mapping
    name_mapping = {
        original: standardized for original, (standardized, _, _) in validation_results.items()
    }

    # Create graph with validated data
    periods = [col for col in df.columns if col != "metric_name"]
    graph = Graph(periods=periods)

    print(f"Building graph with {len(periods)} periods...")

    # Add all data to graph using standardized names
    for _, row in df.iterrows():
        original_name = row["metric_name"]
        standardized_name = name_mapping[original_name]

        # Create period data dict
        period_data = {period: row[period] for period in periods}

        graph.add_financial_statement_item(standardized_name, period_data)

    # Get validation summary
    summary = validator.get_validation_summary()

    print("\nGraph created successfully:")
    print(f"  Total nodes: {len(graph.nodes)}")
    print(f"  Periods: {periods}")
    print(f"  Standardized names: {summary['standard_names']}")
    print(f"  Alternate names converted: {summary['alternate_names']}")
    print(f"  Unrecognized names: {summary['unrecognized_names']}")

    return graph, summary


def analyze_banking_performance(graph: Graph, focus_period: str = "2023") -> None:
    """Perform comprehensive banking performance analysis.

    Args:
        graph: The banking data graph.
        focus_period: Period to focus analysis on.
    """
    print("\n" + "=" * 60)
    print(f"BANKING PERFORMANCE ANALYSIS - {focus_period}")
    print("=" * 60)

    data_nodes = {node.name: node for node in graph.nodes.values()}

    # Define comprehensive banking metrics by category
    metric_categories = {
        "Asset Quality": [
            "non_performing_loan_ratio",
            "allowance_to_loans_ratio",
            "charge_off_rate",
            "provision_coverage_ratio",
        ],
        "Capital Adequacy": [
            "common_equity_tier_1_ratio",
            "tier_1_capital_ratio",
            "total_capital_ratio",
            "tier_1_leverage_ratio",
        ],
        "Liquidity": [
            "liquidity_coverage_ratio",
            "loan_to_deposit_ratio",
            "deposits_to_loans_ratio",
            "liquid_assets_ratio",
        ],
        "Profitability": [
            "net_interest_margin",
            "efficiency_ratio",
            "return_on_assets_(banking)",
            "return_on_equity_(banking)",
            "fee_income_ratio",
        ],
    }

    # Calculate and display metrics by category
    for category, metrics in metric_categories.items():
        print(f"\n=== {category} ===")

        for metric_name in metrics:
            try:
                # Calculate metric
                value = calculate_metric(metric_name, data_nodes, focus_period)

                # Get metric definition and interpretation
                metric_def = metric_registry.get(metric_name)
                interpretation = interpret_metric(metric_def, value)

                # Format output based on metric type
                if (
                    "ratio" in metric_name.lower()
                    or "margin" in metric_name.lower()
                    or metric_name == "charge_off_rate"
                ):
                    value_str = f"{value:.2f}%"
                else:
                    value_str = f"{value:.2f}"

                rating = interpretation["rating"].upper()
                status_icon = {
                    "EXCELLENT": "🟢",
                    "GOOD": "🟢",
                    "FAIR": "🟡",
                    "POOR": "🔴",
                    "CRITICAL": "🔴",
                }.get(rating, "⚪")

                print(f"{status_icon} {metric_def.name}: {value_str} ({rating})")

            except Exception as e:
                print(f"❌ {metric_name}: Could not calculate - {str(e)[:50]}...")


def generate_trend_analysis(graph: Graph) -> None:
    """Generate trend analysis across all periods.

    Args:
        graph: The banking data graph.
    """
    print("\n" + "=" * 60)
    print("TREND ANALYSIS")
    print("=" * 60)

    data_nodes = {node.name: node for node in graph.nodes.values()}

    # Key metrics for trend analysis
    trend_metrics = [
        "non_performing_loan_ratio",
        "tier_1_capital_ratio",
        "return_on_assets_(banking)",
        "efficiency_ratio",
        "net_interest_margin",
        "liquidity_coverage_ratio",
    ]

    print(f"{'Metric':<35} {'2021':<10} {'2022':<10} {'2023':<10} {'Trend':<10}")
    print("-" * 75)

    for metric_name in trend_metrics:
        try:
            values = []
            for period in graph.periods:
                value = calculate_metric(metric_name, data_nodes, period)
                values.append(value)

            # Determine trend
            if len(values) >= 2:
                if values[-1] > values[-2]:
                    trend = "📈 UP"
                elif values[-1] < values[-2]:
                    trend = "📉 DOWN"
                else:
                    trend = "➡️ FLAT"
            else:
                trend = "N/A"

            # Get metric name
            metric_def = metric_registry.get(metric_name)
            display_name = metric_def.name[:33]  # Truncate for display

            # Format values
            formatted_values = [f"{v:.2f}%" for v in values]

            print(
                f"{display_name:<35} {formatted_values[0]:<10} {formatted_values[1]:<10} {formatted_values[2]:<10} {trend:<10}"
            )

        except Exception:
            print(f"{metric_name[:33]:<35} {'Error':<10} {'Error':<10} {'Error':<10} {'N/A':<10}")


def generate_executive_summary(graph: Graph) -> None:
    """Generate an executive summary of the banking analysis.

    Args:
        graph: The banking data graph.
    """
    print("\n" + "=" * 60)
    print("EXECUTIVE SUMMARY")
    print("=" * 60)

    data_nodes = {node.name: node for node in graph.nodes.values()}
    period = "2023"

    # Calculate key summary metrics
    try:
        npl_ratio = calculate_metric("non_performing_loan_ratio", data_nodes, period)
        tier1_ratio = calculate_metric("tier_1_capital_ratio", data_nodes, period)
        roa = calculate_metric("return_on_assets_(banking)", data_nodes, period)
        efficiency = calculate_metric("efficiency_ratio", data_nodes, period)
        nim = calculate_metric("net_interest_margin", data_nodes, period)
        lcr = calculate_metric("liquidity_coverage_ratio", data_nodes, period)

        print(f"Bank Performance Summary for {period}:")
        print(f"  • Asset Quality: NPL Ratio of {npl_ratio:.2f}%")
        print(f"  • Capital Strength: Tier 1 Ratio of {tier1_ratio:.2f}%")
        print(f"  • Profitability: ROA of {roa:.2f}%, NIM of {nim:.2f}%")
        print(f"  • Efficiency: Cost-to-Income of {efficiency:.2f}%")
        print(f"  • Liquidity: LCR of {lcr:.2f}%")

        # Overall assessment
        print("\nOverall Assessment:")
        if npl_ratio < 2.0 and tier1_ratio > 12.0 and roa > 1.0 and efficiency < 65.0:
            print("  🟢 Strong performance across key metrics")
        elif npl_ratio < 3.0 and tier1_ratio > 10.0 and roa > 0.8 and efficiency < 75.0:
            print("  🟡 Satisfactory performance with room for improvement")
        else:
            print("  🔴 Performance concerns requiring attention")

        # Key strengths and areas for improvement
        print("\nKey Observations:")

        strengths = []
        concerns = []

        if npl_ratio < 1.5:
            strengths.append("Excellent asset quality")
        elif npl_ratio > 3.0:
            concerns.append("Elevated credit risk")

        if tier1_ratio > 13.0:
            strengths.append("Strong capital position")
        elif tier1_ratio < 10.0:
            concerns.append("Capital adequacy concerns")

        if roa > 1.2:
            strengths.append("Strong profitability")
        elif roa < 0.8:
            concerns.append("Below-average profitability")

        if efficiency < 60.0:
            strengths.append("Excellent operational efficiency")
        elif efficiency > 70.0:
            concerns.append("High cost structure")

        if lcr > 120.0:
            strengths.append("Strong liquidity position")
        elif lcr < 105.0:
            concerns.append("Tight liquidity buffers")

        if strengths:
            print("  Strengths: " + ", ".join(strengths))
        if concerns:
            print("  Areas for attention: " + ", ".join(concerns))

    except Exception as e:
        print(f"Could not generate summary: {e}")


def generate_regulatory_compliance_summary(graph: Graph) -> None:
    """Generate regulatory compliance summary.

    Args:
        graph: The banking data graph.
    """
    print("\n" + "=" * 60)
    print("REGULATORY COMPLIANCE SUMMARY")
    print("=" * 60)

    data_nodes = {node.name: node for node in graph.nodes.values()}
    period = "2023"

    regulatory_metrics = [
        (
            "Common Equity Tier 1 Ratio",
            "common_equity_tier_1_ratio",
            7.0,
            "Regulatory minimum (with buffers)",
        ),
        (
            "Tier 1 Capital Ratio",
            "tier_1_capital_ratio",
            8.5,
            "Regulatory minimum (with buffers)",
        ),
        (
            "Liquidity Coverage Ratio",
            "liquidity_coverage_ratio",
            100.0,
            "Regulatory minimum",
        ),
        ("Tier 1 Leverage Ratio", "tier_1_leverage_ratio", 4.0, "Regulatory minimum"),
    ]

    print(f"{'Metric':<30} {'Current':<12} {'Minimum':<12} {'Status':<15}")
    print("-" * 70)

    for display_name, metric_name, minimum, description in regulatory_metrics:
        try:
            value = calculate_metric(metric_name, data_nodes, period)

            if value >= minimum * 1.2:  # 20% buffer above minimum
                status = "🟢 Strong"
            elif value >= minimum * 1.1:  # 10% buffer above minimum
                status = "🟡 Adequate"
            elif value >= minimum:
                status = "🟡 Minimum"
            else:
                status = "🔴 Below Min"

            print(f"{display_name[:29]:<30} {value:.2f}%{'':<6} {minimum:.1f}%{'':<6} {status:<15}")

        except Exception:
            print(f"{display_name[:29]:<30} {'Error':<12} {minimum:.1f}%{'':<6} {'🔴 Unknown':<15}")

    print("\nNote: Actual regulatory minimums may vary by institution size,")
    print("      complexity, and additional buffer requirements.")


def main() -> None:
    """Run the realistic banking analysis example."""
    print("REALISTIC BANKING ANALYSIS")
    print("Demonstrating practical banking data analysis workflow")

    # Load and validate data in one step
    graph, validation_summary = load_and_validate_banking_data()

    # Perform comprehensive analysis
    analyze_banking_performance(graph)

    # Generate trend analysis
    generate_trend_analysis(graph)

    # Generate regulatory compliance summary
    generate_regulatory_compliance_summary(graph)

    # Generate executive summary
    generate_executive_summary(graph)

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    print("\nKey Benefits of This Approach:")
    print("✓ Single-step data loading with automatic validation")
    print("✓ Comprehensive metrics analysis with visual indicators")
    print("✓ Trend analysis across multiple periods")
    print("✓ Regulatory compliance monitoring")
    print("✓ Executive summary for stakeholder reporting")
    print("✓ Professional error handling and reporting")


if __name__ == "__main__":
    main()
