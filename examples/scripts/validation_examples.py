"""Examples of node name validation for different use cases.

This module demonstrates how to handle sub-nodes, formula nodes, and
custom nodes while maintaining standard naming where appropriate.
"""

from fin_statement_model.io.node_name_validator import NodeNameValidator
from fin_statement_model.io.context_aware_validator import ContextAwareNodeValidator
from fin_statement_model.core.nodes import (
    FinancialStatementItemNode,
    FormulaCalculationNode,
)


def example_basic_validation():
    """Example: Basic validation with flexibility for sub-nodes."""
    # Create a flexible validator (default settings)
    validator = NodeNameValidator(
        strict_mode=False,  # Allow non-standard names
        auto_standardize=True,  # Standardize known alternates
        warn_on_non_standard=True,  # Warn about non-standard names
    )

    # Example node names including sub-nodes
    node_names = [
        # Standard names
        "revenue",
        "cost_of_goods_sold",
        "operating_income",
        # Alternate names (will be standardized)
        "sales",  # -> revenue
        "cogs",  # -> cost_of_goods_sold
        # Sub-nodes (allowed, with warnings)
        "revenue_north_america",
        "revenue_europe",
        "revenue_asia_pacific",
        "revenue_product_a",
        "revenue_product_b",
        # Time-based sub-nodes
        "revenue_q1",
        "revenue_q2",
        "revenue_2023",
        "revenue_2024",
        # Formula nodes
        "gross_margin_pct",
        "operating_margin_ratio",
        "revenue_growth_yoy",
    ]

    print("=== Basic Validation Example ===")
    for name in node_names:
        std_name, is_valid, message = validator.validate_and_standardize(name)
        print(f"{name:30} -> {std_name:30} Valid: {is_valid} ({message})")


def example_context_aware_validation():
    """Example: Context-aware validation that understands relationships."""
    # Create context-aware validator
    validator = ContextAwareNodeValidator(
        strict_mode=False, validate_subnodes=True, validate_formulas=True
    )

    # Example validations with context
    test_cases = [
        # (name, node_type, parent_nodes)
        ("revenue", "data", None),
        ("revenue_north_america", "data", None),
        ("revenue_q1_2024", "data", None),
        ("gross_profit_margin", "formula", ["gross_profit", "revenue"]),
        ("ebitda_adjustment", "calculation", ["ebitda"]),
        ("custom_metric_123", "calculation", None),
    ]

    print("\n=== Context-Aware Validation Example ===")
    for name, node_type, parents in test_cases:
        std_name, is_valid, message, category = validator.validate_node(
            name, node_type=node_type, parent_nodes=parents
        )
        print(f"{name:30} Category: {category:20} Valid: {is_valid}")
        print(f"   Message: {message}")


def example_graph_building_with_validation():
    """Example: Building a graph with mixed node names."""
    from fin_statement_model.core.graph import Graph

    # Create a graph
    graph = Graph()

    # Create a flexible validator
    validator = NodeNameValidator(strict_mode=False)

    # Regional revenue nodes (sub-nodes)
    regional_revenues = {
        "revenue_north_america": [100, 110, 120],
        "revenue_europe": [80, 85, 90],
        "revenue_asia_pacific": [60, 70, 80],
        "revenue_other": [20, 22, 25],
    }

    # Add regional revenue nodes
    regional_nodes = {}
    for name, values in regional_revenues.items():
        # Validate but don't standardize (we want to keep the regional detail)
        _, is_valid, _ = validator.validate_and_standardize(name)
        if is_valid:
            node = FinancialStatementItemNode(name=name, values=values)
            graph.add_node(node)
            regional_nodes[name] = node

    # Add total revenue node (sums up regions) - Fixed to use dict inputs
    total_revenue = FormulaCalculationNode(
        name="revenue",  # Standard name
        inputs=regional_nodes,  # Dictionary of name -> node
        formula="revenue_north_america + revenue_europe + revenue_asia_pacific + revenue_other",
    )
    graph.add_node(total_revenue)

    # Add COGS and gross profit
    cogs = FinancialStatementItemNode(
        name="cost_of_goods_sold",  # Standard name
        values=[150, 160, 170],
    )
    graph.add_node(cogs)

    gross_profit = FormulaCalculationNode(
        name="gross_profit",  # Standard name
        inputs={"revenue": total_revenue, "cost_of_goods_sold": cogs},
        formula="revenue - cost_of_goods_sold",
    )
    graph.add_node(gross_profit)

    # Add a margin calculation (formula node)
    gross_margin = FormulaCalculationNode(
        name="gross_profit_margin",  # Formula pattern node
        inputs={"gross_profit": gross_profit, "revenue": total_revenue},
        formula="gross_profit / revenue * 100",
    )
    graph.add_node(gross_margin)

    print("\n=== Graph Building Example ===")
    print(f"Total nodes in graph: {len(graph.nodes)}")
    print("\nNodes by type:")

    # Validate all nodes with context
    context_validator = ContextAwareNodeValidator()
    results = context_validator.validate_graph_nodes(list(graph.nodes.values()))

    for category, nodes in results.items():
        if nodes:
            print(f"\n{category.upper()}:")
            for node_info in nodes:
                print(f"  - {node_info['name']}")


