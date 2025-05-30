"""Simple Banking Analysis Example.

This example demonstrates:
1. Node name validation for banking-specific terms
2. Building a basic banking graph with validated nodes
3. Creating a banking-specific statement configuration
4. Analyzing key banking metrics with proper interpretation
5. Using centralized configuration for formatting and forecasting
"""

import logging

from fin_statement_model import get_config, update_config
from fin_statement_model.core.graph import Graph
from fin_statement_model.core.metrics import (
    metric_registry,
    interpret_metric,
    calculate_metric,
)
from fin_statement_model.io.validation import UnifiedNodeValidator
from fin_statement_model.statements import create_statement_dataframe

# Get configuration
config = get_config()

# Configure logging
logger = logging.getLogger(__name__)

# Banking-specific configuration overrides
banking_config = {
    "display": {
        "default_units": "USD Millions",
        "scale_factor": 0.000001,  # Convert to millions
        "default_currency_format": ",.1f",
    },
    "validation": {
        "strict_mode": True,  # Banks need strict validation
        "warn_on_non_standard": True,
    },
}
update_config(banking_config)


def step_1_validate_node_names() -> dict[str, str]:
    """Step 1: Validate banking-specific node names.

    Returns:
        Dictionary mapping original names to standardized names
    """
    logger.info("=" * 60)
    logger.info("STEP 1: NODE NAME VALIDATION")
    logger.info("=" * 60)

    # Create validator using config settings
    validator = UnifiedNodeValidator(
        strict_mode=config.validation.strict_mode,
        auto_standardize=config.validation.auto_standardize_names,
    )

    # Common banking terms that need validation
    banking_terms = [
        # Standard banking items
        "interest_income",
        "interest_expense",
        "net_interest_income",
        "non_interest_income",
        "loan_loss_provision",
        # Assets
        "loans_and_advances",
        "securities_portfolio",
        "cash_and_due_from_banks",
        # Liabilities
        "customer_deposits",
        "wholesale_funding",
        "subordinated_debt",
        # Regulatory metrics
        "tier_1_capital",
        "risk_weighted_assets",
        "common_equity_tier_1",
    ]

    logger.info("Validating banking terminology...")
    mappings = {}

    for term in banking_terms:
        result = validator.validate(term)
        mappings[term] = result.standardized_name
        if result.is_valid:
            logger.info(f"✓ {term} -> {result.standardized_name}")
        else:
            logger.warning(f"✗ {term}: {result.message}")

    return mappings


def create_banking_statement_config() -> str:
    """Create a YAML configuration for a banking income statement."""
    config_yaml = """
id: banking_income_statement
name: Banking Income Statement
description: Standard income statement structure for banks

sections:
  - id: interest_income_section
    name: Interest Income
    items:
      - type: line_item
        id: loans_interest
        name: Interest on Loans
        node_id: interest_income_loans

      - type: line_item
        id: securities_interest
        name: Interest on Securities
        node_id: interest_income_securities

      - type: calculated
        id: total_interest_income
        name: Total Interest Income
        calculation:
          type: addition
          inputs: ["loans_interest", "securities_interest"]

  - id: interest_expense_section
    name: Interest Expense
    items:
      - type: line_item
        id: deposits_interest
        name: Interest on Deposits
        node_id: interest_expense_deposits
        sign_convention: -1

      - type: line_item
        id: borrowings_interest
        name: Interest on Borrowings
        node_id: interest_expense_borrowings
        sign_convention: -1

      - type: calculated
        id: total_interest_expense
        name: Total Interest Expense
        calculation:
          type: addition
          inputs: ["deposits_interest", "borrowings_interest"]

  - id: net_interest_section
    name: Net Interest Income
    items:
      - type: calculated
        id: net_interest_income
        name: Net Interest Income
        calculation:
          type: addition
          inputs: ["total_interest_income", "total_interest_expense"]

  - id: non_interest_section
    name: Non-Interest Income
    items:
      - type: line_item
        id: fee_income
        name: Fee and Commission Income
        node_id: fee_income

      - type: line_item
        id: trading_income
        name: Trading Income
        node_id: trading_income

      - type: calculated
        id: total_non_interest_income
        name: Total Non-Interest Income
        calculation:
          type: addition
          inputs: ["fee_income", "trading_income"]

  - id: operating_income_section
    name: Operating Income
    items:
      - type: calculated
        id: total_operating_income
        name: Total Operating Income
        calculation:
          type: addition
          inputs: ["net_interest_income", "total_non_interest_income"]

      - type: line_item
        id: loan_loss_provision
        name: Loan Loss Provision
        node_id: loan_loss_provision
        sign_convention: -1

      - type: calculated
        id: operating_income_after_provisions
        name: Operating Income After Provisions
        calculation:
          type: addition
          inputs: ["total_operating_income", "loan_loss_provision"]

  - id: expenses_section
    name: Operating Expenses
    items:
      - type: line_item
        id: staff_costs
        name: Staff Costs
        node_id: staff_costs
        sign_convention: -1

      - type: line_item
        id: other_operating_expenses
        name: Other Operating Expenses
        node_id: other_operating_expenses
        sign_convention: -1

      - type: calculated
        id: total_operating_expenses
        name: Total Operating Expenses
        calculation:
          type: addition
          inputs: ["staff_costs", "other_operating_expenses"]

  - id: net_income_section
    name: Net Income
    items:
      - type: calculated
        id: pre_tax_income
        name: Income Before Tax
        calculation:
          type: addition
          inputs: ["operating_income_after_provisions", "total_operating_expenses"]

      - type: line_item
        id: income_tax
        name: Income Tax
        node_id: income_tax
        sign_convention: -1

      - type: calculated
        id: net_income
        name: Net Income
        calculation:
          type: addition
          inputs: ["pre_tax_income", "income_tax"]
"""
    return config_yaml


