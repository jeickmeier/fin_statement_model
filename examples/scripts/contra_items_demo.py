"""Contra Items Formatting Demo.

This example demonstrates how contra items are handled in financial statements,
showing different display styles and their impact on calculations.
"""

import logging
from pathlib import Path
from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import ItemNode, CalculationNode
from fin_statement_model.core.calculations import Addition
from fin_statement_model.statements import create_statement_dataframe
from fin_statement_model.io import write_data

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_graph_with_contra_items() -> Graph:
    """Create a graph with contra items for demonstration."""
    graph = Graph()

    # Regular asset items
    gross_ppe = ItemNode("gross_ppe")
    gross_ppe.set_value("2023", 1000000)
    gross_ppe.set_value("2024", 1200000)
    graph.add_node(gross_ppe)

    # Contra asset item (Accumulated Depreciation)
    accum_depreciation = ItemNode("accumulated_depreciation")
    accum_depreciation.set_value("2023", -300000)  # Negative value
    accum_depreciation.set_value("2024", -400000)
    graph.add_node(accum_depreciation)

    # Net PP&E calculation
    net_ppe = CalculationNode(
        name="net_ppe",
        inputs=["gross_ppe", "accumulated_depreciation"],
        calculation=Addition()  # Since accum_dep is already negative
    )
    graph.add_node(net_ppe)

    # Regular liability items
    gross_debt = ItemNode("gross_debt")
    gross_debt.set_value("2023", 500000)
    gross_debt.set_value("2024", 600000)
    graph.add_node(gross_debt)

    # Contra liability item (Debt Discount)
    debt_discount = ItemNode("debt_discount")
    debt_discount.set_value("2023", -50000)  # Reduces liability
    debt_discount.set_value("2024", -40000)
    graph.add_node(debt_discount)

    # Net Debt calculation
    net_debt = CalculationNode(
        name="net_debt",
        inputs=["gross_debt", "debt_discount"],
        calculation=Addition()
    )
    graph.add_node(net_debt)

    # Revenue items
    gross_revenue = ItemNode("gross_revenue")
    gross_revenue.set_value("2023", 2000000)
    gross_revenue.set_value("2024", 2500000)
    graph.add_node(gross_revenue)

    # Contra revenue items
    sales_returns = ItemNode("sales_returns")
    sales_returns.set_value("2023", -100000)
    sales_returns.set_value("2024", -125000)
    graph.add_node(sales_returns)

    sales_discounts = ItemNode("sales_discounts")
    sales_discounts.set_value("2023", -50000)
    sales_discounts.set_value("2024", -75000)
    graph.add_node(sales_discounts)

    # Net Revenue calculation
    net_revenue = CalculationNode(
        name="net_revenue",
        inputs=["gross_revenue", "sales_returns", "sales_discounts"],
        calculation=Addition()
    )
    graph.add_node(net_revenue)

    return graph


def demo_contra_display_styles():
    """Demonstrate different contra item display styles."""
    logger.info("=== Contra Items Formatting Demo ===\n")

    graph = create_graph_with_contra_items()

    # Path to the contra items example config
    script_dir = Path(__file__).parent
    config_path = script_dir / "configs" / "contra_items_example.yaml"

    if not config_path.exists():
        logger.error("Error: Could not find contra_items_example.yaml configuration file.")
        logger.error("Please ensure the example configuration exists.")
        return

    # Different display styles for contra items
    display_styles = ["parentheses", "brackets", "negative", "indented"]

    for style in display_styles:
        logger.info(f"\n--- Contra Display Style: {style} ---")

        # Create DataFrame with different contra display styles
        df = create_statement_dataframe(
            graph=graph,
            config_path_or_dir=str(config_path),
            format_kwargs={
                "number_format": ",.0f",
                "contra_display_style": style,
                "should_apply_signs": True,
                "add_contra_indicator": True,  # Add column to identify contra items
            },
            periods=["2023", "2024"]
        )

        # Show only relevant columns for clarity
        display_cols = ["Line Item", "2023", "2024"]
        if "is_contra" in df.columns:
            display_cols.append("is_contra")

        logger.info(df[display_cols].to_string(index=False))
        logger.info("")


