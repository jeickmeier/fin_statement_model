"""Banking Analysis Example.

This example demonstrates how to use the banking-specific metrics
and nodes in the financial statement model library for bank analysis.
It also shows how to use node name validators for data quality assurance.
"""

from fin_statement_model.core.metrics import (
    metric_registry,
    interpret_metric,
    calculate_metric,
)
from fin_statement_model.core.nodes import FinancialStatementItemNode
from fin_statement_model.core.nodes.base import Node
from fin_statement_model.io.node_name_validator import NodeNameValidator
from fin_statement_model.io.context_aware_validator import ContextAwareNodeValidator
from fin_statement_model.core.nodes.calculation_nodes import (
    FormulaCalculationNode,
    CustomCalculationNode,
)


def validate_node_names_example() -> dict[str, str]:
    """Demonstrate node name validation and standardization.

    Returns:
        Dictionary mapping original names to standardized names.
    """
    print("\n=== Node Name Validation Example ===")

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

    print(f"Raw node names to validate: {raw_node_names}")

    # Create basic validator
    validator = NodeNameValidator(
        strict_mode=False,  # Allow alternate names
        auto_standardize=True,  # Convert to standard names
        warn_on_non_standard=True,  # Log warnings for non-standard names
    )

    # Validate and standardize names
    validation_results = validator.validate_batch(raw_node_names)

    print("\n--- Basic Validation Results ---")
    standardized_mapping = {}
    for original_name, (
        standardized_name,
        is_valid,
        message,
    ) in validation_results.items():
        print(f"'{original_name}' -> '{standardized_name}' (Valid: {is_valid})")
        print(f"  Message: {message}")
        standardized_mapping[original_name] = standardized_name

    # Get validation summary
    summary = validator.get_validation_summary()
    print("\n--- Validation Summary ---")
    print(f"Total validated: {summary['total_validated']}")
    print(f"Valid: {summary['valid']}")
    print(f"Invalid: {summary['invalid']}")
    print(f"Standard names: {summary['standard_names']}")
    print(f"Alternate names: {summary['alternate_names']}")
    print(f"Unrecognized names: {summary['unrecognized_names']}")

    return standardized_mapping