def step_2_build_graph() -> tuple[Graph, str]:
    """Step 2: Build a banking graph with sample data.

    Returns:
        Tuple of (Graph, period) for analysis
    """
    logger.info("\n" + "=" * 60)
    logger.info("STEP 2: BUILDING BANKING GRAPH")
    logger.info("=" * 60)

    # Sample banking data (in actual dollars, will be scaled by config)
    banking_data = {
        # Interest Income
        "interest_income_loans": {
            "2021": 8500000000,  # $8.5 billion
            "2022": 9200000000,  # $9.2 billion
            "2023": 10500000000,  # $10.5 billion
        },
        "interest_income_securities": {
            "2021": 1200000000,
            "2022": 1400000000,
            "2023": 1800000000,
        },
        # Interest Expense
        "interest_expense_deposits": {
            "2021": 2100000000,
            "2022": 2800000000,
            "2023": 4200000000,
        },
        "interest_expense_borrowings": {
            "2021": 800000000,
            "2022": 950000000,
            "2023": 1200000000,
        },
        # Non-Interest Income
        "fee_income": {"2021": 3200000000, "2022": 3400000000, "2023": 3600000000},
        "trading_income": {"2021": 1100000000, "2022": 800000000, "2023": 1200000000},
        # Provisions and Expenses
        "loan_loss_provision": {
            "2021": 800000000,
            "2022": 1200000000,
            "2023": 900000000,
        },
        "staff_costs": {"2021": 4500000000, "2022": 4700000000, "2023": 4900000000},
        "other_operating_expenses": {
            "2021": 2800000000,
            "2022": 2900000000,
            "2023": 3100000000,
        },
        "income_tax": {"2021": 1200000000, "2022": 1050000000, "2023": 1400000000},
        # Balance Sheet items for ratios
        "total_assets": {
            "2021": 280000000000,  # $280 billion
            "2022": 295000000000,
            "2023": 310000000000,
        },
        "total_loans": {
            "2021": 180000000000,
            "2022": 190000000000,
            "2023": 205000000000,
        },
        "total_deposits": {
            "2021": 220000000000,
            "2022": 235000000000,
            "2023": 248000000000,
        },
        "shareholders_equity": {
            "2021": 28000000000,
            "2022": 29500000000,
            "2023": 31000000000,
        },
        "tier_1_capital": {
            "2021": 25000000000,
            "2022": 26500000000,
            "2023": 28000000000,
        },
        "risk_weighted_assets": {
            "2021": 195000000000,
            "2022": 205000000000,
            "2023": 215000000000,
        },
    }

    # Collect all periods from the data
    all_periods = set()
    for periods_data in banking_data.values():
        all_periods.update(periods_data.keys())
    # Create graph with periods
    graph = Graph(periods=sorted(all_periods))
    logger.info(f"Created graph with periods: {graph.periods}")

    # Add nodes to graph using validated names
    from fin_statement_model.core.nodes import FinancialStatementItemNode

    logger.info(f"Adding banking data nodes (values in {config.display.default_units})...")
    for node_name, periods_data in banking_data.items():
        node = FinancialStatementItemNode(node_name, {})  # Initialize with empty values
        for period, value in periods_data.items():
            node.set_value(period, value)
        graph.add_node(node)

        # Show sample value with configured formatting
        sample_value = periods_data.get("2023", 0)
        scaled_value = sample_value * config.display.scale_factor
        logger.info(
            f"  Added {node_name}: 2023 = {scaled_value:{config.display.default_currency_format}}"
        )

    # Add calculated nodes based on statement config
    from fin_statement_model.core.nodes import CalculationNode
    from fin_statement_model.core.calculations import AdditionCalculation

    # Net Interest Income
    nii_node = CalculationNode(
        "net_interest_income",
        inputs=[
            graph.get_node("interest_income_loans"),
            graph.get_node("interest_income_securities"),
            graph.get_node("interest_expense_deposits"),
            graph.get_node("interest_expense_borrowings"),
        ],
        calculation=AdditionCalculation(),
    )
    graph.add_node(nii_node)

    # Total Operating Income
    operating_income = CalculationNode(
        "total_operating_income",
        inputs=[
            nii_node,  # Use the node object directly
            graph.get_node("fee_income"),
            graph.get_node("trading_income"),
        ],
        calculation=AdditionCalculation(),
    )
    graph.add_node(operating_income)

    # Add more nodes for metric calculations
    # Total Non-Interest Income (alias for fee_income + trading_income)
    total_non_interest_income = CalculationNode(
        "total_non_interest_income",
        inputs=[
            graph.get_node("fee_income"),
            graph.get_node("trading_income"),
        ],
        calculation=AdditionCalculation(),
    )
    graph.add_node(total_non_interest_income)

    # Net Income calculation (simplified)
    # This is very simplified - in reality would need pre-tax income, etc.
    from fin_statement_model.core.calculations import SubtractionCalculation

    # Operating expenses
    total_operating_expenses = CalculationNode(
        "total_operating_expenses",
        inputs=[
            graph.get_node("staff_costs"),
            graph.get_node("other_operating_expenses"),
            graph.get_node("loan_loss_provision"),
        ],
        calculation=AdditionCalculation(),
    )
    graph.add_node(total_operating_expenses)
    # Pre-tax income
    pre_tax_income = CalculationNode(
        "pre_tax_income",
        inputs=[
            operating_income,
            total_operating_expenses,
        ],
        calculation=SubtractionCalculation(),
    )
    graph.add_node(pre_tax_income)
    # Net income
    net_income = CalculationNode(
        "net_income",
        inputs=[
            pre_tax_income,
            graph.get_node("income_tax"),
        ],
        calculation=SubtractionCalculation(),
    )
    graph.add_node(net_income)

    # Add total_equity as a copy of shareholders_equity for metric compatibility
    total_equity = FinancialStatementItemNode("total_equity", {})
    for period, value in banking_data["shareholders_equity"].items():
        total_equity.set_value(period, value)
    graph.add_node(total_equity)

    return graph, "2023"


