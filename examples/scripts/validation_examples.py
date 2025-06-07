"""Examples demonstrating the UnifiedNodeValidator's capabilities.

This example shows how validation settings are controlled through
the centralized configuration system.

AUTOMATIC CASE HANDLING:
The validator now automatically handles case variations for standard node names.
All standard names are stored in lowercase, but the validator will recognize
any case variation:
  - "Revenue", "REVENUE", "revenue" → all recognized as standard "revenue"
  - "COGS", "cogs", "Cogs" → all map to "cost_of_goods_sold"
  - "EBITDA", "ebitda", "Ebitda" → all recognized as standard "ebitda"

Note: Names with spaces still need preprocessing (replace spaces with underscores).

IMPORTANT NOTE ON CASE SENSITIVITY:
The standard node registry is case-sensitive. All standard node names are stored
in lowercase (e.g., "revenue", "cost_of_goods_sold", "ebitda"). When validating
node names from external sources (like Excel), you should normalize them to
lowercase and replace spaces with underscores before validation.

Example normalization:
  "Revenue" -> "revenue"
  "Cost of Goods Sold" -> "cost_of_goods_sold"
  "EBITDA" -> "ebitda"
"""

import logging
from fin_statement_model.config import get_config, update_config, reset_config, cfg, cfg_or_param
from fin_statement_model.io.validation import UnifiedNodeValidator

# Get configuration
config = get_config()

# Configure logging using centralized config
logger = logging.getLogger(__name__)


def example_basic_validation():
    """Show basic node name validation using config settings."""
    logger.info("=== Basic Validation Example ===")

    # Create validator - automatically uses config settings!
    validator = UnifiedNodeValidator()

    # The validator now uses these config defaults internally:
    # - config.validation.strict_mode
    # - config.validation.auto_standardize_names
    # - config.validation.warn_on_non_standard

    logger.info("Validation Config (from centralized config):")
    logger.info(f"  Strict Mode: {validator.strict_mode}")
    logger.info(f"  Auto Standardize: {validator.auto_standardize}")
    logger.info(f"  Warn on Non-Standard: {validator.warn_on_non_standard}")

    # Test various node names
    # The validator now handles case automatically!
    test_names = [
        "revenue",  # Standard financial item
        "Revenue",  # Now recognized as standard!
        "accounts_receivable",  # Standard name (with underscore)
        "Accounts Receivable",  # Still needs space replacement
        "ebitda",  # Standard calculated metric
        "core.ebitda",  # Namespaced metric (custom)
        "custom_metric",  # Custom node
        "revenue_growth_yoy",  # Pattern-based metric
        "revenue_q1",  # Sub-node pattern
        "invalid name!",  # Invalid characters
    ]

    for name in test_names:
        result = validator.validate(name)
        logger.info(f"\nNode: '{name}'")
        logger.info(f"  Standardized: '{result.standardized_name}'")
        logger.info(f"  Valid: {result.is_valid}")
        logger.info(f"  Category: {result.category}")
        logger.info(f"  Message: {result.message}")
        if result.suggestions:
            logger.info(f"  Suggestions: {result.suggestions}")

    # Batch validation
    logger.info("\n--- Batch Validation ---")
    results = validator.validate_batch(test_names)
    for name, result in results.items():
        logger.info(f"{name}: {result.category} - {result.standardized_name}")


def example_case_sensitivity_handling():
    """Show automatic case handling in action."""
    logger.info("\n=== Automatic Case Handling ===")
    validator = UnifiedNodeValidator()
    # Test cases showing automatic case handling
    test_cases = [
        ("revenue", "Standard lowercase"),
        ("Revenue", "Title case"),
        ("REVENUE", "Uppercase"),
        ("cost_of_goods_sold", "Standard with underscores"),
        ("Cost of Goods Sold", "Title case with spaces"),
        ("COGS", "Common abbreviation uppercase"),
        ("cogs", "Common abbreviation lowercase"),
    ]
    logger.info("Automatic case normalization:")
    for name, description in test_cases:
        result = validator.validate(name)
        logger.info(f"{name} ({description}): {result.category} -> '{result.standardized_name}'")
    logger.info("\n--- Names with spaces still need preprocessing ---")
    logger.info("Example: 'Cost of Goods Sold' needs to become 'cost_of_goods_sold'")
    # Show preprocessing for names with spaces
    name_with_spaces = "Cost of Goods Sold"
    preprocessed = name_with_spaces.replace(" ", "_")
    result = validator.validate(preprocessed)
    logger.info(f"'{name_with_spaces}' -> '{preprocessed}' -> '{result.standardized_name}' ({result.category})")