def context_aware_validation_example():
    """Demonstrate context-aware node validation."""
    print("\n=== Context-Aware Validation Example ===")

    # Create context-aware validator
    context_validator = ContextAwareNodeValidator(
        strict_mode=False,
        auto_standardize=True,
        validate_subnodes=True,
        validate_formulas=True,
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

    print("--- Context-Aware Validation Results ---")
    for node_name, node_type, parent_nodes in test_nodes:
        standardized, is_valid, message, category = context_validator.validate_node(
            node_name, node_type=node_type, parent_nodes=parent_nodes
        )

        print(f"Node: '{node_name}' (Type: {node_type})")
        print(f"  Standardized: '{standardized}'")
        print(f"  Valid: {is_valid}")
        print(f"  Category: {category}")
        print(f"  Message: {message}")
        if parent_nodes:
            print(f"  Parent nodes: {parent_nodes}")
        print()


def create_validated_bank_data() -> dict[str, FinancialStatementItemNode]:
    """Create bank data using validated node names."""
    print("\n=== Creating Validated Bank Data ===")

    # Create validator
    validator = NodeNameValidator(auto_standardize=True)

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
        standardized_name, is_valid, message = validator.validate_and_standardize(raw_name)

        print(f"  '{raw_name}' -> '{standardized_name}' (Valid: {is_valid})")
        if message:
            print(f"    Note: {message}")

        # Create node with standardized name
        validated_nodes[standardized_name] = FinancialStatementItemNode(standardized_name, values)

    return validated_nodes


def create_sample_bank_data() -> dict[str, FinancialStatementItemNode]:
    """Create sample bank financial data for analysis."""
    # Asset data
    total_loans = FinancialStatementItemNode(
        "total_loans",
        {"2021": 45_000_000_000, "2022": 48_000_000_000, "2023": 52_000_000_000},
    )

    allowance_for_loan_losses = FinancialStatementItemNode(
        "allowance_for_loan_losses",
        {"2021": 675_000_000, "2022": 720_000_000, "2023": 780_000_000},
    )

    non_performing_loans = FinancialStatementItemNode(
        "non_performing_loans",
        {"2021": 450_000_000, "2022": 480_000_000, "2023": 520_000_000},
    )

    total_securities = FinancialStatementItemNode(
        "total_securities",
        {"2021": 12_000_000_000, "2022": 13_000_000_000, "2023": 14_000_000_000},
    )

    total_assets = FinancialStatementItemNode(
        "total_assets",
        {"2021": 65_000_000_000, "2022": 70_000_000_000, "2023": 75_000_000_000},
    )

    # Liability and equity data
    total_deposits = FinancialStatementItemNode(
        "total_deposits",
        {"2021": 52_000_000_000, "2022": 56_000_000_000, "2023": 60_000_000_000},
    )

    total_shareholders_equity = FinancialStatementItemNode(
        "total_shareholders_equity",
        {"2021": 6_500_000_000, "2022": 7_000_000_000, "2023": 7_500_000_000},
    )

    # Income statement data
    net_interest_income = FinancialStatementItemNode(
        "net_interest_income",
        {"2021": 2_100_000_000, "2022": 2_300_000_000, "2023": 2_600_000_000},
    )

    total_non_interest_income = FinancialStatementItemNode(
        "total_non_interest_income",
        {"2021": 800_000_000, "2022": 850_000_000, "2023": 900_000_000},
    )

    total_non_interest_expense = FinancialStatementItemNode(
        "total_non_interest_expense",
        {"2021": 1_800_000_000, "2022": 1_900_000_000, "2023": 2_000_000_000},
    )

    provision_for_credit_losses = FinancialStatementItemNode(
        "provision_for_credit_losses",
        {"2021": 200_000_000, "2022": 250_000_000, "2023": 300_000_000},
    )

    net_income = FinancialStatementItemNode(
        "net_income", {"2021": 650_000_000, "2022": 700_000_000, "2023": 750_000_000}
    )

    # Regulatory capital data
    common_equity_tier_1 = FinancialStatementItemNode(
        "common_equity_tier_1",
        {"2021": 5_200_000_000, "2022": 5_600_000_000, "2023": 6_000_000_000},
    )

    total_tier_1_capital = FinancialStatementItemNode(
        "total_tier_1_capital",
        {"2021": 5_500_000_000, "2022": 5_900_000_000, "2023": 6_300_000_000},
    )

    total_capital = FinancialStatementItemNode(
        "total_capital",
        {"2021": 6_200_000_000, "2022": 6_600_000_000, "2023": 7_000_000_000},
    )

    total_risk_weighted_assets = FinancialStatementItemNode(
        "total_risk_weighted_assets",
        {"2021": 42_000_000_000, "2022": 45_000_000_000, "2023": 48_000_000_000},
    )

    # Additional calculated nodes for metrics
    average_total_assets = FinancialStatementItemNode(
        "average_total_assets",
        {"2021": 63_000_000_000, "2022": 67_500_000_000, "2023": 72_500_000_000},
    )

    average_total_equity = FinancialStatementItemNode(
        "average_total_equity",
        {"2021": 6_250_000_000, "2022": 6_750_000_000, "2023": 7_250_000_000},
    )

    average_earning_assets = FinancialStatementItemNode(
        "average_earning_assets",
        {"2021": 58_000_000_000, "2022": 62_000_000_000, "2023": 66_000_000_000},
    )

    net_charge_offs = FinancialStatementItemNode(
        "net_charge_offs",
        {"2021": 180_000_000, "2022": 200_000_000, "2023": 250_000_000},
    )

    average_total_loans = FinancialStatementItemNode(
        "average_total_loans",
        {"2021": 44_000_000_000, "2022": 46_500_000_000, "2023": 50_000_000_000},
    )

    # Liquidity-specific data for new metrics
    high_quality_liquid_assets = FinancialStatementItemNode(
        "high_quality_liquid_assets",
        {"2021": 8_000_000_000, "2022": 8_500_000_000, "2023": 9_000_000_000},
    )

    net_cash_outflows_30_days = FinancialStatementItemNode(
        "net_cash_outflows_30_days",
        {"2021": 7_000_000_000, "2022": 7_200_000_000, "2023": 7_500_000_000},
    )

    available_stable_funding = FinancialStatementItemNode(
        "available_stable_funding",
        {"2021": 55_000_000_000, "2022": 59_000_000_000, "2023": 63_000_000_000},
    )

    required_stable_funding = FinancialStatementItemNode(
        "required_stable_funding",
        {"2021": 50_000_000_000, "2022": 53_000_000_000, "2023": 56_000_000_000},
    )

    liquid_assets = FinancialStatementItemNode(
        "liquid_assets",
        {"2021": 15_000_000_000, "2022": 16_000_000_000, "2023": 17_000_000_000},
    )

    return {
        # Assets
        "total_loans": total_loans,
        "allowance_for_loan_losses": allowance_for_loan_losses,
        "non_performing_loans": non_performing_loans,
        "total_securities": total_securities,
        "total_assets": total_assets,
        # Liabilities and equity
        "total_deposits": total_deposits,
        "total_shareholders_equity": total_shareholders_equity,
        # Income statement
        "net_interest_income": net_interest_income,
        "total_non_interest_income": total_non_interest_income,
        "total_non_interest_expense": total_non_interest_expense,
        "provision_for_credit_losses": provision_for_credit_losses,
        "net_income": net_income,
        # Regulatory capital
        "common_equity_tier_1": common_equity_tier_1,
        "total_tier_1_capital": total_tier_1_capital,
        "total_capital": total_capital,
        "total_risk_weighted_assets": total_risk_weighted_assets,
        # Calculated/average items
        "average_total_assets": average_total_assets,
        "average_total_equity": average_total_equity,
        "average_earning_assets": average_earning_assets,
        "net_charge_offs": net_charge_offs,
        "average_total_loans": average_total_loans,
        # Liquidity items
        "high_quality_liquid_assets": high_quality_liquid_assets,
        "net_cash_outflows_30_days": net_cash_outflows_30_days,
        "available_stable_funding": available_stable_funding,
        "required_stable_funding": required_stable_funding,
        "liquid_assets": liquid_assets,
    }


def validate_data_completeness(
    data_nodes: dict[str, FinancialStatementItemNode],
) -> dict:
    """Validate that all required banking data is present."""
    print("\n=== Data Completeness Validation ===")

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
    print(f"Total nodes available: {validation_report['total_nodes']}")
    print(f"Data completeness score: {validation_report['completeness_score']:.1f}%")

    if validation_report["required_missing"]:
        print(f"Missing required nodes ({len(validation_report['required_missing'])}):")
        for node in validation_report["required_missing"]:
            print(f"  - {node}")
    else:
        print("✓ All required nodes present")

    if validation_report["recommended_missing"]:
        print(f"Missing recommended nodes ({len(validation_report['recommended_missing'])}):")
        for node in validation_report["recommended_missing"]:
            print(f"  - {node}")
    else:
        print("✓ All recommended nodes present")

    return validation_report


def analyze_asset_quality(data_nodes: dict[str, FinancialStatementItemNode], period: str) -> dict:
    """Analyze asset quality metrics for the bank."""
    print(f"\n=== Asset Quality Analysis for {period} ===")

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

            print(f"{metric_name}: {value:.2f}% - {interpretation['rating']}")
            print(f"  {interpretation['interpretation_message']}")

        except Exception as e:
            print(f"Could not calculate {metric_name}: {e}")
            results[metric_name] = {"error": str(e)}

    return results


def analyze_capital_adequacy(
    data_nodes: dict[str, FinancialStatementItemNode], period: str
) -> dict:
    """Analyze capital adequacy metrics for the bank."""
    print(f"\n=== Capital Adequacy Analysis for {period} ===")

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

            print(f"{metric_name}: {value:.2f}% - {interpretation['rating']}")
            print(f"  {interpretation['interpretation_message']}")

        except Exception as e:
            print(f"Could not calculate {metric_name}: {e}")
            results[metric_name] = {"error": str(e)}

    return results


def analyze_profitability(data_nodes: dict[str, FinancialStatementItemNode], period: str) -> dict:
    """Analyze profitability metrics for the bank."""
    print(f"\n=== Profitability Analysis for {period} ===")

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

            print(f"{metric_name}: {value:.2f}% - {interpretation['rating']}")
            print(f"  {interpretation['interpretation_message']}")

        except Exception as e:
            print(f"Could not calculate {metric_name}: {e}")
            results[metric_name] = {"error": str(e)}

    return results


def analyze_liquidity(data_nodes: dict[str, FinancialStatementItemNode], period: str) -> dict:
    """Analyze liquidity metrics for the bank."""
    print(f"\n=== Liquidity Analysis for {period} ===")

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

            print(f"{metric_name}: {value:.2f}% - {interpretation['rating']}")
            print(f"  {interpretation['interpretation_message']}")

        except Exception as e:
            print(f"Could not calculate {metric_name}: {e}")
            results[metric_name] = {"error": str(e)}

    return results


def generate_banking_dashboard(
    data_nodes: dict[str, FinancialStatementItemNode], period: str
) -> dict:
    """Generate a comprehensive banking analysis dashboard."""
    print(f"\n{'=' * 60}")
    print(f"COMPREHENSIVE BANKING ANALYSIS DASHBOARD - {period}")
    print(f"{'=' * 60}")

    # Asset Quality Analysis
    asset_quality_results = analyze_asset_quality(data_nodes, period)

    # Capital Adequacy Analysis
    capital_results = analyze_capital_adequacy(data_nodes, period)

    # Profitability Analysis
    profitability_results = analyze_profitability(data_nodes, period)

    # Liquidity Analysis
    liquidity_results = analyze_liquidity(data_nodes, period)

    # Summary Assessment
    print(f"\n=== Overall Assessment for {period} ===")

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

    print("Rating Distribution:")
    for rating, count in rating_counts.items():
        print(f"  {rating}: {count} metrics")

    return {
        "asset_quality": asset_quality_results,
        "capital_adequacy": capital_results,
        "profitability": profitability_results,
        "liquidity": liquidity_results,
        "summary": rating_counts,
    }


def main():
    """Run the banking analysis example with node name validation."""
    print("Banking Analysis Example with Node Name Validation")
    print("=" * 60)

    # Step 1: Demonstrate node name validation
    validate_node_names_example()

    # Step 2: Demonstrate context-aware validation
    context_aware_validation_example()

    # Step 3: Create validated bank data
    validated_data = create_validated_bank_data()

    # Step 4: Create complete sample data (merge with validated data)
    bank_data = create_sample_bank_data()

    # Merge validated data into complete dataset
    bank_data.update(validated_data)

    # Step 5: Validate data completeness
    validation_report = validate_data_completeness(bank_data)

    # Print validation summary
    if validation_report["required_missing"]:
        print(f"⚠️  Warning: {len(validation_report['required_missing'])} required nodes missing")
    if validation_report["completeness_score"] < 80:
        print(
            f"⚠️  Data completeness below recommended threshold: {validation_report['completeness_score']:.1f}%"
        )
    else:
        print(f"✅ Data completeness acceptable: {validation_report['completeness_score']:.1f}%")

    print(f"\n{'=' * 60}")
    print("BANKING ANALYSIS WITH VALIDATED DATA (Node Collection)")
    print(f"{'=' * 60}")

    # Analyze multiple periods using the simple node collection approach
    periods = ["2021", "2022", "2023"]

    all_results = {}
    for period in periods:
        results = generate_banking_dashboard(bank_data, period)
        all_results[period] = results

    # Step 6: Demonstrate comprehensive graph structure
    print(f"\n{'=' * 60}")
    print("COMPREHENSIVE GRAPH STRUCTURE DEMONSTRATION")
    print(f"{'=' * 60}")

    # Create and demonstrate the graph-based approach
    graph_data = create_banking_graph_example()

    # Compare approaches
    print(f"\n{'=' * 60}")
    print("COMPARISON: Node Collection vs Graph Structure")
    print(f"{'=' * 60}")

    print("\n--- Node Collection Approach ---")
    print("✓ Simple dictionary of independent nodes")
    print("✓ Easy to understand and implement")
    print("✓ Direct data access")
    print("✗ No automatic calculations")
    print("✗ No dependency tracking")
    print("✗ Manual metric calculations required")
    print(f"  Total nodes: {len(bank_data)}")
    print("  Calculation nodes: 0")
    print(f"  Data nodes: {len(bank_data)}")

    print("\n--- Graph Structure Approach ---")
    print("✓ Automatic calculations based on dependencies")
    print("✓ Clear relationship modeling")
    print("✓ Dependency tracking and validation")
    print("✓ Consistent calculations across periods")
    print("✗ More complex to set up initially")
    print("✗ Requires understanding of graph concepts")

    # Count different node types in graph
    calculation_nodes = [
        node for node in graph_data.values() if hasattr(node, "inputs") and node.inputs
    ]
    data_nodes = [
        node for node in graph_data.values() if not (hasattr(node, "inputs") and node.inputs)
    ]

    print(f"  Total nodes: {len(graph_data)}")
    print(f"  Calculation nodes: {len(calculation_nodes)}")
    print(f"  Data nodes: {len(data_nodes)}")

    # Trend analysis using simple approach
    print(f"\n{'=' * 60}")
    print("TREND ANALYSIS (Node Collection Approach)")
    print(f"{'=' * 60}")

    # Example: Track key metrics over time
    key_metrics = [
        "non_performing_loan_ratio",
        "common_equity_tier_1_ratio",
        "return_on_assets_(banking)",
        "efficiency_ratio",
        "liquidity_coverage_ratio",
        "deposits_to_loans_ratio",
    ]

    for metric_name in key_metrics:
        print(f"\n{metric_name} Trend:")
        for period in periods:
            try:
                value = calculate_metric(metric_name, bank_data, period)
                print(f"  {period}: {value:.2f}%")
            except Exception as e:
                print(f"  {period}: Error - {e}")

    # Step 7: Demonstrate validation in metric calculation workflow
    print(f"\n{'=' * 60}")
    print("VALIDATION-ENHANCED METRIC CALCULATION")
    print(f"{'=' * 60}")

    # Show how validation helps with metric calculation
    demonstrate_validation_in_metrics(bank_data)

    print(f"\n{'=' * 60}")
    print("Analysis Complete")
    print(f"{'=' * 60}")
    print("\nKey Takeaways:")
    print("1. Node Collection: Simple, direct access, manual calculations")
    print("2. Graph Structure: Automatic calculations, dependency tracking, more complex setup")
    print("3. Both approaches can be validated using the same validation framework")
    print("4. Graph structure provides better consistency and maintainability for complex models")


def demonstrate_validation_in_metrics(
    data_nodes: dict[str, FinancialStatementItemNode],
):
    """Demonstrate how validation helps with metric calculation."""
    print("\n=== Validation-Enhanced Metric Calculation ===")

    # Example: Try to calculate a metric with potentially problematic node names
    test_metric_inputs = {
        "loan_loss_allowance": data_nodes.get("allowance_for_loan_losses"),  # Using alternate name
        "npl": data_nodes.get("non_performing_loans"),  # Using alternate name
        "total_loans": data_nodes.get("total_loans"),  # Standard name
    }

    # Create validator to check metric inputs
    validator = NodeNameValidator(auto_standardize=True)

    print("Checking metric input node names:")
    standardized_inputs = {}
    for input_name, node in test_metric_inputs.items():
        if node is not None:
            standardized_name, is_valid, message = validator.validate_and_standardize(input_name)
            print(f"  Input '{input_name}' -> '{standardized_name}' (Valid: {is_valid})")
            standardized_inputs[standardized_name] = node
        else:
            print(f"  Input '{input_name}' -> Node not found in data")

    # Calculate provision coverage ratio with validated inputs
    if all(
        key in standardized_inputs for key in ["allowance_for_loan_losses", "non_performing_loans"]
    ):
        try:
            # Use standardized names for metric calculation
            metric_data = {
                "allowance_for_loan_losses": standardized_inputs["allowance_for_loan_losses"],
                "non_performing_loans": standardized_inputs["non_performing_loans"],
            }

            provision_coverage = calculate_metric("provision_coverage_ratio", metric_data, "2023")
            print(f"\nCalculated Provision Coverage Ratio (2023): {provision_coverage:.2f}%")

            # Interpret the result
            interpretation = interpret_metric(
                metric_registry.get("provision_coverage_ratio"), provision_coverage
            )
            print(
                f"Interpretation: {interpretation['rating']} - {interpretation['interpretation_message']}"
            )

        except Exception as e:
            print(f"Error calculating metric: {e}")

    # Show validation benefits
    print("\n--- Validation Benefits ---")
    print("1. Automatic standardization of node names")
    print("2. Early detection of missing or misnamed data")
    print("3. Consistent metric calculations across different data sources")
    print("4. Improved data quality and reliability")
    print("5. Better error messages and debugging information")


def create_banking_graph_example() -> dict[str, FinancialStatementItemNode]:
    """Create a comprehensive banking graph with calculation nodes and relationships.

    This demonstrates the difference between a simple collection of nodes
    and a true graph structure with dependencies and calculations.
    """
    print("\n=== Creating Comprehensive Banking Graph ===")

    # 1. Base data nodes (leaf nodes in the graph)
    print("Creating base data nodes...")

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
    print("Creating calculation nodes with dependencies...")

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
        formula_func=lambda cash, securities, loans, other: cash + securities + loans + other,
        description="Total bank assets",
    )

    # 3. Create ratio calculation nodes
    print("Creating ratio calculation nodes...")

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
    print("Demonstrating graph calculations...")

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

    print(f"\nCalculated values for {period}:")
    for name, value in calculated_values.items():
        if "Ratio" in name or "Margin" in name:
            print(f"  {name}: {value:.2f}%")
        else:
            print(f"  {name}: ${value:,.0f}")

    # 5. Show graph dependencies
    print("\nGraph Dependencies:")

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

    print(f"  total_assets depends on: {get_input_names(total_assets)}")
    print(f"  net_interest_income depends on: {get_input_names(net_interest_income)}")
    print(f"  total_interest_income depends on: {get_input_names(total_interest_income)}")
    print(f"  total_securities depends on: {get_input_names(total_securities)}")
    print(f"  net_loans depends on: {get_input_names(net_loans)}")

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