def step_3_analyze_structure(graph: Graph) -> None:
    """Step 3: Analyze the graph structure."""
    logger.info("\n" + "=" * 60)
    logger.info("STEP 3: ANALYZING GRAPH STRUCTURE")
    logger.info("=" * 60)

    logger.info(f"Total nodes: {len(graph.nodes)}")
    logger.info(f"Periods: {sorted(graph.periods)}")

    # Count node types
    from fin_statement_model.core.nodes import (
        FinancialStatementItemNode,
        CalculationNode,
    )

    item_nodes = sum(1 for n in graph.nodes.values() if isinstance(n, FinancialStatementItemNode))
    calc_nodes = sum(1 for n in graph.nodes.values() if isinstance(n, CalculationNode))

    logger.info("\nNode types:")
    logger.info(f"  Item nodes: {item_nodes}")
    logger.info(f"  Calculation nodes: {calc_nodes}")

    # Show dependencies
    logger.info("\nKey calculations:")
    for node in graph.nodes.values():
        if isinstance(node, CalculationNode):
            input_names = [input_node.name for input_node in node.inputs]
            logger.info(f"  {node.name} = f({', '.join(input_names)})")


def analyze_key_banking_metrics(graph: Graph, period: str = "2023") -> None:
    """Analyze key banking metrics using the metrics registry."""
    logger.info("\n" + "=" * 60)
    logger.info("STEP 4: ANALYZING KEY BANKING METRICS")
    logger.info("=" * 60)

    # Key banking metrics to calculate
    banking_metrics = [
        "net_interest_margin",
        "efficiency_ratio",
        "cost_to_income_ratio",
        "return_on_assets",
        "return_on_equity",
        "tier_1_capital_ratio",
        "loan_to_deposit_ratio",
    ]

    logger.info(f"Calculating metrics for {period}...")
    logger.info(f"Values displayed in {config.display.default_units}\n")

    # Get all nodes from graph as a dictionary
    data_nodes = graph.nodes

    for metric_name in banking_metrics:
        try:
            # Check if metric exists
            if metric_name not in metric_registry:
                logger.warning(f"⚠ {metric_name}: Not in registry")
                continue

            # Get metric definition
            metric_def = metric_registry.get(metric_name)

            # Try to calculate value using calculate_metric
            try:
                value = calculate_metric(metric_name, data_nodes, period)
            except ValueError as ve:
                # Log missing inputs and skip this metric
                logger.info(f"Cannot calculate {metric_def.name}: {ve}")
                continue

            # Format based on metric type
            formatted_value = (
                f"{value * 100:.1f}%"
                if getattr(metric_def, "units", None) == "%"
                else f"{value:.2f}"
            )

            # Interpret the metric value
            interpretation = interpret_metric(metric_def, value)

            # Display results
            logger.info(f"{metric_def.name}:")
            logger.info(f"  Value: {formatted_value}")
            # Handle interpretation as dict or object
            if isinstance(interpretation, dict):
                logger.info(f"  Rating: {interpretation.get('rating', 'N/A')}")
                logger.info(
                    f"  Interpretation: {interpretation.get('message', 'No interpretation available')}"
                )
                if interpretation.get("peer_comparison"):
                    logger.info(f"  Peer Comparison: {interpretation['peer_comparison']}")
            else:
                logger.info(f"  Rating: {interpretation.rating}")
                logger.info(f"  Interpretation: {interpretation.message}")
                if interpretation.peer_comparison:
                    logger.info(f"  Peer Comparison: {interpretation.peer_comparison}")

            logger.info("")

        except Exception:
            logger.exception(f"❌ {metric_name}")


