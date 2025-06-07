"""Real Estate Company Debt Analysis Example.

This example demonstrates comprehensive debt analysis for a real estate company,
including loan portfolios, maturity schedules, and covenant calculations.
"""

import logging
from typing import Union

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import FinancialStatementItemNode

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_real_estate_financial_model() -> Graph:
    """Create a financial model for a real estate company with detailed debt analysis."""
    graph = Graph()

    # === Basic Financial Statement Items ===
    # Balance Sheet Items
    balance_sheet_items = {
        # Assets
        "investment_properties": {"2022": 5000000, "2023": 5500000},
        "development_properties": {"2022": 800000, "2023": 1200000},
        "cash": {"2022": 150000, "2023": 180000},
        "other_assets": {"2022": 50000, "2023": 70000},
        # Liabilities - Debt Components
        "mortgage_debt": {"2022": 2800000, "2023": 3100000},
        "construction_loans": {"2022": 500000, "2023": 750000},
        "bridge_loans": {"2022": 200000, "2023": 150000},
        "mezzanine_debt": {"2022": 300000, "2023": 250000},
        "credit_facility": {"2022": 0, "2023": 100000},
        # Other Liabilities
        "accounts_payable": {"2022": 100000, "2023": 120000},
        "accrued_expenses": {"2022": 80000, "2023": 90000},
        # Equity
        "common_equity": {"2022": 1500000, "2023": 1600000},
        "preferred_equity": {"2022": 500000, "2023": 500000},
    }

    # Income Statement Items
    income_items = {
        "rental_income": {"2022": 450000, "2023": 520000},
        "property_management_fees": {"2022": 25000, "2023": 30000},
        "other_income": {"2022": 15000, "2023": 20000},
        "property_operating_expenses": {"2022": 180000, "2023": 210000},
        "interest_expense_mortgage": {"2022": 140000, "2023": 155000},
        "interest_expense_construction": {"2022": 35000, "2023": 52500},
        "interest_expense_other": {"2022": 30000, "2023": 25000},
        "depreciation": {"2022": 125000, "2023": 140000},
        "general_admin": {"2022": 45000, "2023": 50000},
    }

    # Debt Details
    debt_details = {
        # Fixed vs Variable Rate Breakdown
        "fixed_rate_debt": {"2022": 3200000, "2023": 3400000},
        "variable_rate_debt": {"2022": 600000, "2023": 950000},
        # Maturity Schedule
        "debt_maturing_1yr": {"2022": 200000, "2023": 450000},
        "debt_maturing_2_5yr": {"2022": 1500000, "2023": 1600000},
        "debt_maturing_after_5yr": {"2022": 2100000, "2023": 2300000},
        # Credit Facility Details
        "credit_facility_limit": {"2022": 500000, "2023": 500000},
        "unencumbered_assets": {"2022": 800000, "2023": 1000000},
    }

    # Add all items to graph
    for name, values in {**balance_sheet_items, **income_items, **debt_details}.items():
        node = FinancialStatementItemNode(name, values)
        graph.add_node(node)

    # === Calculated Items using graph.add_calculation ===

    # Total Assets
    graph.add_calculation(
        name="total_assets",
        input_names=[
            "investment_properties",
            "development_properties",
            "cash",
            "other_assets",
        ],
        operation_type="addition",
    )

    # Total Debt
    graph.add_calculation(
        name="total_debt",
        input_names=[
            "mortgage_debt",
            "construction_loans",
            "bridge_loans",
            "mezzanine_debt",
            "credit_facility",
        ],
        operation_type="addition",
    )

    # Total Equity
    graph.add_calculation(
        name="total_equity",
        input_names=["common_equity", "preferred_equity"],
        operation_type="addition",
    )

    # Net Operating Income (NOI)
    graph.add_calculation(
        name="total_income",
        input_names=["rental_income", "property_management_fees", "other_income"],
        operation_type="addition",
    )

    graph.add_calculation(
        name="net_operating_income",
        input_names=["total_income", "property_operating_expenses"],
        operation_type="subtraction",
    )

    # Total Interest Expense
    graph.add_calculation(
        name="total_interest_expense",
        input_names=[
            "interest_expense_mortgage",
            "interest_expense_construction",
            "interest_expense_other",
        ],
        operation_type="addition",
    )

    # EBITDA
    graph.add_calculation(
        name="ebitda",
        input_names=["net_operating_income", "general_admin"],
        operation_type="subtraction",
    )

    # === Key Debt Metrics ===

    # Loan-to-Value (LTV) Ratio
    graph.add_calculation(
        name="ltv_ratio",
        input_names=["total_debt", "total_assets"],
        operation_type="division",
    )

    # Debt Service Coverage Ratio (DSCR)
    graph.add_calculation(
        name="dscr",
        input_names=["net_operating_income", "total_interest_expense"],
        operation_type="division",
    )

    # Debt-to-Equity Ratio
    graph.add_calculation(
        name="debt_to_equity",
        input_names=["total_debt", "total_equity"],
        operation_type="division",
    )

    # Interest Coverage Ratio
    graph.add_calculation(
        name="interest_coverage_ratio",
        input_names=["ebitda", "total_interest_expense"],
        operation_type="division",
    )

    # Weighted Average Interest Rate
    graph.add_calculation(
        name="weighted_avg_interest_rate",
        input_names=["total_interest_expense", "total_debt"],
        operation_type="division",
    )

    return graph


