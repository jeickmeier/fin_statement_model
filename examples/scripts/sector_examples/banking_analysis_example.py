"""Banking Analysis Example with Node Validation.

This example demonstrates comprehensive banking sector analysis with node name validation.
It shows how to create a validated financial model, calculate banking-specific metrics,
and perform regulatory compliance checks.
"""

import logging

from fin_statement_model.core.metrics import metric_registry
from fin_statement_model.io.validation import UnifiedNodeValidator
from fin_statement_model.core.metrics import (
    interpret_metric,
    calculate_metric,
)
from fin_statement_model.core.nodes import (
    FinancialStatementItemNode,
    standard_node_registry,
)
from fin_statement_model.core.nodes.base import Node
from fin_statement_model.core.nodes.calculation_nodes import (
    FormulaCalculationNode,
    CustomCalculationNode,
)
from fin_statement_model.config import get_config, update_config

logger = logging.getLogger(__name__)

config = get_config()
update_config({"logging": {"level": "INFO", "format": "%(message)s"}})


def validate_node_names_example() -> dict[str, str]:
    """Demonstrate node name validation and standardization.

    Returns:
        Dictionary mapping original names to standardized names.
    """
    logger.info("\n=== Node Name Validation Example ===")

    # Example of raw data with various node name formats
    raw_node_names = [
        "total_loans",  # Standard name
        "loan_loss_allowance",  # Alternate name for allowance_for_loan_losses
        "npl",  # Alternate name for non_performing_loans
        "deposits",  # Alternate name for total_deposits
        "shareholders_equity",  # Alternate name for total_shareholders_equity
        "nii",  # Alternate name for net_interest_income
        "tier_1_capital",  # Alternate name for total_tier_1_capital
        "rwa",  # Alternate name for total_risk_weighted_assets
        "custom_metric_xyz",  # Non-standard name
        "revenue_q1",  # Sub-node pattern
        "loan_loss_provision",  # Another alternate for provision_for_credit_losses
    ]

    logger.info(f"Raw node names to validate: {raw_node_names}")

    # Demo only: direct use of UnifiedNodeValidator; production code should use StatementConfig/StatementStructureBuilder for validation
    # Create unified validator for demo
    validator = UnifiedNodeValidator(
        standard_node_registry,
        strict_mode=False,  # Allow alternate names
        auto_standardize=True,  # Convert to standard names
        warn_on_non_standard=True,  # Log warnings for non-standard names
        enable_patterns=True,  # Enable pattern recognition for sub-nodes and formulas
    )

    # Validate and standardize names
    validation_results = validator.validate_batch(raw_node_names)

    logger.info("\n--- Basic Validation Results ---")
    standardized_mapping = {}
    for original_name, result in validation_results.items():
        logger.info(
            f"'{original_name}' -> '{result.standardized_name}' (Valid: {result.is_valid})"
        )
        logger.info(f"  Category: {result.category}")
        logger.info(f"  Message: {result.message}")
        if result.suggestions:
            logger.info(f"  Suggestions: {result.suggestions}")
        standardized_mapping[original_name] = result.standardized_name

    # Get validation summary
    logger.info("\n--- Validation Summary ---")
    logger.info(f"Total validated: {len(validation_results)}")
    valid_count = sum(1 for r in validation_results.values() if r.is_valid)
    logger.info(f"Valid: {valid_count}")
    logger.info(f"Invalid: {len(validation_results) - valid_count}")

    # Count by category
    categories = {}
    for result in validation_results.values():
        categories[result.category] = categories.get(result.category, 0) + 1

    for category, count in categories.items():
        logger.info(f"{category}: {count}")

    return standardized_mapping


