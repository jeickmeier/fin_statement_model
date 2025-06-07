"""Example demonstrating UnifiedNodeValidator integration with statement processing.

This example shows how to use the enhanced statement configuration and building
capabilities that include node ID validation using the UnifiedNodeValidator.
"""

from fin_statement_model.core.graph import Graph
from fin_statement_model.statements import (
    StatementConfig,
    create_validated_statement_config,
    create_validated_statement_builder,
    validate_statement_config_with_nodes,
)
from fin_statement_model.io.validation import UnifiedNodeValidator


def example_basic_node_validation():
    """Demonstrate basic node validation during statement configuration."""
    print("=== Basic Node Validation Example ===")

    # Example configuration with mixed node ID quality
    config_data = {
        "id": "sample_income_statement",
        "name": "Sample Income Statement",
        "description": "Demonstrates node validation",
        "sections": [
            {
                "id": "revenue_section",
                "name": "Revenue",
                "type": "section",
                "items": [
                    {
                        "type": "line_item",
                        "id": "revenue",  # Standard node name - should pass
                        "name": "Total Revenue",
                        "node_id": "revenue",
                    },
                    {
                        "type": "line_item",
                        "id": "sales",  # Alternate name for revenue - should be standardized
                        "name": "Sales Revenue",
                        "node_id": "sales",
                    },
                    {
                        "type": "line_item",
                        "id": "custom_revenue_stream",  # Custom name - should generate warning
                        "name": "Custom Revenue Stream",
                        "node_id": "custom_rev_123",
                    },
                ],
            },
            {
                "id": "expenses_section",
                "name": "Expenses",
                "type": "section",
                "items": [
                    {
                        "type": "line_item",
                        "id": "cogs",  # Standard name - should pass
                        "name": "Cost of Goods Sold",
                        "node_id": "cogs",
                    },
                    {
                        "type": "calculated",
                        "id": "gross_profit",  # Standard name - should pass
                        "name": "Gross Profit",
                        "calculation": {
                            "type": "subtraction",
                            "inputs": ["revenue", "cogs"],  # Both standard names
                        },
                    },
                ],
            },
        ],
    }

    print("\n--- Testing Non-Strict Mode (Warnings Only) ---")
    config = StatementConfig(
        config_data,
        enable_node_validation=True,
        node_validation_strict=False,  # Warnings only
    )

    errors = config.validate_config()
    print(f"Validation errors: {len(errors)}")
    for error in errors:
        print(f"  - {error}")

    if config.model:
        print("✅ Configuration successfully validated and parsed")
        print(f"   Statement ID: {config.model.id}")
        print(f"   Sections: {len(config.model.sections)}")

    print("\n--- Testing Strict Mode ---")
    strict_config = StatementConfig(
        config_data,
        enable_node_validation=True,
        node_validation_strict=True,  # Errors for non-standard names
    )

    strict_errors = strict_config.validate_config()
    print(f"Strict validation errors: {len(strict_errors)}")
    for error in strict_errors:
        print(f"  - {error}")

    if strict_config.model:
        print("✅ Strict validation passed")
    else:
        print("❌ Strict validation failed")