def calculate_debt_metrics(graph: Graph, period: str = "2023") -> dict[str, Union[float, None]]:
    """Calculate and return key debt metrics for analysis."""
    metrics = {}

    # Basic metrics
    basic_metrics = [
        "ltv_ratio",
        "dscr",
        "debt_to_equity",
        "interest_coverage_ratio",
        "weighted_avg_interest_rate",
    ]

    for metric_name in basic_metrics:
        try:
            metrics[metric_name] = graph.calculate(metric_name, period)
        except Exception as e:
            logger.warning(f"Warning: Could not calculate {metric_name}: {e}")
            metrics[metric_name] = None

    return metrics


def analyze_debt_composition(graph: Graph, period: str = "2023") -> dict[str, float]:
    """Analyze the composition of the debt portfolio."""
    try:
        total_debt = graph.calculate("total_debt", period)

        # Debt type breakdown
        mortgage = graph.get_node("mortgage_debt").get_value(period)
        construction = graph.get_node("construction_loans").get_value(period)
        bridge = graph.get_node("bridge_loans").get_value(period)
        mezzanine = graph.get_node("mezzanine_debt").get_value(period)

        # Fixed vs Variable
        fixed = graph.get_node("fixed_rate_debt").get_value(period)
        variable = graph.get_node("variable_rate_debt").get_value(period)

        # Maturity profile
        short_term = graph.get_node("debt_maturing_1yr").get_value(period)
        medium_term = graph.get_node("debt_maturing_2_5yr").get_value(period)

        # Credit utilization
        credit_used = graph.get_node("credit_facility").get_value(period)
        credit_limit = graph.get_node("credit_facility_limit").get_value(period)

        composition = {
            "mortgage_debt_pct": (mortgage / total_debt) * 100,
            "construction_loans_pct": (construction / total_debt) * 100,
            "bridge_loans_pct": (bridge / total_debt) * 100,
            "mezzanine_debt_pct": (mezzanine / total_debt) * 100,
            "fixed_rate_pct": (fixed / total_debt) * 100,
            "variable_rate_pct": (variable / total_debt) * 100,
            "maturities_1yr_pct": (short_term / total_debt) * 100,
            "maturities_2_5yr_pct": (medium_term / total_debt) * 100,
            "credit_utilization_pct": (
                (credit_used / credit_limit) * 100 if credit_limit > 0 else 0
            ),
        }

        return composition
    except Exception:
        logger.exception("Error analyzing debt composition")
        return {}


def calculate_debt_trends(graph: Graph) -> dict[str, float]:
    """Calculate year-over-year trends in debt metrics."""
    trends = {}

    try:
        # LTV trend
        ltv_2022 = graph.calculate("ltv_ratio", "2022")
        ltv_2023 = graph.calculate("ltv_ratio", "2023")
        trends["ltv_change"] = ltv_2023 - ltv_2022

        # Interest rate trend
        rate_2022 = graph.calculate("weighted_avg_interest_rate", "2022")
        rate_2023 = graph.calculate("weighted_avg_interest_rate", "2023")
        trends["interest_rate_change"] = (rate_2023 - rate_2022) * 100

        # DSCR trend
        dscr_2022 = graph.calculate("dscr", "2022")
        dscr_2023 = graph.calculate("dscr", "2023")
        trends["dscr_change"] = dscr_2023 - dscr_2022

        # Total debt growth
        debt_2022 = graph.calculate("total_debt", "2022")
        debt_2023 = graph.calculate("total_debt", "2023")
        trends["debt_growth"] = ((debt_2023 - debt_2022) / debt_2022) * 100

    except Exception:
        logger.exception("Error calculating trends")

    return trends


def interpret_debt_metrics(
    metrics: dict[str, Union[float, None]],
) -> dict[str, dict[str, str]]:
    """Provide interpretation of debt metrics for real estate context."""
    interpretations = {}

    # LTV Ratio interpretation
    ltv = metrics.get("ltv_ratio", 0)
    if ltv:
        if ltv < 0.5:
            interpretations["ltv"] = {
                "status": "Conservative",
                "interpretation": "Low leverage, strong equity cushion",
            }
        elif ltv < 0.65:
            interpretations["ltv"] = {
                "status": "Moderate",
                "interpretation": "Industry standard leverage",
            }
        elif ltv < 0.75:
            interpretations["ltv"] = {
                "status": "Aggressive",
                "interpretation": "High leverage, limited refinancing flexibility",
            }
        else:
            interpretations["ltv"] = {
                "status": "Very High Risk",
                "interpretation": "Excessive leverage, potential covenant breach",
            }

    # DSCR interpretation
    dscr = metrics.get("dscr", 0)
    if dscr:
        if dscr > 1.5:
            interpretations["dscr"] = {
                "status": "Strong",
                "interpretation": "Comfortable debt service coverage",
            }
        elif dscr > 1.25:
            interpretations["dscr"] = {
                "status": "Adequate",
                "interpretation": "Meeting typical covenant requirements",
            }
        elif dscr > 1.0:
            interpretations["dscr"] = {
                "status": "Thin",
                "interpretation": "Limited margin of safety",
            }
        else:
            interpretations["dscr"] = {
                "status": "Insufficient",
                "interpretation": "Unable to cover debt service from operations",
            }

    return interpretations


