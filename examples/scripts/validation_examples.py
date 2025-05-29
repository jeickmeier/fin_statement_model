"""Examples demonstrating the UnifiedNodeValidator's capabilities."""

import logging
from fin_statement_model.io.validation import UnifiedNodeValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def example_basic_validation():
    """Show basic node name validation."""
    logger.info("=== Basic Validation Example ===")

    validator = UnifiedNodeValidator()

    # Test various node names
    test_names = [
        "revenue",  # Standard financial item
        "Accounts Receivable",  # Needs case standardization
        "core.ebitda",  # Namespaced metric
        "custom_metric",  # Custom node
        "revenue_growth_yoy",  # Pattern-based metric
        "invalid name!",  # Invalid characters
    ]

    for name in test_names:
        result = validator.validate_node(name)
        logger.info(f"\nNode: '{name}'")
        logger.info(f"  Standardized: '{result.standardized_name}'")
        logger.info(f"  Valid: {result.is_valid}")
        logger.info(f"  Category: {result.category}")
        logger.info(f"  Message: {result.message}")
        if result.suggestions:
            logger.info(f"  Suggestions: {result.suggestions}")

    # Batch validation
    logger.info("\n--- Batch Validation ---")
    results = validator.validate_nodes(test_names)
    for name, result in results.items():
        logger.info(f"{name}: {result.category} - {result.standardized_name}")


def example_context_aware_validation():
    """Show context-aware validation with node types and relationships."""
    logger.info("\n=== Context-Aware Validation Example ===")

    validator = UnifiedNodeValidator(
        enable_patterns=True,
        strict_mode=False,
    )

    # Test nodes with context
    test_cases = [
        ("revenue", "data", []),
        ("gross_profit", "calculation", ["revenue", "cogs"]),
        ("revenue_growth_yoy", "metric", ["revenue"]),
        ("custom_analysis", "custom", []),
    ]

    for name, node_type, parent_nodes in test_cases:
        result = validator.validate_node(name, node_type=node_type, parent_nodes=parent_nodes)
        logger.info(f"\nNode: '{name}' (Type: {node_type})")
        logger.info(f"  Parents: {parent_nodes}")
        logger.info(f"  Category: {result.category}")
        logger.info(f"  Valid: {result.is_valid}")
        logger.info(f"  Message: {result.message}")


def example_graph_building():
    """Show validation during graph building."""
    logger.info("\n=== Graph Building with Validation ===")

    from fin_statement_model.core.graph import Graph
    from fin_statement_model.core.nodes import ItemNode

    validator = UnifiedNodeValidator(
        auto_standardize=True,
        warn_on_non_standard=True,
    )

    graph = Graph()

    # Simulate adding nodes with validation
    node_data = {
        "Revenue": {"2023": 1000},
        "COGS": {"2023": 600},
        "gross profit": {"2023": 400},
        "Operating Expenses": {"2023": 200},
    }

    for name, values in node_data.items():
        result = validator.validate_node(name)

        if result.is_valid:
            if result.standardized_name != name:
                logger.info(f"Standardized '{name}' to '{result.standardized_name}'")
            else:
                logger.warning(f"Warning: '{name}' is invalid - {result.message}")

            # Add node with standardized name
            node = ItemNode(result.standardized_name)
            for period, value in values.items():
                node.set_value(period, value)
            graph.add_node(node)

    # Generate validation report
    all_node_names = [node.name for node in graph.nodes.values()]
    report = validator.generate_validation_report(all_node_names)

    logger.info("\n--- Graph Validation Report ---")
    logger.info(f"Total nodes: {report['total']}")
    logger.info(f"Valid: {report['by_validity']['valid']}")
    logger.info(f"Invalid: {report['by_validity']['invalid']}")

    logger.info("\nBy category:")
    for category, nodes in report["by_category"].items():
        logger.info(f"  {category}: {len(nodes)} nodes")

    if report["suggestions"]:
        logger.info("\nSuggestions for improvement:")
        for node_name, suggestions in report["suggestions"].items():
            logger.info(f"  {node_name}:")
            for suggestion in suggestions:
                logger.info(f"    - {suggestion}")


def example_flexible_vs_strict():
    """Show difference between flexible and strict validation modes."""
    logger.info("\n=== Strict vs Flexible Validation ===")

    # Strict validator
    strict_validator = UnifiedNodeValidator(strict_mode=True)

    # Flexible validator
    flexible_validator = UnifiedNodeValidator(strict_mode=False)

    test_names = ["revenue_2023_q1", "custom_metric", "My Special Node"]

    logger.info("Strict Mode Results:")
    for name in test_names:
        result = strict_validator.validate_node(name)
        logger.info(f"  {name}: Valid={result.is_valid}, Category={result.category}")

    logger.info("\nFlexible Mode Results:")
    for name in test_names:
        result = flexible_validator.validate_node(name)
        logger.info(f"  {name}: Valid={result.is_valid}, Category={result.category}")


def example_excel_reader_integration():
    """Show how validation integrates with Excel reading."""
    logger.info("\n=== Reader Integration Example ===")

    validator = UnifiedNodeValidator(
        auto_standardize=True,
        enable_patterns=True,
    )

    # Simulate Excel column headers
    excel_headers = [
        "Revenue",
        "Cost of Goods Sold",
        "Operating Income",
        "EBITDA",
        "Accounts Receivable",
        "PP&E",
    ]

    # Map Excel headers to standardized node names
    mapping = {}
    for excel_name in excel_headers:
        result = validator.validate_node(excel_name)
        if result.is_valid:
            mapping[excel_name] = result.standardized_name
            if excel_name != result.standardized_name:
                logger.info(f"Mapped '{excel_name}' to '{result.standardized_name}'")
        else:
            # Handle invalid names - maybe prompt user or use as-is
            logger.warning(f"No mapping found for '{excel_name}', using as-is")
            mapping[excel_name] = excel_name

    logger.info(f"\nFinal mapping: {mapping}")


if __name__ == "__main__":
    example_basic_validation()
    example_context_aware_validation()
    example_graph_building()
    example_flexible_vs_strict()
    example_excel_reader_integration()
