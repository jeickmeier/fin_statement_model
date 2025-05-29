"""Realistic Banking Analysis Example.

This example demonstrates a realistic banking analysis workflow using the
financial statement model library. It includes:

1. Loading real-world banking data from multiple sources
2. Building a comprehensive banking financial model
3. Calculating key banking metrics and ratios
4. Performing regulatory capital analysis
5. Generating risk-adjusted performance metrics
6. Creating professional banking reports and visualizations

The example uses realistic data structures and calculations that mirror
actual banking analysis practices.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.metrics import (
    calculate_metric,
    interpret_metric,
    metric_registry,
)
from fin_statement_model.io.validation import UnifiedNodeValidator
from fin_statement_model.io import read_data, write_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_realistic_banking_data() -> dict[str, dict[str, float]]:
    """Create realistic banking financial data based on a mid-sized regional bank.

    Returns:
        Dictionary of financial data with node names as keys and period values as sub-dict
    """
    return {
        # Balance Sheet - Assets (in millions)
        "cash_and_due_from_banks": {
            "2021": 2_450.5,
            "2022": 2_875.3,
            "2023": 3_125.8,
        },
        "interest_bearing_deposits": {
            "2021": 1_250.0,
            "2022": 1_500.0,
            "2023": 1_750.0,
        },
        "federal_funds_sold": {
            "2021": 500.0,
            "2022": 450.0,
            "2023": 400.0,
        },
        "securities_available_for_sale": {
            "2021": 12_500.0,
            "2022": 13_250.0,
            "2023": 13_750.0,
        },
        "securities_held_to_maturity": {
            "2021": 5_000.0,
            "2022": 5_250.0,
            "2023": 5_500.0,
        },
        "gross_loans": {
            "2021": 48_750.0,
            "2022": 52_500.0,
            "2023": 56_250.0,
        },
        "commercial_loans": {
            "2021": 20_000.0,
            "2022": 21_500.0,
            "2023": 23_000.0,
        },
        "commercial_real_estate_loans": {
            "2021": 15_000.0,
            "2022": 16_250.0,
            "2023": 17_500.0,
        },
        "residential_mortgages": {
            "2021": 10_000.0,
            "2022": 10_750.0,
            "2023": 11_500.0,
        },
        "consumer_loans": {
            "2021": 3_750.0,
            "2022": 4_000.0,
            "2023": 4_250.0,
        },
        "allowance_for_loan_losses": {
            "2021": 731.25,  # 1.5% of gross loans
            "2022": 840.00,  # 1.6% of gross loans
            "2023": 956.25,  # 1.7% of gross loans
        },
        "premises_and_equipment": {
            "2021": 850.0,
            "2022": 900.0,
            "2023": 950.0,
        },
        "other_assets": {
            "2021": 2_150.0,
            "2022": 2_300.0,
            "2023": 2_450.0,
        },
        # Balance Sheet - Liabilities
        "non_interest_bearing_deposits": {
            "2021": 12_500.0,
            "2022": 13_750.0,
            "2023": 15_000.0,
        },
        "interest_bearing_deposits": {
            "2021": 45_000.0,
            "2022": 48_750.0,
            "2023": 52_500.0,
        },
        "demand_deposits": {
            "2021": 15_000.0,
            "2022": 16_500.0,
            "2023": 18_000.0,
        },
        "savings_deposits": {
            "2021": 20_000.0,
            "2022": 21_750.0,
            "2023": 23_500.0,
        },
        "time_deposits": {
            "2021": 10_000.0,
            "2022": 10_500.0,
            "2023": 11_000.0,
        },
        "federal_funds_purchased": {
            "2021": 1_000.0,
            "2022": 750.0,
            "2023": 500.0,
        },
        "short_term_borrowings": {
            "2021": 2_500.0,
            "2022": 2_250.0,
            "2023": 2_000.0,
        },
        "long_term_debt": {
            "2021": 5_000.0,
            "2022": 5_250.0,
            "2023": 5_500.0,
        },
        "other_liabilities": {
            "2021": 1_250.0,
            "2022": 1_375.0,
            "2023": 1_500.0,
        },
        # Balance Sheet - Equity
        "common_stock": {
            "2021": 500.0,
            "2022": 500.0,
            "2023": 500.0,
        },
        "additional_paid_in_capital": {
            "2021": 2_000.0,
            "2022": 2_000.0,
            "2023": 2_000.0,
        },
        "retained_earnings": {
            "2021": 4_268.75,
            "2022": 4_759.55,
            "2023": 5_318.33,
        },
        "accumulated_other_comprehensive_income": {
            "2021": -250.0,
            "2022": -300.0,
            "2023": -275.0,
        },
        # Income Statement (annual)
        "interest_income_loans": {
            "2021": 2_437.50,  # ~5% yield
            "2022": 2_887.50,  # ~5.5% yield
            "2023": 3_375.00,  # ~6% yield
        },
        "interest_income_securities": {
            "2021": 437.50,  # ~2.5% yield
            "2022": 472.50,  # ~2.5% yield
            "2023": 507.50,  # ~2.6% yield
        },
        "interest_income_other": {
            "2021": 50.0,
            "2022": 60.0,
            "2023": 70.0,
        },
        "interest_expense_deposits": {
            "2021": 450.00,  # ~1% cost
            "2022": 731.25,  # ~1.5% cost
            "2023": 1_050.00,  # ~2% cost
        },
        "interest_expense_borrowings": {
            "2021": 175.00,  # ~2% cost
            "2022": 200.00,  # ~2.5% cost
            "2023": 240.00,  # ~3% cost
        },
        "provision_for_credit_losses": {
            "2021": 250.0,
            "2022": 350.0,
            "2023": 450.0,
        },
        "non_interest_income": {
            "2021": 875.0,
            "2022": 950.0,
            "2023": 1_025.0,
        },
        "service_charges": {
            "2021": 350.0,
            "2022": 375.0,
            "2023": 400.0,
        },
        "trading_income": {
            "2021": 125.0,
            "2022": 150.0,
            "2023": 175.0,
        },
        "mortgage_banking_income": {
            "2021": 200.0,
            "2022": 225.0,
            "2023": 250.0,
        },
        "other_non_interest_income": {
            "2021": 200.0,
            "2022": 200.0,
            "2023": 200.0,
        },
        "non_interest_expense": {
            "2021": 1_750.0,
            "2022": 1_875.0,
            "2023": 2_000.0,
        },
        "salaries_and_benefits": {
            "2021": 1_050.0,
            "2022": 1_125.0,
            "2023": 1_200.0,
        },
        "occupancy_expense": {
            "2021": 175.0,
            "2022": 187.5,
            "2023": 200.0,
        },
        "technology_expense": {
            "2021": 262.5,
            "2022": 281.25,
            "2023": 300.0,
        },
        "other_operating_expense": {
            "2021": 262.5,
            "2022": 281.25,
            "2023": 300.0,
        },
        "income_tax_expense": {
            "2021": 225.0,
            "2022": 264.75,
            "2023": 317.5,
        },
        # Regulatory Capital Components
        "common_equity_tier_1": {
            "2021": 6_268.75,
            "2022": 6_709.55,
            "2023": 7_268.33,
        },
        "additional_tier_1_capital": {
            "2021": 500.0,
            "2022": 500.0,
            "2023": 500.0,
        },
        "tier_2_capital": {
            "2021": 731.25,
            "2022": 840.0,
            "2023": 956.25,
        },
        "total_risk_weighted_assets": {
            "2021": 52_500.0,
            "2022": 56_250.0,
            "2023": 60_000.0,
        },
        # Asset Quality Metrics
        "non_performing_loans": {
            "2021": 487.50,  # 1% of gross loans
            "2022": 577.50,  # 1.1% of gross loans
            "2023": 675.00,  # 1.2% of gross loans
        },
        "net_charge_offs": {
            "2021": 195.0,  # 0.4% of average loans
            "2022": 241.5,  # 0.46% of average loans
            "2023": 292.5,  # 0.52% of average loans
        },
        "loans_30_89_days_past_due": {
            "2021": 243.75,
            "2022": 262.50,
            "2023": 281.25,
        },
        "loans_90_plus_days_past_due": {
            "2021": 146.25,
            "2022": 157.50,
            "2023": 168.75,
        },
        # Liquidity Metrics
        "high_quality_liquid_assets": {
            "2021": 16_200.5,
            "2022": 18_075.3,
            "2023": 19_525.8,
        },
        "net_cash_outflows_30_days": {
            "2021": 13_500.0,
            "2022": 14_625.0,
            "2023": 15_750.0,
        },
        "available_stable_funding": {
            "2021": 58_750.0,
            "2022": 63_125.0,
            "2023": 67_500.0,
        },
        "required_stable_funding": {
            "2021": 48_958.33,
            "2022": 52_604.17,
            "2023": 56_250.0,
        },
        # Additional items for calculations
        "average_total_assets": {
            "2021": 71_250.0,
            "2022": 75_625.0,
            "2023": 80_000.0,
        },
        "average_earning_assets": {
            "2021": 65_000.0,
            "2022": 69_062.5,
            "2023": 73_125.0,
        },
        "average_total_loans": {
            "2021": 47_500.0,
            "2022": 50_625.0,
            "2023": 54_375.0,
        },
        "average_total_deposits": {
            "2021": 56_250.0,
            "2022": 60_625.0,
            "2023": 65_000.0,
        },
        "average_total_equity": {
            "2021": 6_393.75,
            "2022": 6_734.55,
            "2023": 7_271.58,
        },
    }


def validate_banking_data(
    raw_data: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    """Validate and standardize banking-specific node names.

    Args:
        raw_data: Dictionary with potentially non-standard node names

    Returns:
        Tuple of (standardized_data, validation_report)
    """
    print("\n" + "=" * 60)
    print("BANKING DATA VALIDATION AND STANDARDIZATION")
    print("=" * 60)

    # Create validator with banking-specific settings
    validator = UnifiedNodeValidator(
        strict_mode=False,
        auto_standardize=True,
        warn_on_non_standard=True,
        enable_patterns=True,
    )

    # Common banking abbreviations to test
    banking_abbreviations = {
        "npl": "non_performing_loans",
        "rwa": "total_risk_weighted_assets",
        "nii": "net_interest_income",
        "nim": "net_interest_margin",
        "cet1": "common_equity_tier_1",
        "lcr": "liquidity_coverage_ratio",
        "nsfr": "net_stable_funding_ratio",
        "all": "allowance_for_loan_losses",
    }

    print("Testing common banking abbreviations:")
    for abbrev, expected in banking_abbreviations.items():
        result = validator.validate(abbrev)
        print(f"  '{abbrev}' → '{result.standardized_name}' (expected: '{expected}')")

    # Validate all node names
    validation_results = validator.validate_batch(list(raw_data.keys()))

    # Create standardized data dictionary
    standardized_data = {}
    validation_report = {
        "total": len(raw_data),
        "valid": 0,
        "standardized": 0,
        "invalid": 0,
        "banking_specific": 0,
        "mappings": {},
    }

    print("\nValidation Results:")
    for original_name, result in validation_results.items():
        if result.is_valid:
            validation_report["valid"] += 1
            if original_name != result.standardized_name:
                validation_report["standardized"] += 1
                print(
                    f"  ✓ '{original_name}' → '{result.standardized_name}' (standardized)"
                )

            # Check if it's a banking-specific metric
            if any(
                term in original_name
                for term in ["loan", "deposit", "capital", "tier", "risk_weighted"]
            ):
                validation_report["banking_specific"] += 1

            standardized_data[result.standardized_name] = raw_data[original_name]
            validation_report["mappings"][original_name] = result.standardized_name
        else:
            validation_report["invalid"] += 1
            print(f"  ✗ '{original_name}' - {result.message}")

    # Print summary
    print("\nValidation Summary:")
    print(f"  Total nodes: {validation_report['total']}")
    print(f"  Valid: {validation_report['valid']}")
    print(f"  Banking-specific: {validation_report['banking_specific']}")
    print(f"  Standardized: {validation_report['standardized']}")
    print(f"  Invalid: {validation_report['invalid']}")

    return standardized_data, validation_report


def build_banking_graph(data: dict[str, dict[str, float]]) -> Graph:
    """Build a comprehensive banking financial graph.

    Args:
        data: Dictionary of financial data

    Returns:
        Graph object with all nodes and relationships
    """
    print("\n" + "=" * 60)
    print("BUILDING BANKING FINANCIAL GRAPH")
    print("=" * 60)

    # Create graph from data
    graph = read_data(format_type="dict", source=data)
    print(f"Created graph with {len(graph.nodes)} nodes")
    print(f"Time periods: {graph.periods}")

    # Categorize nodes
    node_categories = {
        "assets": [],
        "liabilities": [],
        "equity": [],
        "income": [],
        "expense": [],
        "regulatory": [],
        "quality": [],
        "liquidity": [],
    }

    for node_name in graph.nodes:
        if any(
            term in node_name for term in ["loan", "securities", "cash", "premises"]
        ):
            node_categories["assets"].append(node_name)
        elif any(term in node_name for term in ["deposit", "borrowing", "debt"]):
            node_categories["liabilities"].append(node_name)
        elif any(
            term in node_name for term in ["stock", "capital", "retained", "equity"]
        ):
            if "tier" in node_name or "risk_weighted" in node_name:
                node_categories["regulatory"].append(node_name)
            else:
                node_categories["equity"].append(node_name)
        elif "income" in node_name and "expense" not in node_name:
            node_categories["income"].append(node_name)
        elif "expense" in node_name:
            node_categories["expense"].append(node_name)
        elif any(
            term in node_name for term in ["non_performing", "charge_off", "past_due"]
        ):
            node_categories["quality"].append(node_name)
        elif any(term in node_name for term in ["liquid", "outflow", "funding"]):
            node_categories["liquidity"].append(node_name)

    print("\nNode Categories:")
    for category, nodes in node_categories.items():
        if nodes:
            print(f"  {category.capitalize()}: {len(nodes)} nodes")

    return graph


def calculate_banking_metrics(graph: Graph) -> dict[str, dict[str, Any]]:
    """Calculate comprehensive banking metrics for all periods.

    Args:
        graph: Banking financial graph

    Returns:
        Dictionary of metrics organized by category and period
    """
    print("\n" + "=" * 60)
    print("CALCULATING BANKING METRICS")
    print("=" * 60)

    metrics = {
        "capital_adequacy": {},
        "asset_quality": {},
        "management_efficiency": {},
        "earnings": {},
        "liquidity": {},
        "sensitivity": {},
    }

    # Get data nodes for metric calculation
    data_nodes = {node.name: node for node in graph.nodes.values()}

    # Define CAMELS metrics
    camels_metrics = {
        "capital_adequacy": [
            "common_equity_tier_1_ratio",
            "tier_1_capital_ratio",
            "total_capital_ratio",
            "tier_1_leverage_ratio",
        ],
        "asset_quality": [
            "non_performing_loan_ratio",
            "provision_coverage_ratio",
            "net_charge_off_rate",
            "allowance_to_loans_ratio",
        ],
        "management_efficiency": [
            "efficiency_ratio",
            "operating_expense_ratio",
            "cost_to_income_ratio",
        ],
        "earnings": [
            "return_on_assets_(banking)",
            "return_on_equity_(banking)",
            "net_interest_margin",
            "fee_income_ratio",
        ],
        "liquidity": [
            "liquidity_coverage_ratio",
            "net_stable_funding_ratio",
            "loan_to_deposit_ratio",
            "liquid_assets_ratio",
        ],
        "sensitivity": [
            "securities_to_assets_ratio",
            "interest_rate_sensitivity_ratio",
        ],
    }

    # Calculate metrics for each period
    for period in graph.periods:
        print(f"\nCalculating metrics for {period}:")

        for category, metric_list in camels_metrics.items():
            metrics[category][period] = {}

            for metric_name in metric_list:
                try:
                    value = calculate_metric(metric_name, data_nodes, period)
                    interpretation = interpret_metric(
                        metric_registry.get(metric_name), value
                    )

                    metrics[category][period][metric_name] = {
                        "value": value,
                        "interpretation": interpretation,
                    }

                    # Print key metrics
                    if metric_name in [
                        "common_equity_tier_1_ratio",
                        "non_performing_loan_ratio",
                        "return_on_equity_(banking)",
                        "net_interest_margin",
                        "liquidity_coverage_ratio",
                    ]:
                        print(
                            f"  {metric_name}: {value:.2f}% - {interpretation['rating']}"
                        )

                except Exception as e:
                    logger.warning(
                        f"Could not calculate {metric_name} for {period}: {e}"
                    )

    return metrics


def perform_stress_testing(
    graph: Graph, metrics: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Perform basic stress testing on the bank's financial position.

    Args:
        graph: Banking financial graph
        metrics: Calculated banking metrics

    Returns:
        Dictionary containing stress test results
    """
    print("\n" + "=" * 60)
    print("STRESS TESTING ANALYSIS")
    print("=" * 60)

    latest_period = graph.periods[-1]
    data_nodes = {node.name: node for node in graph.nodes.values()}

    stress_results = {
        "baseline": {},
        "adverse": {},
        "severely_adverse": {},
    }

    # Define stress scenarios
    scenarios = {
        "baseline": {
            "loan_loss_rate": 0.01,  # 1% loss rate
            "deposit_runoff": 0.05,  # 5% deposit runoff
            "securities_loss": 0.02,  # 2% securities loss
        },
        "adverse": {
            "loan_loss_rate": 0.03,  # 3% loss rate
            "deposit_runoff": 0.15,  # 15% deposit runoff
            "securities_loss": 0.05,  # 5% securities loss
        },
        "severely_adverse": {
            "loan_loss_rate": 0.05,  # 5% loss rate
            "deposit_runoff": 0.25,  # 25% deposit runoff
            "securities_loss": 0.10,  # 10% securities loss
        },
    }

    print("Stress Test Scenarios:")

    for scenario_name, scenario_params in scenarios.items():
        print(f"\n{scenario_name.upper()} Scenario:")

        # Get baseline values
        if all(
            node in data_nodes
            for node in [
                "gross_loans",
                "total_deposits",
                "securities_available_for_sale",
            ]
        ):
            gross_loans = data_nodes["gross_loans"].get_value(latest_period)
            total_deposits = data_nodes["total_deposits"].get_value(latest_period)
            securities = data_nodes["securities_available_for_sale"].get_value(
                latest_period
            )

            # Calculate stressed values
            loan_losses = gross_loans * scenario_params["loan_loss_rate"]
            deposit_outflows = total_deposits * scenario_params["deposit_runoff"]
            securities_losses = securities * scenario_params["securities_loss"]

            total_losses = loan_losses + securities_losses

            # Calculate impact on capital
            if "common_equity_tier_1" in data_nodes:
                cet1_capital = data_nodes["common_equity_tier_1"].get_value(
                    latest_period
                )
                stressed_cet1 = cet1_capital - total_losses

                if "total_risk_weighted_assets" in data_nodes:
                    rwa = data_nodes["total_risk_weighted_assets"].get_value(
                        latest_period
                    )
                    stressed_cet1_ratio = (stressed_cet1 / rwa) * 100

                    stress_results[scenario_name] = {
                        "loan_losses": loan_losses,
                        "securities_losses": securities_losses,
                        "total_losses": total_losses,
                        "deposit_outflows": deposit_outflows,
                        "stressed_cet1_capital": stressed_cet1,
                        "stressed_cet1_ratio": stressed_cet1_ratio,
                        "capital_buffer": stressed_cet1_ratio
                        - 4.5,  # Minimum CET1 requirement
                    }

                    print(f"  Loan Losses: ${loan_losses:,.1f}M")
                    print(f"  Securities Losses: ${securities_losses:,.1f}M")
                    print(f"  Total Losses: ${total_losses:,.1f}M")
                    print(f"  Deposit Outflows: ${deposit_outflows:,.1f}M")
                    print(f"  Stressed CET1 Ratio: {stressed_cet1_ratio:.2f}%")
                    print(f"  Capital Buffer: {stressed_cet1_ratio - 4.5:.2f}%")

                    if stressed_cet1_ratio < 4.5:
                        print("  ⚠️  WARNING: Below minimum regulatory requirement!")
                    elif stressed_cet1_ratio < 7.0:
                        print("  ⚠️  WARNING: Below well-capitalized threshold!")

    return stress_results