def example_custom_validator_configuration():
    """Demonstrate using a custom UnifiedNodeValidator configuration."""
    print("\n=== Custom Validator Configuration Example ===")

    # Create a custom validator with specific settings
    custom_validator = UnifiedNodeValidator(
        strict_mode=False,
        auto_standardize=True,  # Convert alternate names to standard
        warn_on_non_standard=True,
        enable_patterns=True,  # Enable pattern recognition for subnodes
    )

    config_data = {
        "id": "quarterly_statement",
        "name": "Quarterly Statement",
        "sections": [
            {
                "id": "quarterly_revenue",
                "name": "Quarterly Revenue",
                "type": "section",
                "items": [
                    {
                        "type": "line_item",
                        "id": "revenue_q1",  # Pattern: revenue + quarterly suffix
                        "name": "Q1 Revenue",
                        "node_id": "revenue_q1",
                    },
                    {
                        "type": "line_item",
                        "id": "sales_q1",  # Alternate name + quarterly pattern
                        "name": "Q1 Sales",
                        "node_id": "sales_q1",
                    },
                    {
                        "type": "calculated",
                        "id": "revenue_growth",  # Pattern: base + growth suffix
                        "name": "Revenue Growth",
                        "calculation": {
                            "type": "percentage_change",
                            "inputs": ["revenue_q1", "revenue_q0"],
                        },
                    },
                ],
            },
        ],
    }

    config = StatementConfig(
        config_data,
        enable_node_validation=True,
        node_validation_strict=False,
        node_validator=custom_validator,
    )

    errors = config.validate_config()
    print(f"Custom validation errors: {len(errors)}")
    for error in errors:
        print(f"  - {error}")

    if config.model:
        print("✅ Custom validation completed successfully")


def example_convenience_functions():
    """Demonstrate the convenience functions for easier usage."""
    print("\n=== Convenience Functions Example ===")

    config_data = {
        "id": "balance_sheet",
        "name": "Balance Sheet",
        "sections": [
            {
                "id": "assets",
                "name": "Assets",
                "type": "section",
                "items": [
                    {
                        "type": "line_item",
                        "id": "cash",  # Standard name
                        "name": "Cash and Cash Equivalents",
                        "standard_node_ref": "cash",  # Using standard node reference
                    },
                    {
                        "type": "line_item",
                        "id": "receivables",  # Standard name
                        "name": "Accounts Receivable",
                        "node_id": "accounts_receivable",
                    },
                ],
                "subtotal": {
                    "type": "subtotal",
                    "id": "total_current_assets",
                    "name": "Total Current Assets",
                    "items_to_sum": ["cash", "receivables"],
                },
            },
        ],
    }

    print("\n--- Using create_validated_statement_config ---")
    config = create_validated_statement_config(
        config_data,
        enable_node_validation=True,
        strict_mode=False,  # Warnings only
    )

    errors = config.validate_config()
    print(f"Validation errors: {len(errors)}")

    print("\n--- Using create_validated_statement_builder ---")
    builder = create_validated_statement_builder(
        enable_node_validation=True,
        strict_mode=False,
    )

    if config.model:
        statement = builder.build(config)
        print(f"✅ Statement built successfully: {statement.name}")
        print(f"   Sections: {len(statement.sections)}")

        # Show the sections and items
        for section in statement.sections:
            print(f"   Section: {section.name}")
            for item in section.items:
                print(f"     - {item.name} (ID: {item.id})")

    print("\n--- Using validate_statement_config_with_nodes ---")
    validated_config, validation_errors = validate_statement_config_with_nodes(
        config_data,
        strict_mode=False,
        auto_standardize=True,
    )

    print(f"High-level validation errors: {len(validation_errors)}")
    if not validation_errors:
        print("✅ High-level validation passed")


def example_invalid_configuration():
    """Demonstrate validation with invalid node IDs."""
    print("\n=== Invalid Configuration Example ===")

    # Configuration with various invalid node IDs
    invalid_config_data = {
        "id": "bad@statement!",  # Invalid characters
        "name": "Invalid Statement",
        "sections": [
            {
                "id": "section with spaces",  # Spaces not allowed
                "name": "Invalid Section",
                "type": "section",
                "items": [
                    {
                        "type": "line_item",
                        "id": "node#with$symbols",  # Invalid characters
                        "name": "Invalid Node",
                        "node_id": "another_bad_node!!!",  # Invalid characters
                    },
                    {
                        "type": "calculated",
                        "id": "123_starts_with_number",  # Bad practice
                        "name": "Numeric Start",
                        "calculation": {
                            "type": "addition",
                            "inputs": ["input@1", "input@2"],  # Invalid characters
                        },
                    },
                ],
            },
        ],
    }

    print("\n--- Testing Invalid Config in Strict Mode ---")
    try:
        config = StatementConfig(
            invalid_config_data,
            enable_node_validation=True,
            node_validation_strict=True,
        )

        errors = config.validate_config()
        print(f"Validation errors found: {len(errors)}")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")

        if errors:
            print("❌ Validation failed as expected due to invalid node IDs")

    except Exception as e:
        print(f"Exception during validation: {e}")

    print("\n--- Testing Invalid Config in Non-Strict Mode ---")
    config = StatementConfig(
        invalid_config_data,
        enable_node_validation=True,
        node_validation_strict=False,  # Warnings only
    )

    errors = config.validate_config()
    print(f"Validation completed with {len(errors)} errors (warnings logged)")

    if config.model:
        print("✅ Non-strict validation allowed processing to continue")
    else:
        print("❌ Even non-strict validation failed")