def context_aware_validation_example():
    """Demonstrate context-aware node validation."""
    logger.info("\n=== Context-Aware Validation Example ===")

    # Create unified validator with pattern recognition
    validator = UnifiedNodeValidator(
        standard_node_registry,
        strict_mode=False,
        auto_standardize=True,
        enable_patterns=True,  # Enable pattern recognition
    )

    # Example node names with different patterns
    test_nodes = [
        ("total_loans", "data", None),
        ("revenue_q1", "data", None),  # Quarterly sub-node
        ("loan_loss_provision", "data", None),  # Alternate name
        (
            "debt_yield",
            "calculation",
            ["net_operating_income", "total_debt"],
        ),  # Formula node
        (
            "custom_banking_ratio",
            "formula",
            ["total_assets", "total_equity"],
        ),  # Custom formula
        (
            "npl_ratio",
            "calculation",
            ["non_performing_loans", "total_loans"],
        ),  # Ratio calculation
    ]

    logger.info("--- Context-Aware Validation Results ---")
    for node_name, node_type, parent_nodes in test_nodes:
        result = validator.validate(
            node_name, node_type=node_type, parent_nodes=parent_nodes
        )

        logger.info(f"Node: '{node_name}' (Type: {node_type})")
        logger.info(f"  Standardized: '{result.standardized_name}'")
        logger.info(f"  Valid: {result.is_valid}")
        logger.info(f"  Category: {result.category}")
        logger.info(f"  Message: {result.message}")
        if parent_nodes:
            logger.info(f"  Parent nodes: {parent_nodes}")
        logger.info("")


def create_validated_bank_data() -> dict[str, FinancialStatementItemNode]:
    """Create bank data using validated node names."""
    logger.info("\n=== Creating Validated Bank Data ===")

    # Create validator
    validator = UnifiedNodeValidator(standard_node_registry, auto_standardize=True)

    # Raw data with potentially non-standard names
    raw_data_mapping = {
        "loan_loss_allowance": {  # Non-standard name
            "2021": 800_000_000,
            "2022": 900_000_000,
            "2023": 1_100_000_000,
        },
        "npl": {  # Abbreviated name
            "2021": 1_200_000_000,
            "2022": 1_400_000_000,
            "2023": 1_800_000_000,
        },
        "tier_1_capital": {  # Standard name
            "2021": 8_500_000_000,
            "2022": 9_200_000_000,
            "2023": 10_000_000_000,
        },
    }

    validated_nodes = {}

    for raw_name, values in raw_data_mapping.items():
        # Validate and standardize the name
        result = validator.validate(raw_name)

        logger.info(
            f"  '{raw_name}' -> '{result.standardized_name}' (Valid: {result.is_valid})"
        )
        if result.message:
            logger.info(f"    Note: {result.message}")

        # Create node with standardized name
        validated_nodes[result.standardized_name] = FinancialStatementItemNode(
            result.standardized_name, values
        )

    return validated_nodes


def validate_data_completeness(
    data_nodes: dict[str, FinancialStatementItemNode],
) -> dict:
    """Validate that all required banking data is present."""
    logger.info("\n=== Data Completeness Validation ===")

    # Define required banking nodes for comprehensive analysis
    required_nodes = [
        "total_loans",
        "non_performing_loans",
        "allowance_for_loan_losses",
        "total_deposits",
        "total_equity",
        "net_interest_income",
        "non_interest_income",
        "non_interest_expense",
        "provision_for_loan_losses",
        "tier_1_capital",
        "risk_weighted_assets",
    ]

    # Optional but recommended nodes
    recommended_nodes = [
        "high_quality_liquid_assets",
        "net_cash_outflows_30_days",
        "available_stable_funding",
        "required_stable_funding",
        "common_equity_tier_1_capital",
        "total_capital",
    ]

    validation_report = {
        "required_missing": [],
        "recommended_missing": [],
        "total_nodes": len(data_nodes),
        "completeness_score": 0.0,
    }

    # Check required nodes
    for node_name in required_nodes:
        if node_name not in data_nodes:
            validation_report["required_missing"].append(node_name)

    # Check recommended nodes
    for node_name in recommended_nodes:
        if node_name not in data_nodes:
            validation_report["recommended_missing"].append(node_name)

    # Calculate completeness score
    total_expected = len(required_nodes) + len(recommended_nodes)
    missing_count = len(validation_report["required_missing"]) + len(
        validation_report["recommended_missing"]
    )
    validation_report["completeness_score"] = (
        (total_expected - missing_count) / total_expected
    ) * 100

    # Print validation results
    logger.info(f"Total nodes available: {validation_report['total_nodes']}")
    logger.info(
        f"Data completeness score: {validation_report['completeness_score']:.1f}%"
    )

    if validation_report["required_missing"]:
        logger.info(
            f"Missing required nodes ({len(validation_report['required_missing'])}):"
        )
        for node in validation_report["required_missing"]:
            logger.info(f"  - {node}")
    else:
        logger.info("✓ All required nodes present")

    if validation_report["recommended_missing"]:
        logger.info(
            f"Missing recommended nodes ({len(validation_report['recommended_missing'])}):"
        )
        for node in validation_report["recommended_missing"]:
            logger.info(f"  - {node}")
    else:
        logger.info("✓ All recommended nodes present")

    return validation_report


