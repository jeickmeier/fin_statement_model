"""Examples demonstrating node name validation in the financial statement model."""

from fin_statement_model.io.validation import UnifiedNodeValidator
from fin_statement_model.io import read_data


def example_basic_validation():
    """Basic validation example."""
    print("=== Basic Validation Example ===")

    validator = UnifiedNodeValidator(
        strict_mode=False, auto_standardize=True, warn_on_non_standard=True
    )

    # Test various node names
    test_names = [
        "revenue",  # Standard name
        "sales",  # Alternate name
        "total_revenue",  # Custom name
        "revenue_q1",  # Sub-node pattern
        "gross_margin",  # Formula pattern
    ]

    for name in test_names:
        result = validator.validate(name)
        print(f"\nNode: '{name}'")
        print(f"  Standardized: '{result.standardized_name}'")
        print(f"  Valid: {result.is_valid}")
        print(f"  Category: {result.category}")
        print(f"  Message: {result.message}")
        if result.suggestions:
            print(f"  Suggestions: {result.suggestions}")

    # Batch validation
    print("\n--- Batch Validation ---")
    results = validator.validate_batch(test_names)
    for name, result in results.items():
        print(f"{name}: {result.category} - {result.standardized_name}")


def example_context_aware_validation():
    """Context-aware validation with parent nodes."""
    print("\n=== Context-Aware Validation Example ===")

    validator = UnifiedNodeValidator(
        strict_mode=False,
        enable_patterns=True,  # Enable pattern recognition
    )

    # Test with context
    test_cases = [
        ("revenue_margin", "calculation", ["revenue", "gross_profit"]),
        ("debt_equity_ratio", "formula", ["total_debt", "total_equity"]),
        ("revenue_north_america", "data", ["revenue"]),
        ("custom_metric", "calculation", ["revenue", "expenses"]),
    ]

    for name, node_type, parent_nodes in test_cases:
        result = validator.validate(
            name, node_type=node_type, parent_nodes=parent_nodes
        )
        print(f"\nNode: '{name}' (Type: {node_type})")
        print(f"  Parents: {parent_nodes}")
        print(f"  Category: {result.category}")
        print(f"  Valid: {result.is_valid}")
        print(f"  Message: {result.message}")


def example_graph_building_with_validation():
    """Build a graph with validation."""
    print("\n=== Graph Building with Validation ===")

    # Create data with potentially non-standard names
    raw_data = {
        "sales": {"2021": 1000, "2022": 1100, "2023": 1200},
        "cogs": {"2021": 600, "2022": 650, "2023": 700},
        "opex": {"2021": 200, "2022": 210, "2023": 220},
        "custom_item": {"2021": 50, "2022": 55, "2023": 60},
    }

    validator = UnifiedNodeValidator(strict_mode=False)

    # Validate and standardize before creating graph
    standardized_data = {}
    for name, values in raw_data.items():
        result = validator.validate(name)
        if result.is_valid:
            standardized_data[result.standardized_name] = values
            if result.standardized_name != name:
                print(f"Standardized '{name}' to '{result.standardized_name}'")
        else:
            print(f"Warning: '{name}' is invalid - {result.message}")
            # Still include it if not in strict mode
            standardized_data[name] = values

    # Create graph with standardized data
    graph = read_data("dict", standardized_data)

    # Add calculations
    graph.add_calculation(
        name="gross_profit",
        input_names=["revenue", "cost_of_goods_sold"],
        operation_type="addition",
    )

    # Validate the entire graph
    print("\n--- Graph Validation Report ---")
    report = validator.validate_graph(list(graph.nodes.values()))

    print(f"Total nodes: {report['total']}")
    print(f"Valid: {report['by_validity']['valid']}")
    print(f"Invalid: {report['by_validity']['invalid']}")

    print("\nBy category:")
    for category, nodes in report["by_category"].items():
        print(f"  {category}: {len(nodes)} nodes")

    if report["suggestions"]:
        print("\nSuggestions for improvement:")
        for node_name, suggestions in report["suggestions"].items():
            print(f"  {node_name}:")
            for suggestion in suggestions:
                print(f"    - {suggestion}")

    return graph


def example_strict_vs_flexible():
    """Compare strict vs flexible validation modes."""
    print("\n=== Strict vs Flexible Validation ===")

    strict_validator = UnifiedNodeValidator(strict_mode=True, auto_standardize=True)
    flexible_validator = UnifiedNodeValidator(strict_mode=False, auto_standardize=True)

    test_names = ["revenue", "sales", "custom_metric", "revenue_q1"]

    print("Strict Mode Results:")
    for name in test_names:
        result = strict_validator.validate(name)
        print(f"  {name}: Valid={result.is_valid}, Category={result.category}")

    print("\nFlexible Mode Results:")
    for name in test_names:
        result = flexible_validator.validate(name)
        print(f"  {name}: Valid={result.is_valid}, Category={result.category}")


def example_reader_integration():
    """Show validation integrated with data readers."""
    print("\n=== Reader Integration Example ===")

    # Simulate reading from Excel with non-standard names
    excel_data = {
        "Sales Revenue": {"2021": 1000, "2022": 1100, "2023": 1200},
        "Cost of Sales": {"2021": 600, "2022": 650, "2023": 700},
        "Operating Expenses": {"2021": 200, "2022": 210, "2023": 220},
    }

    # Create mapping based on validation
    validator = UnifiedNodeValidator(strict_mode=False, auto_standardize=True)

    mapping = {}
    for excel_name in excel_data:
        # Try to find a match by checking various possibilities
        test_name = excel_name.lower().replace(" ", "_")
        result = validator.validate(test_name)

        if result.is_valid:
            mapping[excel_name] = result.standardized_name
            print(f"Mapped '{excel_name}' to '{result.standardized_name}'")
        else:
            # Use as-is if no match found
            mapping[excel_name] = excel_name
            print(f"No mapping found for '{excel_name}', using as-is")

    print(f"\nFinal mapping: {mapping}")


def main():
    """Run all validation examples."""
    example_basic_validation()
    example_context_aware_validation()
    example_graph_building_with_validation()
    example_strict_vs_flexible()
    example_reader_integration()


if __name__ == "__main__":
    main()