def example_integration_with_graph():
    """Demonstrate integration with actual graph operations."""
    print("\n=== Graph Integration Example ===")

    # Create a sample graph
    graph = Graph()
    graph.add_financial_statement_item("revenue", {"2023": 100000, "2024": 120000})
    graph.add_financial_statement_item("cogs", {"2023": 60000, "2024": 70000})
    graph.add_financial_statement_item(
        "operating_expenses", {"2023": 25000, "2024": 30000}
    )

    config_data = {
        "id": "income_statement",
        "name": "Income Statement",
        "sections": [
            {
                "id": "revenue_section",
                "name": "Revenue",
                "type": "section",
                "items": [
                    {
                        "type": "line_item",
                        "id": "revenue",
                        "name": "Total Revenue",
                        "node_id": "revenue",
                    },
                ],
            },
            {
                "id": "expenses_section",
                "name": "Expenses",
                "type": "section",
                "items": [
                    {
                        "type": "line_item",
                        "id": "cogs",
                        "name": "Cost of Goods Sold",
                        "node_id": "cogs",
                    },
                    {
                        "type": "line_item",
                        "id": "operating_expenses",
                        "name": "Operating Expenses",
                        "node_id": "operating_expenses",
                    },
                    {
                        "type": "calculated",
                        "id": "gross_profit",
                        "name": "Gross Profit",
                        "calculation": {
                            "type": "subtraction",
                            "inputs": ["revenue", "cogs"],
                        },
                    },
                ],
            },
        ],
    }

    print(f"Graph has {len(graph.nodes)} nodes: {list(graph.nodes.keys())}")
    print(f"Periods: {graph.periods}")

    # Build statement with validation
    config = create_validated_statement_config(
        config_data,
        enable_node_validation=True,
        strict_mode=False,
    )

    errors = config.validate_config()
    if errors:
        print(f"Validation issues: {len(errors)}")
        for error in errors:
            print(f"  - {error}")

    builder = create_validated_statement_builder(
        enable_node_validation=True,
        strict_mode=False,
    )

    if config.model:
        statement = builder.build(config)
        print(f"✅ Statement built: {statement.name}")

        # Note: To complete this example, you would typically:
        # 1. Populate the graph with calculation nodes from the statement
        # 2. Use StatementFormatter to create a DataFrame
        # 3. Display the formatted results
        print("   Statement would be ready for graph population and formatting")


def main():
    """Run all node validation examples."""
    print("Node Validation Integration Examples")
    print("=" * 50)

    try:
        example_basic_node_validation()
        example_custom_validator_configuration()
        example_convenience_functions()
        example_invalid_configuration()
        example_integration_with_graph()

        print("\n" + "=" * 50)
        print("✅ All examples completed successfully!")
        print("\nKey Benefits of Node Validation Integration:")
        print("  • Early detection of naming convention violations")
        print("  • Automatic standardization of alternate node names")
        print("  • Improved graph hygiene and consistency")
        print("  • Better error messages with context")
        print("  • Flexible validation modes (strict vs. warnings)")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