def analyze_asset_quality(
    data_nodes: dict[str, FinancialStatementItemNode], period: str
) -> dict:
    """Analyze asset quality metrics for the bank."""
    logger.info(f"\n=== Asset Quality Analysis for {period} ===")

    asset_quality_metrics = [
        "non_performing_loan_ratio",
        "charge_off_rate",
        "provision_coverage_ratio",
        "allowance_to_loans_ratio",
    ]

    results = {}
    for metric_name in asset_quality_metrics:
        try:
            value = calculate_metric(metric_name, data_nodes, period)
            interpretation = interpret_metric(metric_registry.get(metric_name), value)

            results[metric_name] = {
                "value": value,
                "interpretation": interpretation,
            }

            logger.info(f"{metric_name}: {value:.2f}% - {interpretation['rating']}")
            logger.info(f"  {interpretation['interpretation_message']}")

        except Exception as e:
            logger.exception(f"Could not calculate {metric_name}")
            results[metric_name] = {"error": str(e)}

    return results


def analyze_capital_adequacy(
    data_nodes: dict[str, FinancialStatementItemNode], period: str
) -> dict:
    """Analyze capital adequacy metrics for the bank."""
    logger.info(f"\n=== Capital Adequacy Analysis for {period} ===")

    capital_metrics = [
        "common_equity_tier_1_ratio",
        "tier_1_capital_ratio",
        "total_capital_ratio",
        "tier_1_leverage_ratio",
    ]

    results = {}
    for metric_name in capital_metrics:
        try:
            value = calculate_metric(metric_name, data_nodes, period)
            interpretation = interpret_metric(metric_registry.get(metric_name), value)

            results[metric_name] = {
                "value": value,
                "interpretation": interpretation,
            }

            logger.info(f"{metric_name}: {value:.2f}% - {interpretation['rating']}")
            logger.info(f"  {interpretation['interpretation_message']}")

        except Exception as e:
            logger.exception(f"Could not calculate {metric_name}")
            results[metric_name] = {"error": str(e)}

    return results


def analyze_profitability(
    data_nodes: dict[str, FinancialStatementItemNode], period: str
) -> dict:
    """Analyze profitability metrics for the bank."""
    logger.info(f"\n=== Profitability Analysis for {period} ===")

    profitability_metrics = [
        "net_interest_margin",
        "efficiency_ratio",
        "return_on_assets_(banking)",
        "return_on_equity_(banking)",
        "fee_income_ratio",
    ]

    results = {}
    for metric_name in profitability_metrics:
        try:
            value = calculate_metric(metric_name, data_nodes, period)
            interpretation = interpret_metric(metric_registry.get(metric_name), value)

            results[metric_name] = {
                "value": value,
                "interpretation": interpretation,
            }

            logger.info(f"{metric_name}: {value:.2f}% - {interpretation['rating']}")
            logger.info(f"  {interpretation['interpretation_message']}")

        except Exception as e:
            logger.exception(f"Could not calculate {metric_name}")
            results[metric_name] = {"error": str(e)}

    return results