def demo_calculation_accuracy():
    """Demonstrate that calculations remain accurate regardless of display."""
    logger.info("=== Calculation Accuracy Demo ===\n")

    graph = create_graph_with_contra_items()

    # Create a simple config to show PP&E section
    simple_config = {
        "id": "ppe_demo",
        "name": "PP&E Section Demo",
        "sections": [
            {
                "id": "ppe_section",
                "name": "Property, Plant & Equipment",
                "items": [
                    {
                        "id": "gross_ppe",
                        "name": "Gross PP&E",
                        "type": "line_item",
                        "node_id": "gross_ppe",
                        "sign_convention": 1,
                    },
                    {
                        "id": "accum_dep",
                        "name": "Accumulated Depreciation",
                        "type": "line_item",
                        "node_id": "accumulated_depreciation",
                        "is_contra": True,
                        "sign_convention": -1,
                    },
                    {
                        "id": "net_ppe",
                        "name": "Net PP&E",
                        "type": "calculated",
                        "calculation": {
                            "type": "addition",
                            "inputs": ["gross_ppe", "accum_dep"]
                        },
                        "sign_convention": 1,
                    }
                ]
            }
        ]
    }

    # Generate DataFrame
    df = create_statement_dataframe(
        graph=graph,
        config_path_or_dir=simple_config,
        format_kwargs={
            "number_format": ",.0f",
            "contra_display_style": "parentheses",
            "should_apply_signs": True,
            "add_contra_indicator": True,
        },
        periods=["2023", "2024"]
    )

    logger.info("PP&E Calculation with Contra Items:")
    logger.info(df[["Line Item", "2023", "2024", "is_contra"]].to_string(index=False))

    # Verify calculations manually
    gross_2023 = graph.get_node("gross_ppe").get_value("2023")
    accum_2023 = abs(graph.get_node("accumulated_depreciation").get_value("2023"))
    net_2023 = graph.calculate("net_ppe", "2023")

    logger.info("\nManual Verification for 2023:")
    logger.info(f"Gross PP&E: ${gross_2023:,.0f}")
    logger.info(f"Less: Accumulated Depreciation: ${accum_2023:,.0f}")
    logger.info(f"Net PP&E: ${net_2023:,.0f}")
    logger.info(f"Calculation: {gross_2023:,.0f} - {accum_2023:,.0f} = {net_2023:,.0f}")


def demo_html_output():
    """Demonstrate HTML output with contra item styling."""
    logger.info("\n=== HTML Output Demo ===\n")

    graph = create_graph_with_contra_items()

    # Use the example config
    script_dir = Path(__file__).parent
    config_path = script_dir / "configs" / "contra_items_example.yaml"

    if config_path.exists():
        # Generate HTML with contra styling
        html = write_data(
            format_type="html",
            graph=graph,
            target=None,  # Return as string
            config_path=str(config_path),
            format_kwargs={
                "number_format": ",.0f",
                "contra_display_style": "parentheses",
                "should_apply_signs": True,
                "include_css": True,
                "contra_css_class": "contra-item",
            },
            periods=["2023", "2024"]
        )

        # Save HTML to file
        output_path = script_dir / "contra_items_demo.html"
        with open(output_path, "w") as f:
            f.write(html)

        logger.info("HTML Output (first 500 characters):")
        logger.info(html[:500])
        logger.info("...")
        logger.info("\nFull HTML saved to contra_items_demo.html")


def main():
    """Run all contra item demonstrations."""
    try:
        logger.info("Financial Statement Model - Contra Items Demo")
        logger.info("=" * 50)

        # Run demonstrations
        demo_contra_display_styles()
        demo_calculation_accuracy()
        demo_html_output()

        logger.info("\n=== Demo Complete ===")
        logger.info("Key takeaways:")
        logger.info("1. Contra items display intuitively (parentheses, etc.)")
        logger.info("2. Calculations remain mathematically correct")
        logger.info("3. CSS styling automatically applied")
        logger.info("4. Multiple display styles supported")
        logger.info("5. Clear separation of calculation vs. display logic")

    except Exception:
        logger.exception("Error during demo")


if __name__ == "__main__":
    main()