def main() -> None:
    """Run the real estate debt analysis example."""
    logger.info("=== Real Estate Debt Analysis Example ===\n")

    # Create the financial model
    graph = create_real_estate_financial_model()

    # Calculate key metrics
    metrics = calculate_debt_metrics(graph)

    # Display results
    logger.info("Key Debt Metrics for 2023:")
    logger.info("-" * 50)

    # Format and display metrics
    metric_display = {
        "ltv_ratio": ("Loan-to-Value Ratio", "%"),
        "dscr": ("Debt Service Coverage Ratio", "x"),
        "debt_to_equity": ("Debt-to-Equity Ratio", "x"),
        "interest_coverage_ratio": ("Interest Coverage Ratio", "x"),
        "weighted_avg_interest_rate": ("Weighted Avg Interest Rate", "%"),
    }

    interpretations = interpret_debt_metrics(metrics)

    for metric_key, (display_name, unit) in metric_display.items():
        value = metrics.get(metric_key)
        if value is not None:
            if unit == "%":
                if metric_key == "weighted_avg_interest_rate":
                    value *= 100  # Convert to percentage
                elif metric_key == "ltv_ratio":
                    value *= 100  # LTV is a ratio, convert to percentage
                logger.info(f"{display_name}: {value:.1f}%")
            else:
                logger.info(f"{display_name}: {value:.2f}x")

            # Add interpretation if available
            if metric_key in interpretations:
                logger.info(f"  → {interpretations[metric_key]['interpretation']}")

            logger.info("")

    # Analyze debt composition
    logger.info("Debt Portfolio Composition (2023):")
    logger.info("-" * 50)

    composition = analyze_debt_composition(graph)

    logger.info("By Debt Type:")
    logger.info(f"  Mortgage Debt: {composition['mortgage_debt_pct']:.1f}%")
    logger.info(f"  Construction Loans: {composition['construction_loans_pct']:.1f}%")
    logger.info(f"  Bridge Loans: {composition['bridge_loans_pct']:.1f}%")
    logger.info(f"  Mezzanine Debt: {composition['mezzanine_debt_pct']:.1f}%")
    logger.info("")

    logger.info("By Interest Rate Type:")
    logger.info(f"  Fixed Rate: {composition['fixed_rate_pct']:.1f}%")
    logger.info(f"  Variable Rate: {composition['variable_rate_pct']:.1f}%")
    logger.info("")

    logger.info("By Maturity:")
    logger.info(f"  Maturing in 1 Year: {composition['maturities_1yr_pct']:.1f}%")
    logger.info(f"  Maturing in 2-5 Years: {composition['maturities_2_5yr_pct']:.1f}%")
    logger.info("")

    logger.info("Credit Facility Utilization:")
    logger.info(f"  Utilization Rate: {composition['credit_utilization_pct']:.1f}%")
    logger.info("")

    # Show trends
    logger.info("Debt Trends (2022-2023):")
    logger.info("-" * 50)

    trends = calculate_debt_trends(graph)

    logger.info(f"LTV Change: {trends['ltv_change']:+.1f} percentage points")
    logger.info(f"Interest Rate Change: {trends['interest_rate_change']:+.1f} percentage points")
    logger.info(f"DSCR Change: {trends['dscr_change']:+.2f}x")
    logger.info(f"Total Debt Growth: {trends['debt_growth']:+.1f}%")
    logger.info("")

    # Risk assessment
    logger.info("Risk Assessment:")
    logger.info("-" * 50)

    risk_factors = []

    if metrics.get("ltv_ratio", 0) > 0.65:
        risk_factors.append("High leverage (LTV > 65%)")

    if metrics.get("dscr", 0) < 1.25:
        risk_factors.append("Low debt service coverage")

    if composition.get("variable_rate_pct", 0) > 30:
        risk_factors.append("Significant interest rate risk exposure")

    if composition.get("maturities_1yr_pct", 0) > 20:
        risk_factors.append("Near-term refinancing risk")

    if risk_factors:
        logger.info("Key Risk Factors:")
        for factor in risk_factors:
            logger.info(f"  • {factor}")
    else:
        logger.info("No significant risk factors identified")

    logger.info("\n=== Debt Analysis Complete ===")


if __name__ == "__main__":
    main()