def analyze_liquidity(
    data_nodes: dict[str, FinancialStatementItemNode], period: str
) -> dict:
    """Analyze liquidity metrics for the bank."""
    logger.info(f"\n=== Liquidity Analysis for {period} ===")

    liquidity_metrics = [
        "liquidity_coverage_ratio",
        "net_stable_funding_ratio",
        "deposits_to_loans_ratio",
        "loan_to_deposit_ratio",
        "liquid_assets_ratio",
    ]

    results = {}
    for metric_name in liquidity_metrics:
        try:
            value = calculate_metric(metric_name, data_nodes, period)
            interpretation = interpret_metric(metric_registry.get(metric_name), value)

            results[metric_name] = {
                "value": value,
                "interpretation": interpretation,
            }

            logger.info(f"{metric_name}: {value:.2f}% - {interpretation['rating']}")
            logger.info(f"  {interpretation['interpretation_message']}")

        except Exception as e:
            logger.exception(f"Could not calculate {metric_name}")
            results[metric_name] = {"error": str(e)}

    return results


def generate_banking_dashboard(
    data_nodes: dict[str, FinancialStatementItemNode], period: str
) -> dict:
    """Generate a comprehensive banking analysis dashboard."""
    logger.info(f"\n{'=' * 60}")
    logger.info(f"COMPREHENSIVE BANKING ANALYSIS DASHBOARD - {period}")
    logger.info(f"{'=' * 60}")

    # Asset Quality Analysis
    asset_quality_results = analyze_asset_quality(data_nodes, period)

    # Capital Adequacy Analysis
    capital_results = analyze_capital_adequacy(data_nodes, period)

    # Profitability Analysis
    profitability_results = analyze_profitability(data_nodes, period)

    # Liquidity Analysis
    liquidity_results = analyze_liquidity(data_nodes, period)

    # Summary Assessment
    logger.info(f"\n=== Overall Assessment for {period} ===")

    # Count metrics by rating
    all_results = {
        **asset_quality_results,
        **capital_results,
        **profitability_results,
        **liquidity_results,
    }
    ratings = [
        result["interpretation"]["rating"]
        for result in all_results.values()
        if "interpretation" in result
    ]

    rating_counts = {}
    for rating in ratings:
        rating_counts[rating] = rating_counts.get(rating, 0) + 1

    logger.info("Rating Distribution:")
    for rating, count in rating_counts.items():
        logger.info(f"  {rating}: {count} metrics")

    return {
        "asset_quality": asset_quality_results,
        "capital_adequacy": capital_results,
        "profitability": profitability_results,
        "liquidity": liquidity_results,
        "summary": rating_counts,
    }


def main():
    """Run the banking analysis example showcasing graph capabilities."""
    # Create and demonstrate the graph-based banking example
    create_banking_graph_example()


