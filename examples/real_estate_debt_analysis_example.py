"""Real Estate Debt Analysis Example.

This example demonstrates how to use the real estate debt-specific metrics
and nodes in the financial statement model library for comprehensive debt
analysis of real estate investments and REITs.
"""

from fin_statement_model.core.metrics import metric_registry, interpret_metric, calculate_metric
from fin_statement_model.core.nodes import FinancialStatementItemNode


def create_sample_reit_debt_data() -> dict[str, FinancialStatementItemNode]:
    """Create sample REIT debt and financing data for analysis."""
    # Property Portfolio Data
    total_property_value = FinancialStatementItemNode(
        "total_property_value",
        {"2021": 2_800_000_000, "2022": 3_200_000_000, "2023": 3_500_000_000},
    )

    net_operating_income = FinancialStatementItemNode(
        "net_operating_income",
        {"2021": 180_000_000, "2022": 195_000_000, "2023": 210_000_000},
    )

    # Debt Portfolio Data
    total_debt = FinancialStatementItemNode(
        "total_debt",
        {
            "2021": 1_680_000_000,  # 60% LTV
            "2022": 1_920_000_000,  # 60% LTV
            "2023": 2_100_000_000,  # 60% LTV
        },
    )

    mortgage_debt = FinancialStatementItemNode(
        "mortgage_debt",
        {"2021": 1_400_000_000, "2022": 1_600_000_000, "2023": 1_750_000_000},
    )

    construction_loans = FinancialStatementItemNode(
        "construction_loans",
        {"2021": 150_000_000, "2022": 200_000_000, "2023": 250_000_000},
    )

    bridge_loans = FinancialStatementItemNode(
        "bridge_loans", {"2021": 80_000_000, "2022": 70_000_000, "2023": 50_000_000}
    )

    mezzanine_debt = FinancialStatementItemNode(
        "mezzanine_debt", {"2021": 50_000_000, "2022": 50_000_000, "2023": 50_000_000}
    )

    # Debt Service and Payments
    mortgage_payments = FinancialStatementItemNode(
        "mortgage_payments",
        {"2021": 120_000_000, "2022": 135_000_000, "2023": 150_000_000},
    )

    interest_payments = FinancialStatementItemNode(
        "interest_payments",
        {
            "2021": 84_000_000,  # 5.0% weighted average rate
            "2022": 96_000_000,  # 5.0% weighted average rate
            "2023": 115_500_000,  # 5.5% weighted average rate
        },
    )

    principal_payments = FinancialStatementItemNode(
        "principal_payments",
        {"2021": 36_000_000, "2022": 39_000_000, "2023": 34_500_000},
    )

    # Debt Composition
    fixed_rate_debt = FinancialStatementItemNode(
        "fixed_rate_debt",
        {
            "2021": 1_344_000_000,  # 80% fixed
            "2022": 1_536_000_000,  # 80% fixed
            "2023": 1_575_000_000,  # 75% fixed
        },
    )

    variable_rate_debt = FinancialStatementItemNode(
        "variable_rate_debt",
        {
            "2021": 336_000_000,  # 20% variable
            "2022": 384_000_000,  # 20% variable
            "2023": 525_000_000,  # 25% variable
        },
    )

    # Unencumbered Assets
    unencumbered_assets = FinancialStatementItemNode(
        "unencumbered_assets",
        {
            "2021": 840_000_000,  # 30% unencumbered
            "2022": 960_000_000,  # 30% unencumbered
            "2023": 1_050_000_000,  # 30% unencumbered
        },
    )

    # Debt Maturities
    debt_maturities_1_year = FinancialStatementItemNode(
        "debt_maturities_1_year",
        {
            "2021": 168_000_000,  # 10% maturing in 1 year
            "2022": 192_000_000,  # 10% maturing in 1 year
            "2023": 315_000_000,  # 15% maturing in 1 year
        },
    )

    debt_maturities_2_to_5_years = FinancialStatementItemNode(
        "debt_maturities_2_to_5_years",
        {
            "2021": 672_000_000,  # 40% maturing in 2-5 years
            "2022": 768_000_000,  # 40% maturing in 2-5 years
            "2023": 840_000_000,  # 40% maturing in 2-5 years
        },
    )

    # Development Projects
    development_costs_to_date = FinancialStatementItemNode(
        "development_costs_to_date",
        {"2021": 120_000_000, "2022": 180_000_000, "2023": 250_000_000},
    )

    remaining_development_budget = FinancialStatementItemNode(
        "remaining_development_budget",
        {"2021": 80_000_000, "2022": 120_000_000, "2023": 100_000_000},
    )

    # Credit Facilities
    available_credit = FinancialStatementItemNode(
        "available_credit",
        {"2021": 200_000_000, "2022": 150_000_000, "2023": 100_000_000},
    )

    credit_facility_total = FinancialStatementItemNode(
        "credit_facility_total",
        {"2021": 500_000_000, "2022": 500_000_000, "2023": 500_000_000},
    )

    return {
        "total_property_value": total_property_value,
        "net_operating_income": net_operating_income,
        "total_debt": total_debt,
        "mortgage_debt": mortgage_debt,
        "construction_loans": construction_loans,
        "bridge_loans": bridge_loans,
        "mezzanine_debt": mezzanine_debt,
        "mortgage_payments": mortgage_payments,
        "interest_payments": interest_payments,
        "principal_payments": principal_payments,
        "fixed_rate_debt": fixed_rate_debt,
        "variable_rate_debt": variable_rate_debt,
        "unencumbered_assets": unencumbered_assets,
        "debt_maturities_1_year": debt_maturities_1_year,
        "debt_maturities_2_to_5_years": debt_maturities_2_to_5_years,
        "development_costs_to_date": development_costs_to_date,
        "remaining_development_budget": remaining_development_budget,
        "available_credit": available_credit,
        "credit_facility_total": credit_facility_total,
    }