def explore_metrics_registry() -> None:
    """Explore available banking metrics in the registry."""
    logger.info("\n" + "=" * 60)
    logger.info("STEP 5: EXPLORING METRICS REGISTRY")
    logger.info("=" * 60)

    # Get all metrics
    all_metrics = metric_registry.list_metrics()

    # Filter banking-specific metrics
    banking_keywords = ["bank", "loan", "deposit", "tier", "capital", "interest"]
    banking_metrics = [
        m for m in all_metrics if any(keyword in m.lower() for keyword in banking_keywords)
    ]

    logger.info(f"Found {len(banking_metrics)} banking-related metrics:")
    for metric_name in sorted(banking_metrics):
        try:
            metric_def = metric_registry.get(metric_name)
            logger.info(f"  • {metric_def.name} ({metric_name})")
            if metric_def.description:
                logger.info(f"    {metric_def.description}")
        except Exception:
            logger.info(f"  • {metric_name} (definition error)")


def main() -> None:
    """Run the complete banking analysis example."""
    # Configure logging to ensure we see INFO messages
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info("=" * 80)
    logger.info("SIMPLE BANKING ANALYSIS EXAMPLE")
    logger.info("=" * 80)
    logger.info("\nUsing configuration:")
    logger.info(f"  Units: {config.display.default_units}")
    logger.info(f"  Format: {config.display.default_currency_format}")
    logger.info(f"  Validation: {'Strict' if config.validation.strict_mode else 'Flexible'}")

    # Step 1: Validate node names
    step_1_validate_node_names()

    # Step 2: Build graph
    graph, analysis_period = step_2_build_graph()

    # Step 3: Analyze structure
    step_3_analyze_structure(graph)

    # Step 4: Calculate metrics
    analyze_key_banking_metrics(graph, analysis_period)

    # Step 5: Explore registry
    explore_metrics_registry()

    # Show statement creation
    logger.info("\n" + "=" * 60)
    logger.info("CREATING FORMATTED STATEMENT")
    logger.info("=" * 60)

    try:
        # Save config to temp file
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(create_banking_statement_config())
            config_path = f.name

        # Create statement
        statement_df = create_statement_dataframe(
            graph=graph,
            config_path_or_dir=config_path,
            format_kwargs={
                "number_format": config.display.default_currency_format,
                "should_apply_signs": True,
                "include_empty_items": not config.display.hide_zero_rows,
            },
        )

        logger.info("Banking Income Statement:")
        logger.info(statement_df.to_string(index=False))

        # Clean up
        import os

        os.unlink(config_path)

    except Exception:
        logger.exception("Could not create statement")

    logger.info("\n" + "=" * 80)
    logger.info("EXAMPLE COMPLETE")
    logger.info("=" * 80)
    logger.info("\nKey Takeaways:")
    logger.info("• Node validation ensures consistent naming across the model")
    logger.info("• Banking metrics have specific interpretations and thresholds")
    logger.info("• Statement configurations define presentation structure")
    logger.info("• The metrics registry provides comprehensive analysis tools")
    logger.info("• Centralized config controls formatting, validation, and display")


if __name__ == "__main__":
    main()
