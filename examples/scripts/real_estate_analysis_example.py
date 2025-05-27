"""Real Estate Analysis Example.

This example demonstrates how to use the real estate-specific metrics
and nodes in the financial statement model library for REIT analysis.
"""

from fin_statement_model.core.metrics import metric_registry, interpret_metric, calculate_metric
from fin_statement_model.core.nodes import FinancialStatementItemNode


def create_sample_reit_data() -> dict[str, FinancialStatementItemNode]:
    """Create sample REIT financial data for analysis."""
    # Property operations data
    rental_income = FinancialStatementItemNode(
        "rental_income", {"2021": 95_000_000, "2022": 102_000_000, "2023": 108_000_000}
    )

    other_property_income = FinancialStatementItemNode(
        "other_property_income",
        {"2021": 5_000_000, "2022": 5_500_000, "2023": 6_000_000},
    )

    property_operating_expenses = FinancialStatementItemNode(
        "property_operating_expenses",
        {"2021": 40_000_000, "2022": 42_000_000, "2023": 44_000_000},
    )

    # REIT-specific data
    net_income = FinancialStatementItemNode(
        "net_income", {"2021": 45_000_000, "2022": 48_000_000, "2023": 52_000_000}
    )

    depreciation_and_amortization = FinancialStatementItemNode(
        "depreciation_and_amortization",
        {"2021": 25_000_000, "2022": 26_000_000, "2023": 27_000_000},
    )

    gains_on_property_sales = FinancialStatementItemNode(
        "gains_on_property_sales",
        {"2021": 2_000_000, "2022": 3_000_000, "2023": 1_500_000},
    )

    # Property metrics
    occupied_square_feet = FinancialStatementItemNode(
        "occupied_square_feet",
        {"2021": 4_500_000, "2022": 4_750_000, "2023": 4_900_000},
    )

    total_rentable_square_feet = FinancialStatementItemNode(
        "total_rentable_square_feet",
        {"2021": 5_000_000, "2022": 5_000_000, "2023": 5_200_000},
    )

    # Market data
    shares_outstanding = FinancialStatementItemNode(
        "shares_outstanding",
        {"2021": 100_000_000, "2022": 102_000_000, "2023": 104_000_000},
    )

    market_cap = FinancialStatementItemNode(
        "market_cap",
        {"2021": 2_500_000_000, "2022": 2_800_000_000, "2023": 3_100_000_000},
    )

    property_value = FinancialStatementItemNode(
        "property_value",
        {"2021": 1_800_000_000, "2022": 1_950_000_000, "2023": 2_100_000_000},
    )

    return {
        "rental_income": rental_income,
        "other_property_income": other_property_income,
        "property_operating_expenses": property_operating_expenses,
        "net_income": net_income,
        "depreciation_and_amortization": depreciation_and_amortization,
        "gains_on_property_sales": gains_on_property_sales,
        "occupied_square_feet": occupied_square_feet,
        "total_rentable_square_feet": total_rentable_square_feet,
        "shares_outstanding": shares_outstanding,
        "market_cap": market_cap,
        "property_value": property_value,
    }


def calculate_reit_metrics(
    data_nodes: dict[str, FinancialStatementItemNode], period: str = "2023"
) -> dict[str, float]:
    """Calculate key REIT metrics for analysis."""
    results = {}

    # Calculate Net Operating Income first (needed for cap rate)
    results["noi"] = calculate_metric("net_operating_income", data_nodes, period)

    # Calculate Funds From Operations (needed for FFO per share and multiple)
    results["ffo"] = calculate_metric("funds_from_operations", data_nodes, period)

    # Calculate Occupancy Rate
    results["occupancy_rate"] = calculate_metric("occupancy_rate", data_nodes, period)

    # For metrics that depend on calculated values, we need to add them to data_nodes
    # Create temporary nodes for calculated values
    from fin_statement_model.core.nodes import FinancialStatementItemNode

    # Add calculated NOI and FFO to data_nodes for dependent calculations
    extended_data_nodes = data_nodes.copy()
    extended_data_nodes["net_operating_income"] = FinancialStatementItemNode(
        "net_operating_income", {period: results["noi"]}
    )
    extended_data_nodes["funds_from_operations"] = FinancialStatementItemNode(
        "funds_from_operations", {period: results["ffo"]}
    )

    # Calculate metrics that depend on calculated values
    results["cap_rate"] = calculate_metric("capitalization_rate", extended_data_nodes, period)
    results["ffo_per_share"] = calculate_metric("ffo_per_share", extended_data_nodes, period)
    results["ffo_multiple"] = calculate_metric("ffo_multiple", extended_data_nodes, period)

    return results


def analyze_reit_performance() -> None:
    """Perform comprehensive REIT analysis."""
    print("=== REIT Analysis Example ===\n")

    # Create sample data
    data_nodes = create_sample_reit_data()

    # Calculate metrics for 2023
    metrics_2023 = calculate_reit_metrics(data_nodes, "2023")

    print("Key REIT Metrics for 2023:")
    print("-" * 40)

    # Display results with interpretations
    metric_names = [
        ("noi", "Net Operating Income"),
        ("ffo", "Funds From Operations"),
        ("occupancy_rate", "Occupancy Rate"),
        ("cap_rate", "Capitalization Rate"),
        ("ffo_per_share", "FFO Per Share"),
        ("ffo_multiple", "FFO Multiple"),
    ]

    for metric_key, display_name in metric_names:
        value = metrics_2023[metric_key]

        # Get interpretation if available
        try:
            if metric_key in ["noi", "ffo"]:
                # These are dollar amounts
                print(f"{display_name}: ${value:,.0f}")
            elif metric_key in ["occupancy_rate", "cap_rate"]:
                # These are percentages
                metric_def = metric_registry.get(metric_key)
                interpretation = interpret_metric(metric_def, value)
                print(f"{display_name}: {value:.1f}%")
                print(f"  → {interpretation['interpretation_message']}")
            elif metric_key == "ffo_per_share":
                # This is per share
                print(f"{display_name}: ${value:.2f}")
            elif metric_key == "ffo_multiple":
                # This is a multiple
                metric_def = metric_registry.get(metric_key)
                interpretation = interpret_metric(metric_def, value)
                print(f"{display_name}: {value:.1f}x")
                print(f"  → {interpretation['interpretation_message']}")
        except Exception:
            print(f"{display_name}: {value:.2f}")

        print()

    # Calculate growth rates
    print("Growth Analysis:")
    print("-" * 40)

    # NOI growth 2022 to 2023
    noi_2022 = calculate_reit_metrics(data_nodes, "2022")["noi"]
    noi_2023 = metrics_2023["noi"]
    noi_growth = ((noi_2023 - noi_2022) / noi_2022) * 100
    print(f"NOI Growth (2022-2023): {noi_growth:.1f}%")

    # FFO growth 2022 to 2023
    ffo_2022 = calculate_reit_metrics(data_nodes, "2022")["ffo"]
    ffo_2023 = metrics_2023["ffo"]
    ffo_growth = ((ffo_2023 - ffo_2022) / ffo_2022) * 100
    print(f"FFO Growth (2022-2023): {ffo_growth:.1f}%")

    print("\n=== Analysis Complete ===")


if __name__ == "__main__":
    analyze_reit_performance()