def create_banking_visualizations(
    graph: Graph,
    metrics: dict[str, dict[str, Any]],
    stress_results: dict[str, Any],
    output_dir: Path,
) -> None:
    """Create professional banking analysis visualizations.

    Args:
        graph: Banking financial graph
        metrics: Calculated banking metrics
        stress_results: Stress testing results
        output_dir: Directory to save visualizations
    """
    print("\n" + "=" * 60)
    print("CREATING BANKING VISUALIZATIONS")
    print("=" * 60)

    output_dir.mkdir(exist_ok=True)

    # 1. CAMELS Rating Dashboard
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle("CAMELS Rating Dashboard", fontsize=16, fontweight="bold")

    camels_components = [
        ("Capital Adequacy", "capital_adequacy", axes[0, 0]),
        ("Asset Quality", "asset_quality", axes[0, 1]),
        ("Management", "management_efficiency", axes[0, 2]),
        ("Earnings", "earnings", axes[1, 0]),
        ("Liquidity", "liquidity", axes[1, 1]),
        ("Sensitivity", "sensitivity", axes[1, 2]),
    ]

    periods = graph.periods

    for title, category, ax in camels_components:
        if category in metrics and periods[-1] in metrics[category]:
            # Get a key metric for each category
            key_metrics = {
                "capital_adequacy": "common_equity_tier_1_ratio",
                "asset_quality": "non_performing_loan_ratio",
                "management_efficiency": "efficiency_ratio",
                "earnings": "return_on_equity_(banking)",
                "liquidity": "liquidity_coverage_ratio",
                "sensitivity": "securities_to_assets_ratio",
            }

            metric_name = key_metrics.get(category)
            if metric_name:
                values = []
                for period in periods:
                    if (
                        period in metrics[category]
                        and metric_name in metrics[category][period]
                    ):
                        values.append(metrics[category][period][metric_name]["value"])
                    else:
                        values.append(None)

                # Filter out None values
                valid_periods = [p for p, v in zip(periods, values) if v is not None]
                valid_values = [v for v in values if v is not None]

                if valid_values:
                    ax.plot(
                        valid_periods,
                        valid_values,
                        marker="o",
                        linewidth=2,
                        markersize=8,
                    )
                    ax.set_title(title, fontweight="bold")
                    ax.set_ylabel(f"{metric_name.replace('_', ' ').title()} (%)")
                    ax.grid(True, alpha=0.3)

                    # Add rating zones
                    if "ratio" in metric_name:
                        if "capital" in metric_name:
                            ax.axhline(
                                y=10.5,
                                color="green",
                                linestyle="--",
                                alpha=0.5,
                                label="Well Capitalized",
                            )
                            ax.axhline(
                                y=8.0,
                                color="orange",
                                linestyle="--",
                                alpha=0.5,
                                label="Adequately Capitalized",
                            )
                            ax.axhline(
                                y=6.0,
                                color="red",
                                linestyle="--",
                                alpha=0.5,
                                label="Undercapitalized",
                            )

    plt.tight_layout()
    plt.savefig(output_dir / "camels_dashboard.png", dpi=300, bbox_inches="tight")
    plt.close()
    print("  ✓ Created CAMELS rating dashboard")

    # 2. Stress Test Results
    if stress_results:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
        fig.suptitle("Stress Test Results", fontsize=14, fontweight="bold")

        scenarios = list(stress_results.keys())
        cet1_ratios = [
            stress_results[s].get("stressed_cet1_ratio", 0) for s in scenarios
        ]
        total_losses = [stress_results[s].get("total_losses", 0) for s in scenarios]

        # CET1 Ratio under stress
        colors = ["green", "orange", "red"]
        bars1 = ax1.bar(scenarios, cet1_ratios, color=colors, alpha=0.7)
        ax1.axhline(y=4.5, color="red", linestyle="--", label="Minimum Requirement")
        ax1.axhline(y=7.0, color="orange", linestyle="--", label="Well Capitalized")
        ax1.set_ylabel("CET1 Ratio (%)")
        ax1.set_title("Capital Ratios Under Stress")
        ax1.legend()
        ax1.set_ylim(0, max(cet1_ratios) * 1.2)

        # Add value labels on bars
        for bar, value in zip(bars1, cet1_ratios):
            height = bar.get_height()
            ax1.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{value:.1f}%",
                ha="center",
                va="bottom",
            )

        # Total losses
        bars2 = ax2.bar(scenarios, total_losses, color=colors, alpha=0.7)
        ax2.set_ylabel("Total Losses ($M)")
        ax2.set_title("Projected Losses by Scenario")
        ax2.set_ylim(0, max(total_losses) * 1.2)

        # Add value labels
        for bar, value in zip(bars2, total_losses):
            height = bar.get_height()
            ax2.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"${value:,.0f}M",
                ha="center",
                va="bottom",
            )

        plt.tight_layout()
        plt.savefig(
            output_dir / "stress_test_results.png", dpi=300, bbox_inches="tight"
        )
        plt.close()
        print("  ✓ Created stress test visualization")

    # 3. Trend Analysis
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Banking Performance Trends", fontsize=14, fontweight="bold")

    # Asset growth
    if "total_assets" in graph.nodes:
        asset_node = graph.get_node("average_total_assets")
        if asset_node:
            assets = [asset_node.get_value(p) / 1000 for p in periods]  # In billions
            ax1.plot(
                periods, assets, marker="o", linewidth=2, markersize=8, color="blue"
            )
            ax1.set_title("Total Assets Growth")
            ax1.set_ylabel("Assets ($B)")
            ax1.grid(True, alpha=0.3)

    # Net Interest Margin trend
    nim_values = []
    for period in periods:
        if "earnings" in metrics and period in metrics["earnings"]:
            if "net_interest_margin" in metrics["earnings"][period]:
                nim_values.append(
                    metrics["earnings"][period]["net_interest_margin"]["value"]
                )

    if nim_values:
        ax2.plot(
            periods[: len(nim_values)],
            nim_values,
            marker="o",
            linewidth=2,
            markersize=8,
            color="green",
        )
        ax2.set_title("Net Interest Margin Trend")
        ax2.set_ylabel("NIM (%)")
        ax2.grid(True, alpha=0.3)

    # Asset Quality trend
    npl_values = []
    for period in periods:
        if "asset_quality" in metrics and period in metrics["asset_quality"]:
            if "non_performing_loan_ratio" in metrics["asset_quality"][period]:
                npl_values.append(
                    metrics["asset_quality"][period]["non_performing_loan_ratio"][
                        "value"
                    ]
                )

    if npl_values:
        ax3.plot(
            periods[: len(npl_values)],
            npl_values,
            marker="o",
            linewidth=2,
            markersize=8,
            color="red",
        )
        ax3.set_title("Non-Performing Loans Trend")
        ax3.set_ylabel("NPL Ratio (%)")
        ax3.grid(True, alpha=0.3)
        ax3.invert_yaxis()  # Lower is better

    # Efficiency Ratio trend
    eff_values = []
    for period in periods:
        if (
            "management_efficiency" in metrics
            and period in metrics["management_efficiency"]
        ):
            if "efficiency_ratio" in metrics["management_efficiency"][period]:
                eff_values.append(
                    metrics["management_efficiency"][period]["efficiency_ratio"][
                        "value"
                    ]
                )

    if eff_values:
        ax4.plot(
            periods[: len(eff_values)],
            eff_values,
            marker="o",
            linewidth=2,
            markersize=8,
            color="orange",
        )
        ax4.set_title("Efficiency Ratio Trend")
        ax4.set_ylabel("Efficiency Ratio (%)")
        ax4.grid(True, alpha=0.3)
        ax4.invert_yaxis()  # Lower is better

    plt.tight_layout()
    plt.savefig(output_dir / "performance_trends.png", dpi=300, bbox_inches="tight")
    plt.close()
    print("  ✓ Created performance trends visualization")