def create_banking_graph_example() -> dict[str, FinancialStatementItemNode]:
    """Create a comprehensive banking graph with calculation nodes and relationships.

    This demonstrates the difference between a simple collection of nodes
    and a true graph structure with dependencies and calculations.
    """
    logger.info("\n=== Creating Comprehensive Banking Graph ===")

    # 1. Base data nodes (leaf nodes in the graph)
    logger.info("Creating base data nodes...")

    # Asset nodes
    cash_and_equivalents = FinancialStatementItemNode(
        "cash_and_equivalents",
        {"2021": 8_000_000_000, "2022": 8_500_000_000, "2023": 9_000_000_000},
    )

    securities_available_for_sale = FinancialStatementItemNode(
        "securities_available_for_sale",
        {"2021": 10_000_000_000, "2022": 11_000_000_000, "2023": 12_000_000_000},
    )

    securities_held_to_maturity = FinancialStatementItemNode(
        "securities_held_to_maturity",
        {"2021": 2_000_000_000, "2022": 2_000_000_000, "2023": 2_000_000_000},
    )

    gross_loans = FinancialStatementItemNode(
        "gross_loans",
        {"2021": 45_675_000_000, "2022": 48_720_000_000, "2023": 52_780_000_000},
    )

    allowance_for_loan_losses = FinancialStatementItemNode(
        "allowance_for_loan_losses",
        {"2021": 675_000_000, "2022": 720_000_000, "2023": 780_000_000},
    )

    # Liability nodes
    demand_deposits = FinancialStatementItemNode(
        "demand_deposits",
        {"2021": 20_000_000_000, "2022": 22_000_000_000, "2023": 24_000_000_000},
    )

    time_deposits = FinancialStatementItemNode(
        "time_deposits",
        {"2021": 25_000_000_000, "2022": 27_000_000_000, "2023": 29_000_000_000},
    )

    savings_deposits = FinancialStatementItemNode(
        "savings_deposits",
        {"2021": 7_000_000_000, "2022": 7_000_000_000, "2023": 7_000_000_000},
    )

    # Income statement nodes
    interest_income_loans = FinancialStatementItemNode(
        "interest_income_loans",
        {"2021": 2_400_000_000, "2022": 2_650_000_000, "2023": 3_000_000_000},
    )

    interest_income_securities = FinancialStatementItemNode(
        "interest_income_securities",
        {"2021": 300_000_000, "2022": 350_000_000, "2023": 400_000_000},
    )

    interest_expense_deposits = FinancialStatementItemNode(
        "interest_expense_deposits",
        {"2021": 500_000_000, "2022": 600_000_000, "2023": 700_000_000},
    )

    interest_expense_borrowings = FinancialStatementItemNode(
        "interest_expense_borrowings",
        {"2021": 100_000_000, "2022": 100_000_000, "2023": 100_000_000},
    )

    # 2. Create calculation nodes that derive values from base nodes
    logger.info("Creating calculation nodes with dependencies...")

    # Total securities = AFS + HTM
    total_securities = FormulaCalculationNode(
        name="total_securities",
        inputs={
            "afs": securities_available_for_sale,
            "htm": securities_held_to_maturity,
        },
        formula="afs + htm",
    )

    # Net loans = Gross loans - Allowance
    net_loans = FormulaCalculationNode(
        name="net_loans",
        inputs={"gross": gross_loans, "allowance": allowance_for_loan_losses},
        formula="gross - allowance",
    )

    # Total deposits = Demand + Time + Savings
    total_deposits = CustomCalculationNode(
        name="total_deposits",
        inputs=[demand_deposits, time_deposits, savings_deposits],
        formula_func=lambda demand, time, savings: demand + time + savings,
        description="Sum of all deposit types",
    )

    # Total interest income = Loan income + Securities income
    total_interest_income = FormulaCalculationNode(
        name="total_interest_income",
        inputs={
            "loans": interest_income_loans,
            "securities": interest_income_securities,
        },
        formula="loans + securities",
    )

    # Total interest expense = Deposit expense + Borrowing expense
    total_interest_expense = FormulaCalculationNode(
        name="total_interest_expense",
        inputs={
            "deposits": interest_expense_deposits,
            "borrowings": interest_expense_borrowings,
        },
        formula="deposits + borrowings",
    )

    # Net interest income = Total interest income - Total interest expense
    net_interest_income = CustomCalculationNode(
        name="net_interest_income",
        inputs=[total_interest_income, total_interest_expense],
        formula_func=lambda income, expense: income - expense,
        description="Net interest income calculation",
    )

    # Total earning assets = Net loans + Total securities
    total_earning_assets = CustomCalculationNode(
        name="total_earning_assets",
        inputs=[net_loans, total_securities],
        formula_func=lambda loans, securities: loans + securities,
        description="Sum of earning assets",
    )

    # Total assets = Cash + Securities + Net loans + Other (simplified)
    other_assets = FinancialStatementItemNode(
        "other_assets",
        {"2021": 2_000_000_000, "2022": 2_200_000_000, "2023": 2_400_000_000},
    )

    total_assets = CustomCalculationNode(
        name="total_assets",
        inputs=[cash_and_equivalents, total_securities, net_loans, other_assets],
        formula_func=lambda cash, securities, loans, other: cash
        + securities
        + loans
        + other,
        description="Total bank assets",
    )

    # 3. Create ratio calculation nodes
    logger.info("Creating ratio calculation nodes...")

    # Loan to deposit ratio = Net loans / Total deposits
    loan_to_deposit_ratio = CustomCalculationNode(
        name="loan_to_deposit_ratio_calculated",
        inputs=[net_loans, total_deposits],
        formula_func=lambda loans, deposits: loans / deposits if deposits != 0 else 0,
        description="Loan to deposit ratio",
    )

    # Net interest margin = Net interest income / Total earning assets
    net_interest_margin_calculated = CustomCalculationNode(
        name="net_interest_margin_calculated",
        inputs=[net_interest_income, total_earning_assets],
        formula_func=lambda nii, assets: nii / assets if assets != 0 else 0,
        description="Net interest margin calculation",
    )

    # 4. Demonstrate graph traversal and calculation
    logger.info("Demonstrating graph calculations...")

    # Calculate values for 2023 to show graph dependencies
    period = "2023"

    # These will automatically calculate based on their inputs
    calculated_values = {
        "Total Securities": total_securities.calculate(period),
        "Net Loans": net_loans.calculate(period),
        "Total Deposits": total_deposits.calculate(period),
        "Net Interest Income": net_interest_income.calculate(period),
        "Total Assets": total_assets.calculate(period),
        "Loan-to-Deposit Ratio": loan_to_deposit_ratio.calculate(period) * 100,
        "Net Interest Margin": net_interest_margin_calculated.calculate(period) * 100,
    }

    logger.info(f"\nCalculated values for {period}:")
    for name, value in calculated_values.items():
        if "Ratio" in name or "Margin" in name:
            logger.info(f"  {name}: {value:.2f}%")
        else:
            logger.info(f"  {name}: ${value:,.0f}")

    # 5. Show graph dependencies
    logger.info("\nGraph Dependencies:")

    # Handle different input types for different calculation nodes
    def get_input_names(node: Node) -> list[str]:
        if hasattr(node, "inputs"):
            if isinstance(node.inputs, dict):
                # FormulaCalculationNode has dict inputs
                return [input_node.name for input_node in node.inputs.values()]
            elif isinstance(node.inputs, list):
                # CustomCalculationNode has list inputs
                return [input_node.name for input_node in node.inputs]
        return []

    logger.info(f"  total_assets depends on: {get_input_names(total_assets)}")
    logger.info(
        f"  net_interest_income depends on: {get_input_names(net_interest_income)}"
    )
    logger.info(
        f"  total_interest_income depends on: {get_input_names(total_interest_income)}"
    )
    logger.info(f"  total_securities depends on: {get_input_names(total_securities)}")
    logger.info(f"  net_loans depends on: {get_input_names(net_loans)}")

    # Return all nodes (both base and calculated)
    return {
        # Base data nodes
        "cash_and_equivalents": cash_and_equivalents,
        "securities_available_for_sale": securities_available_for_sale,
        "securities_held_to_maturity": securities_held_to_maturity,
        "gross_loans": gross_loans,
        "allowance_for_loan_losses": allowance_for_loan_losses,
        "demand_deposits": demand_deposits,
        "time_deposits": time_deposits,
        "savings_deposits": savings_deposits,
        "interest_income_loans": interest_income_loans,
        "interest_income_securities": interest_income_securities,
        "interest_expense_deposits": interest_expense_deposits,
        "interest_expense_borrowings": interest_expense_borrowings,
        "other_assets": other_assets,
        # Calculated nodes (graph structure)
        "total_securities": total_securities,
        "net_loans": net_loans,
        "total_deposits": total_deposits,
        "total_interest_income": total_interest_income,
        "total_interest_expense": total_interest_expense,
        "net_interest_income": net_interest_income,
        "total_earning_assets": total_earning_assets,
        "total_assets": total_assets,
        "loan_to_deposit_ratio_calculated": loan_to_deposit_ratio,
        "net_interest_margin_calculated": net_interest_margin_calculated,
    }


if __name__ == "__main__":
    main()