def calculate_debt_metrics(
    data_nodes: dict[str, FinancialStatementItemNode], period: str = "2023"
) -> dict[str, float]:
    """Calculate key real estate debt metrics for analysis."""
    results = {}

    # Use the new calculate_metric helper function to simplify calculations
    metric_calculations = [
        ("loan_to_value_ratio", "loan_to_value_ratio"),
        ("debt_service_coverage_ratio_(real_estate)", "debt_service_coverage_ratio"),
        ("interest_coverage_ratio_(real_estate)", "interest_coverage_ratio"),
        ("unencumbered_asset_ratio", "unencumbered_asset_ratio"),
        ("fixed_rate_debt_percentage", "fixed_rate_debt_percentage"),
        ("weighted_average_interest_rate", "weighted_average_interest_rate"),
        ("debt_maturity_profile", "debt_maturity_profile_1yr"),
        ("construction_loan_to_cost_ratio", "construction_loan_to_cost_ratio"),
        ("debt_yield", "debt_yield"),
    ]

    for metric_name, result_key in metric_calculations:
        try:
            results[result_key] = calculate_metric(metric_name, data_nodes, period)
        except (KeyError, ValueError) as e:
            print(f"Warning: Could not calculate {metric_name}: {e}")
            results[result_key] = 0.0  # Default value for missing calculations

    return results