def example_context_aware_validation():
    """Show context-aware validation with node types and relationships."""
    logger.info("\n=== Context-Aware Validation Example ===")

    validator = UnifiedNodeValidator(
        enable_patterns=True,
        strict_mode=config.validation.strict_mode,
    )

    # Test nodes with context
    test_cases = [
        ("revenue", "data", []),
        ("gross_profit", "calculation", ["revenue", "cost_of_goods_sold"]),
        ("revenue_growth_yoy", "metric", ["revenue"]),
        ("custom_analysis", "custom", []),
    ]

    for name, node_type, parent_nodes in test_cases:
        result = validator.validate(name, node_type=node_type, parent_nodes=parent_nodes)
        logger.info(f"\nNode: '{name}' (Type: {node_type})")
        logger.info(f"  Parents: {parent_nodes}")
        logger.info(f"  Category: {result.category}")
        logger.info(f"  Valid: {result.is_valid}")
        logger.info(f"  Message: {result.message}")


def example_graph_building():
    """Show validation during graph building with config settings."""
    logger.info("\n=== Graph Building with Validation ===")

    from fin_statement_model.core.graph import Graph
    from fin_statement_model.core.nodes import FinancialStatementItemNode

    # Use config settings for validation
    validator = UnifiedNodeValidator(
        auto_standardize=config.validation.auto_standardize_names,
        warn_on_non_standard=config.validation.warn_on_non_standard,
        strict_mode=config.validation.strict_mode,
    )

    graph = Graph()

    # Simulate adding nodes with validation
    # Mixed case works automatically now!
    node_data = {
        "Revenue": {"2023": 1000},
        "COGS": {"2023": 600},
        "gross profit": {"2023": 400},
        "Operating Expenses": {"2023": 200},
    }

    for name, values in node_data.items():
        # For names with spaces, we still need to replace them
        preprocessed_name = name.replace(" ", "_")
        result = validator.validate(preprocessed_name)

        if result.is_valid:
            if result.standardized_name != preprocessed_name:
                logger.info(f"Standardized '{name}' -> '{result.standardized_name}'")

            # Add node with standardized name
            node_name = (
                result.standardized_name if config.validation.auto_standardize_names else name
            )
            node = FinancialStatementItemNode(node_name, values)
            graph.add_node(node)
        elif config.validation.strict_mode:
            logger.error(f"Invalid node name '{name}' - {result.message}")
            # In strict mode, skip invalid nodes
            continue
        else:
            logger.warning(f"Warning: '{name}' is invalid - {result.message}")
            # In non-strict mode, add anyway
            node = FinancialStatementItemNode(name, values)
            graph.add_node(node)

    # Generate validation report
    all_node_names = [node.name for node in graph.nodes.values()]
    results = validator.validate_batch(all_node_names)
    # Create report from results
    report = {
        "total": len(results),
        "by_validity": {"valid": 0, "invalid": 0},
        "by_category": {},
        "suggestions": {},
    }
    for name, result in results.items():
        # Count by validity
        if result.is_valid:
            report["by_validity"]["valid"] += 1
        else:
            report["by_validity"]["invalid"] += 1
        # Count by category
        if result.category not in report["by_category"]:
            report["by_category"][result.category] = []
        report["by_category"][result.category].append(name)
        # Collect suggestions
        if result.suggestions:
            report["suggestions"][name] = result.suggestions

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
    """Show difference between flexible and strict validation modes using config."""
    logger.info("\n=== Strict vs Flexible Validation ===")

    # Save current config
    current_strict = config.validation.strict_mode

    # Test with strict mode
    update_config({"validation": {"strict_mode": True}})
    strict_validator = UnifiedNodeValidator(strict_mode=config.validation.strict_mode)

    # Test with flexible mode
    update_config({"validation": {"strict_mode": False}})
    flexible_validator = UnifiedNodeValidator(strict_mode=config.validation.strict_mode)

    test_names = ["revenue_2023_q1", "custom_metric", "My Special Node"]

    logger.info("Strict Mode Results:")
    for name in test_names:
        result = strict_validator.validate(name)
        logger.info(f"  {name}: Valid={result.is_valid}, Category={result.category}")

    logger.info("\nFlexible Mode Results:")
    for name in test_names:
        result = flexible_validator.validate(name)
        logger.info(f"  {name}: Valid={result.is_valid}, Category={result.category}")

    # Restore original config
    update_config({"validation": {"strict_mode": current_strict}})