def generate_banking_report(
    graph: Graph,
    metrics: dict[str, dict[str, Any]],
    stress_results: dict[str, Any],
    validation_report: dict[str, Any],
    output_dir: Path,
) -> None:
    """Generate a comprehensive banking analysis report.

    Args:
        graph: Banking financial graph
        metrics: Calculated banking metrics
        stress_results: Stress testing results
        validation_report: Data validation report
        output_dir: Directory to save report
    """
    print("\n" + "=" * 60)
    print("GENERATING BANKING ANALYSIS REPORT")
    print("=" * 60)

    output_dir.mkdir(exist_ok=True)

    # Create markdown report
    report_path = output_dir / "banking_analysis_report.md"

    with open(report_path, "w") as f:
        f.write("# Banking Financial Analysis Report\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Executive Summary
        f.write("## Executive Summary\n\n")

        latest_period = graph.periods[-1]

        # Key metrics summary
        if (
            "capital_adequacy" in metrics
            and latest_period in metrics["capital_adequacy"]
        ):
            if (
                "common_equity_tier_1_ratio"
                in metrics["capital_adequacy"][latest_period]
            ):
                cet1 = metrics["capital_adequacy"][latest_period][
                    "common_equity_tier_1_ratio"
                ]
                f.write(
                    f"- **CET1 Ratio**: {cet1['value']:.2f}% ({cet1['interpretation']['rating']})\n"
                )

        if "asset_quality" in metrics and latest_period in metrics["asset_quality"]:
            if "non_performing_loan_ratio" in metrics["asset_quality"][latest_period]:
                npl = metrics["asset_quality"][latest_period][
                    "non_performing_loan_ratio"
                ]
                f.write(
                    f"- **NPL Ratio**: {npl['value']:.2f}% ({npl['interpretation']['rating']})\n"
                )

        if "earnings" in metrics and latest_period in metrics["earnings"]:
            if "return_on_equity_(banking)" in metrics["earnings"][latest_period]:
                roe = metrics["earnings"][latest_period]["return_on_equity_(banking)"]
                f.write(
                    f"- **ROE**: {roe['value']:.2f}% ({roe['interpretation']['rating']})\n"
                )

            if "net_interest_margin" in metrics["earnings"][latest_period]:
                nim = metrics["earnings"][latest_period]["net_interest_margin"]
                f.write(
                    f"- **Net Interest Margin**: {nim['value']:.2f}% ({nim['interpretation']['rating']})\n"
                )

        if "liquidity" in metrics and latest_period in metrics["liquidity"]:
            if "liquidity_coverage_ratio" in metrics["liquidity"][latest_period]:
                lcr = metrics["liquidity"][latest_period]["liquidity_coverage_ratio"]
                f.write(
                    f"- **LCR**: {lcr['value']:.2f}% ({lcr['interpretation']['rating']})\n"
                )

        # CAMELS Assessment
        f.write("\n## CAMELS Assessment\n\n")

        camels_categories = [
            ("Capital Adequacy", "capital_adequacy"),
            ("Asset Quality", "asset_quality"),
            ("Management", "management_efficiency"),
            ("Earnings", "earnings"),
            ("Liquidity", "liquidity"),
            ("Sensitivity", "sensitivity"),
        ]

        for category_name, category_key in camels_categories:
            f.write(f"\n### {category_name}\n\n")

            if category_key in metrics and latest_period in metrics[category_key]:
                f.write("| Metric | Value | Rating | Interpretation |\n")
                f.write("|--------|-------|--------|----------------|\n")

                for metric_name, metric_data in metrics[category_key][
                    latest_period
                ].items():
                    if "value" in metric_data and "interpretation" in metric_data:
                        value = metric_data["value"]
                        rating = metric_data["interpretation"]["rating"]
                        message = metric_data["interpretation"][
                            "interpretation_message"
                        ]

                        # Truncate long messages
                        if len(message) > 50:
                            message = message[:47] + "..."

                        metric_display = metric_name.replace("_", " ").title()
                        f.write(
                            f"| {metric_display} | {value:.2f}% | {rating} | {message} |\n"
                        )

        # Stress Testing Results
        f.write("\n## Stress Testing Results\n\n")

        if stress_results:
            f.write(
                "| Scenario | Total Losses | Stressed CET1 Ratio | Capital Buffer | Status |\n"
            )
            f.write(
                "|----------|--------------|---------------------|----------------|--------|\n"
            )

            for scenario_name, results in stress_results.items():
                if "total_losses" in results:
                    losses = results["total_losses"]
                    cet1_ratio = results.get("stressed_cet1_ratio", 0)
                    buffer = results.get("capital_buffer", 0)

                    status = (
                        "✅ Pass"
                        if cet1_ratio >= 7.0
                        else "⚠️ Watch" if cet1_ratio >= 4.5 else "❌ Fail"
                    )

                    f.write(
                        f"| {scenario_name.title()} | ${losses:,.0f}M | {cet1_ratio:.2f}% | {buffer:.2f}% | {status} |\n"
                    )

        # Risk Assessment
        f.write("\n## Risk Assessment\n\n")

        # Credit Risk
        f.write("### Credit Risk\n")
        if "asset_quality" in metrics and latest_period in metrics["asset_quality"]:
            npl_data = metrics["asset_quality"][latest_period].get(
                "non_performing_loan_ratio", {}
            )
            if npl_data:
                npl_value = npl_data.get("value", 0)
                if npl_value < 1.0:
                    f.write("- **Low Credit Risk**: NPL ratio below 1%\n")
                elif npl_value < 2.0:
                    f.write("- **Moderate Credit Risk**: NPL ratio between 1-2%\n")
                else:
                    f.write("- **Elevated Credit Risk**: NPL ratio above 2%\n")

        # Interest Rate Risk
        f.write("\n### Interest Rate Risk\n")
        data_nodes = {node.name: node for node in graph.nodes.values()}
        if all(
            node in data_nodes
            for node in ["interest_income_loans", "average_earning_assets"]
        ):
            int_income = data_nodes["interest_income_loans"].get_value(latest_period)
            avg_assets = data_nodes["average_earning_assets"].get_value(latest_period)
            asset_yield = (int_income / avg_assets) * 100 if avg_assets > 0 else 0
            f.write(f"- **Asset Yield**: {asset_yield:.2f}%\n")
            f.write("- **Rate Sensitivity**: Monitor for rising rate environment\n")

        # Liquidity Risk
        f.write("\n### Liquidity Risk\n")
        if "liquidity" in metrics and latest_period in metrics["liquidity"]:
            lcr_data = metrics["liquidity"][latest_period].get(
                "liquidity_coverage_ratio", {}
            )
            if lcr_data and "value" in lcr_data:
                lcr_value = lcr_data["value"]
                if lcr_value >= 100:
                    f.write("- **Low Liquidity Risk**: LCR above regulatory minimum\n")
                else:
                    f.write("- **Elevated Liquidity Risk**: LCR below 100%\n")

        # Data Quality
        f.write("\n## Data Quality Assessment\n\n")
        f.write(f"- **Total Nodes Validated**: {validation_report['total']}\n")
        f.write(
            f"- **Banking-Specific Nodes**: {validation_report['banking_specific']}\n"
        )
        f.write(
            f"- **Data Completeness**: {(validation_report['valid'] / validation_report['total'] * 100):.1f}%\n"
        )

        # Recommendations
        f.write("\n## Recommendations\n\n")

        recommendations = []

        # Check capital adequacy
        if (
            "capital_adequacy" in metrics
            and latest_period in metrics["capital_adequacy"]
        ):
            cet1_data = metrics["capital_adequacy"][latest_period].get(
                "common_equity_tier_1_ratio", {}
            )
            if cet1_data and "value" in cet1_data:
                if cet1_data["value"] < 9.0:
                    recommendations.append(
                        "Consider building additional capital buffers"
                    )

        # Check asset quality
        if "asset_quality" in metrics and latest_period in metrics["asset_quality"]:
            npl_data = metrics["asset_quality"][latest_period].get(
                "non_performing_loan_ratio", {}
            )
            if npl_data and "value" in npl_data:
                if npl_data["value"] > 2.0:
                    recommendations.append(
                        "Enhance credit underwriting and monitoring processes"
                    )

        # Check efficiency
        if (
            "management_efficiency" in metrics
            and latest_period in metrics["management_efficiency"]
        ):
            eff_data = metrics["management_efficiency"][latest_period].get(
                "efficiency_ratio", {}
            )
            if eff_data and "value" in eff_data:
                if eff_data["value"] > 60.0:
                    recommendations.append(
                        "Focus on operational efficiency improvements"
                    )

        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                f.write(f"{i}. {rec}\n")
        else:
            f.write("The bank appears to be well-positioned across all key metrics.\n")

        f.write("\n---\n")
        f.write(
            "*This report was generated using the Financial Statement Model library*\n"
        )

    print(f"  ✓ Created banking analysis report: {report_path}")

    # Export to Excel
    excel_path = output_dir / "banking_financial_data.xlsx"
    write_data(
        graph=graph,
        format_type="excel",
        output_path=str(excel_path),
        include_metadata=True,
    )
    print(f"  ✓ Exported data to Excel: {excel_path}")


def main():
    """Run the realistic banking analysis example."""
    print("=" * 60)
    print("REALISTIC BANKING ANALYSIS EXAMPLE")
    print("=" * 60)
    print("Demonstrating comprehensive banking analysis using the")
    print("Financial Statement Model library with realistic data")

    # Create output directory
    output_dir = Path("examples/output/banking_analysis")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Create and validate banking data
    raw_data = create_realistic_banking_data()
    standardized_data, validation_report = validate_banking_data(raw_data)

    # Step 2: Build banking financial graph
    graph = build_banking_graph(standardized_data)

    # Step 3: Calculate comprehensive banking metrics
    metrics = calculate_banking_metrics(graph)

    # Step 4: Perform stress testing
    stress_results = perform_stress_testing(graph, metrics)

    # Step 5: Create visualizations
    create_banking_visualizations(graph, metrics, stress_results, output_dir)

    # Step 6: Generate comprehensive report
    generate_banking_report(
        graph, metrics, stress_results, validation_report, output_dir
    )

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"\nResults saved to: {output_dir}")
    print("\nKey Features Demonstrated:")
    print("1. Banking-specific data validation and standardization")
    print("2. Comprehensive CAMELS framework analysis")
    print("3. Regulatory capital calculations (Basel III)")
    print("4. Stress testing with multiple scenarios")
    print("5. Professional visualizations and reporting")
    print("6. Risk assessment across multiple dimensions")
    print("\nThis example shows how the Financial Statement Model library")
    print("can be used for sophisticated banking analysis and regulatory reporting.")


if __name__ == "__main__":
    main()