def analyze_debt_composition(
    data_nodes: dict[str, FinancialStatementItemNode], period: str = "2023"
) -> dict[str, float]:
    """Analyze the composition of the debt portfolio."""
    composition = {}

    total_debt = data_nodes["total_debt"].calculate(period)

    # Debt by type
    composition["mortgage_debt_pct"] = (
        data_nodes["mortgage_debt"].calculate(period) / total_debt
    ) * 100
    composition["construction_loans_pct"] = (
        data_nodes["construction_loans"].calculate(period) / total_debt
    ) * 100
    composition["bridge_loans_pct"] = (
        data_nodes["bridge_loans"].calculate(period) / total_debt
    ) * 100
    composition["mezzanine_debt_pct"] = (
        data_nodes["mezzanine_debt"].calculate(period) / total_debt
    ) * 100

    # Rate type composition
    composition["fixed_rate_pct"] = (
        data_nodes["fixed_rate_debt"].calculate(period) / total_debt
    ) * 100
    composition["variable_rate_pct"] = (
        data_nodes["variable_rate_debt"].calculate(period) / total_debt
    ) * 100

    # Maturity composition
    composition["maturities_1yr_pct"] = (
        data_nodes["debt_maturities_1_year"].calculate(period) / total_debt
    ) * 100
    composition["maturities_2_5yr_pct"] = (
        data_nodes["debt_maturities_2_to_5_years"].calculate(period) / total_debt
    ) * 100

    # Credit facility utilization
    total_facility = data_nodes["credit_facility_total"].calculate(period)
    available = data_nodes["available_credit"].calculate(period)
    composition["credit_utilization_pct"] = ((total_facility - available) / total_facility) * 100

    return composition


def analyze_debt_trends(
    data_nodes: dict[str, FinancialStatementItemNode],
) -> dict[str, float]:
    """Analyze debt trends over time."""
    trends = {}

    # LTV trend
    ltv_2022 = (
        data_nodes["total_debt"].calculate("2022")
        / data_nodes["total_property_value"].calculate("2022")
    ) * 100
    ltv_2023 = (
        data_nodes["total_debt"].calculate("2023")
        / data_nodes["total_property_value"].calculate("2023")
    ) * 100
    trends["ltv_change"] = ltv_2023 - ltv_2022

    # Interest rate trend
    rate_2022 = (
        data_nodes["interest_payments"].calculate("2022")
        / data_nodes["total_debt"].calculate("2022")
    ) * 100
    rate_2023 = (
        data_nodes["interest_payments"].calculate("2023")
        / data_nodes["total_debt"].calculate("2023")
    ) * 100
    trends["interest_rate_change"] = rate_2023 - rate_2022

    # DSCR trend
    dscr_2022 = data_nodes["net_operating_income"].calculate("2022") / data_nodes[
        "mortgage_payments"
    ].calculate("2022")
    dscr_2023 = data_nodes["net_operating_income"].calculate("2023") / data_nodes[
        "mortgage_payments"
    ].calculate("2023")
    trends["dscr_change"] = dscr_2023 - dscr_2022

    # Debt growth
    debt_2022 = data_nodes["total_debt"].calculate("2022")
    debt_2023 = data_nodes["total_debt"].calculate("2023")
    trends["debt_growth"] = ((debt_2023 - debt_2022) / debt_2022) * 100

    return trends