def example_excel_reader_integration():
    """Show how validation integrates with Excel reading using config."""
    logger.info("\n=== Reader Integration Example ===")

    # Create validator with IO config settings
    validator = UnifiedNodeValidator(
        auto_standardize=config.io.auto_standardize_columns,
        enable_patterns=True,
    )

    # Simulate Excel column headers (often in mixed case)
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
        # Only need to handle spaces and special characters now
        # Case is handled automatically!
        normalized = excel_name.replace(" ", "_").replace("&", "_and_")
        result = validator.validate(normalized)
        if result.is_valid:
            mapping[excel_name] = result.standardized_name
            if normalized != result.standardized_name:
                logger.info(f"Mapped '{excel_name}' -> '{result.standardized_name}'")
        elif config.io.strict_validation:
            logger.error(f"Invalid column name '{excel_name}' - {result.message}")
        else:
            logger.warning(f"No mapping found for '{excel_name}', using normalized: '{normalized}'")
            mapping[excel_name] = normalized

    logger.info(f"\nFinal mapping: {mapping}")

    # Show how config affects behavior
    logger.info("\nIO Validation Config:")
    logger.info(f"  Strict Validation: {config.io.strict_validation}")
    logger.info(f"  Auto Standardize: {config.io.auto_standardize_columns}")
    logger.info(f"  Skip Invalid: {config.io.skip_invalid_rows}")


def demonstrate_config_override():
    """Show how to temporarily override validation config."""
    logger.info("\n=== Config Override Example ===")

    # Show current config
    logger.info("Current Validation Config:")
    logger.info(f"  Strict Mode: {config.validation.strict_mode}")
    logger.info(f"  Balance Check: {config.validation.check_balance_sheet_balance}")

    # Temporarily override for a specific operation
    with_balance_check = {
        "validation": {"check_balance_sheet_balance": True, "balance_tolerance": 0.01}
    }

    logger.info("\nTemporarily enabling balance sheet validation...")
    update_config(with_balance_check)

    logger.info("Updated Config:")
    logger.info(f"  Balance Check: {config.validation.check_balance_sheet_balance}")
    logger.info(f"  Tolerance: {config.validation.balance_tolerance}")

    # Perform validation with updated config
    # ... validation logic here ...

    # Note: In practice, you'd want to restore the original config
    # or use a context manager for temporary changes


if __name__ == "__main__":
    # Show initial config source
    logger.info(f"Configuration loaded from: {getattr(config, '_source', 'defaults')}\n")

    # Check if standard nodes are loaded
    from fin_statement_model.core.nodes import standard_node_registry
    logger.info(f"Standard nodes loaded: {len(standard_node_registry)}")
    if len(standard_node_registry) == 0:
        logger.warning("No standard nodes loaded! The registry is empty.")
    else:
        # Show a few examples
        sample_names = list(standard_node_registry.list_standard_names())[:5]
        logger.info(f"Sample standard node names: {sample_names}")

    logger.info("\n" + "="*60 + "\n")

    example_basic_validation()
    example_case_sensitivity_handling()
    example_context_aware_validation()
    example_graph_building()
    example_flexible_vs_strict()
    example_excel_reader_integration()
    demonstrate_config_override()