def example_strict_vs_flexible():
    """Example: Difference between strict and flexible validation."""
    # Strict validator - only allows standard names
    strict_validator = NodeNameValidator(strict_mode=True, auto_standardize=True)

    # Flexible validator - allows custom names
    flexible_validator = NodeNameValidator(strict_mode=False, auto_standardize=True)

    test_names = [
        "revenue",  # Standard
        "sales",  # Alternate for revenue
        "revenue_europe",  # Sub-node
        "custom_adjustment",  # Custom
    ]

    print("\n=== Strict vs Flexible Validation ===")
    print("Name                    | Strict Valid | Flexible Valid")
    print("-" * 55)

    for name in test_names:
        _, strict_valid, _ = strict_validator.validate_and_standardize(name)
        _, flex_valid, _ = flexible_validator.validate_and_standardize(name)
        print(f"{name:23} | {strict_valid!s:12} | {flex_valid!s:12}")


def example_reader_integration():
    """Example: Using validation in a data reader."""
    # Simulated data from Excel/CSV
    raw_data = {
        "Sales": [1000, 1100, 1200],  # Will standardize to revenue
        "Revenue - North America": [600, 650, 700],  # Sub-node
        "Revenue - Europe": [400, 450, 500],  # Sub-node
        "Cost of Sales": [600, 650, 700],  # Will standardize to COGS
        "Gross Margin %": [40, 41, 42],  # Formula node
        "EBITDA Adjustment": [10, 12, 15],  # Custom node
    }

    # Create validator for reader
    validator = NodeNameValidator(strict_mode=False, auto_standardize=True)

    print("\n=== Reader Integration Example ===")
    print("Original Name           | Standardized Name      | Category")
    print("-" * 70)

    # Process data with validation
    processed_data = {}
    for original_name, values in raw_data.items():
        # Clean the name (remove extra spaces, normalize)
        clean_name = original_name.lower().replace(" - ", "_").replace(" ", "_")

        # Validate and potentially standardize
        std_name, is_valid, message = validator.validate_and_standardize(clean_name)

        # Determine category
        if "sales" in clean_name and std_name == "revenue":
            category = "standardized"
        elif "_" in std_name and any(region in std_name for region in ["north", "europe"]):
            category = "sub-node"
        elif "%" in original_name or "margin" in std_name:
            category = "formula"
        else:
            category = "custom"

        processed_data[std_name] = values
        print(f"{original_name:23} | {std_name:23} | {category}")

    # Show validation summary
    summary = validator.get_validation_summary()
    print("\nValidation Summary:")
    print(f"  Standard names: {summary['standard_names']}")
    print(f"  Alternate names: {summary['alternate_names']}")
    print(f"  Unrecognized names: {summary['unrecognized_names']}")


if __name__ == "__main__":
    # Run all examples
    example_basic_validation()
    example_context_aware_validation()
    example_graph_building_with_validation()
    example_strict_vs_flexible()
    example_reader_integration()