def perform_debt_analysis() -> None:
    """Perform comprehensive real estate debt analysis."""
    print("=== Real Estate Debt Analysis Example ===\n")

    # Create sample data
    data_nodes = create_sample_reit_debt_data()

    # Calculate debt metrics for 2023
    debt_metrics_2023 = calculate_debt_metrics(data_nodes, "2023")

    print("Key Debt Metrics for 2023:")
    print("-" * 50)

    # Display debt metrics with interpretations
    debt_metric_names = [
        ("loan_to_value_ratio", "Loan-to-Value Ratio"),
        ("debt_service_coverage_ratio", "Debt Service Coverage Ratio"),
        ("interest_coverage_ratio", "Interest Coverage Ratio"),
        ("unencumbered_asset_ratio", "Unencumbered Asset Ratio"),
        ("fixed_rate_debt_percentage", "Fixed Rate Debt Percentage"),
        ("weighted_average_interest_rate", "Weighted Average Interest Rate"),
        ("debt_maturity_profile_1yr", "Debt Maturing in 1 Year"),
        ("construction_loan_to_cost_ratio", "Construction Loan-to-Cost Ratio"),
        ("debt_yield", "Debt Yield"),
    ]

    for metric_key, display_name in debt_metric_names:
        value = debt_metrics_2023[metric_key]

        try:
            # Get interpretation if available
            metric_def = metric_registry.get(metric_key.replace("_(real_estate)", ""))
            if metric_def:
                interpretation = interpret_metric(metric_def, value)
                if metric_key in [
                    "loan_to_value_ratio",
                    "fixed_rate_debt_percentage",
                    "weighted_average_interest_rate",
                    "debt_maturity_profile_1yr",
                    "construction_loan_to_cost_ratio",
                    "debt_yield",
                ]:
                    print(f"{display_name}: {value:.1f}%")
                else:
                    print(f"{display_name}: {value:.2f}x")
                print(f"  → {interpretation['interpretation_message']}")
            elif "ratio" in metric_key or "coverage" in metric_key:
                print(f"{display_name}: {value:.2f}x")
            else:
                print(f"{display_name}: {value:.1f}%")
        except Exception:
            if "ratio" in metric_key or "coverage" in metric_key:
                print(f"{display_name}: {value:.2f}x")
            else:
                print(f"{display_name}: {value:.1f}%")
        print()

    # Debt composition analysis
    print("Debt Portfolio Composition (2023):")
    print("-" * 50)

    composition = analyze_debt_composition(data_nodes, "2023")

    print("By Debt Type:")
    print(f"  Mortgage Debt: {composition['mortgage_debt_pct']:.1f}%")
    print(f"  Construction Loans: {composition['construction_loans_pct']:.1f}%")
    print(f"  Bridge Loans: {composition['bridge_loans_pct']:.1f}%")
    print(f"  Mezzanine Debt: {composition['mezzanine_debt_pct']:.1f}%")
    print()

    print("By Interest Rate Type:")
    print(f"  Fixed Rate: {composition['fixed_rate_pct']:.1f}%")
    print(f"  Variable Rate: {composition['variable_rate_pct']:.1f}%")
    print()

    print("By Maturity:")
    print(f"  Maturing in 1 Year: {composition['maturities_1yr_pct']:.1f}%")
    print(f"  Maturing in 2-5 Years: {composition['maturities_2_5yr_pct']:.1f}%")
    print()

    print("Credit Facility Utilization:")
    print(f"  Utilization Rate: {composition['credit_utilization_pct']:.1f}%")
    print()

    # Trend analysis
    print("Debt Trends (2022-2023):")
    print("-" * 50)

    trends = analyze_debt_trends(data_nodes)

    print(f"LTV Change: {trends['ltv_change']:+.1f} percentage points")
    print(f"Interest Rate Change: {trends['interest_rate_change']:+.1f} percentage points")
    print(f"DSCR Change: {trends['dscr_change']:+.2f}x")
    print(f"Total Debt Growth: {trends['debt_growth']:+.1f}%")
    print()

    # Risk assessment
    print("Risk Assessment:")
    print("-" * 50)

    ltv = debt_metrics_2023["loan_to_value_ratio"]
    dscr = debt_metrics_2023["debt_service_coverage_ratio"]
    fixed_rate_pct = debt_metrics_2023["fixed_rate_debt_percentage"]
    near_term_maturities = debt_metrics_2023["debt_maturity_profile_1yr"]

    risk_factors = []

    if ltv > 75:
        risk_factors.append(f"High leverage (LTV: {ltv:.1f}%)")
    if dscr < 1.25:
        risk_factors.append(f"Tight debt service coverage (DSCR: {dscr:.2f}x)")
    if fixed_rate_pct < 70:
        risk_factors.append(f"High interest rate exposure ({100 - fixed_rate_pct:.1f}% variable)")
    if near_term_maturities > 20:
        risk_factors.append(
            f"High refinancing risk ({near_term_maturities:.1f}% maturing in 1 year)"
        )

    if risk_factors:
        print("Key Risk Factors:")
        for factor in risk_factors:
            print(f"  • {factor}")
    else:
        print("No significant risk factors identified")

    print("\n=== Debt Analysis Complete ===")


if __name__ == "__main__":
    perform_debt_analysis()
