"""Contra Items Demonstration.

This script demonstrates the contra items feature in the Financial Statement Model.
It shows how contra items like Accumulated Depreciation, Treasury Stock, and Sales Returns
are handled with proper calculation logic and intuitive display formatting.
"""

from fin_statement_model.core.graph import Graph
from fin_statement_model.statements import (
    StatementFormatter,
    build_validated_statement_from_config,
    populate_graph_from_statement,
)


def create_sample_graph() -> Graph:
    """Create a sample graph with data for demonstrating contra items."""
    graph = Graph()

    # Asset items
    graph.add_financial_statement_item("gross_property_plant_equipment", {"2023": 1000000, "2024": 1200000})
    graph.add_financial_statement_item("accumulated_depreciation", {"2023": 250000, "2024": 350000})

    # Revenue items
    graph.add_financial_statement_item("gross_sales", {"2023": 5000000, "2024": 5500000})
    graph.add_financial_statement_item("sales_returns_allowances", {"2023": 50000, "2024": 60000})
    graph.add_financial_statement_item("sales_discounts", {"2023": 25000, "2024": 30000})

    # Equity items
    graph.add_financial_statement_item("common_stock", {"2023": 1000000, "2024": 1000000})
    graph.add_financial_statement_item("retained_earnings", {"2023": 800000, "2024": 950000})
    graph.add_financial_statement_item("treasury_stock", {"2023": 150000, "2024": 200000})

    return graph


def demonstrate_contra_formatting():
    """Demonstrate different contra formatting styles."""
    print("=== Contra Items Formatting Demo ===\n")

    # Create sample graph
    graph = create_sample_graph()

    # Load the contra items example configuration
    try:
        statement = build_validated_statement_from_config(
            "examples/scripts/configs/contra_items_example.yaml"
        )
    except FileNotFoundError:
        print("Error: Could not find contra_items_example.yaml configuration file.")
        print("Please ensure the example configuration exists.")
        return

    # Populate the graph with calculation nodes from the statement
    populate_graph_from_statement(statement, graph)
    formatter = StatementFormatter(statement)

    # Demonstrate different display styles
    styles = ["parentheses", "negative_sign", "brackets"]

    for style in styles:
        print(f"\n--- Contra Display Style: {style} ---")

        df = formatter.generate_dataframe(
            graph=graph,
            contra_display_style=style,
            apply_contra_formatting=True,
            add_contra_indicator_column=True,
            include_css_classes=True,
        )

        # Show just the key columns for demo
        display_cols = ["Line Item", "2023", "2024", "is_contra"]
        if "css_class" in df.columns:
            display_cols.append("css_class")

        print(df[display_cols].to_string(index=False))
        print()


def demonstrate_calculation_accuracy():
    """Demonstrate that calculations remain accurate with contra items."""
    print("=== Calculation Accuracy Demo ===\n")

    graph = create_sample_graph()

    # Create a simple test case for PPE calculation
    statement_config = {
        "id": "test_contra_calc",
        "name": "Contra Calculation Test",
        "sections": [
            {
                "id": "ppe_section",
                "name": "Property, Plant & Equipment",
                "items": [
                    {
                        "id": "gross_ppe",
                        "name": "Gross PP&E",
                        "type": "line_item",
                        "node_id": "gross_property_plant_equipment",
                        "sign_convention": 1,
                    },
                    {
                        "id": "accum_depreciation",
                        "name": "Less: Accumulated Depreciation",
                        "type": "line_item",
                        "node_id": "accumulated_depreciation",
                        "sign_convention": -1,
                        "is_contra": True,
                    },
                    {
                        "id": "net_ppe",
                        "name": "Net PP&E",
                        "type": "calculated",
                        "calculation": {
                            "type": "addition",
                            "inputs": ["gross_ppe", "accum_depreciation"],
                        },
                        "sign_convention": 1,
                    },
                ],
            }
        ],
    }

    statement = build_validated_statement_from_config(statement_config)
    populate_graph_from_statement(statement, graph)
    formatter = StatementFormatter(statement)

    # Show calculation with contra formatting
    df = formatter.generate_dataframe(
        graph=graph,
        apply_contra_formatting=True,
        add_contra_indicator_column=True,
    )

    print("PP&E Calculation with Contra Items:")
    print(df[["Line Item", "2023", "2024", "is_contra"]].to_string(index=False))

    # Verify calculations manually
    gross_2023 = 1000000
    accum_2023 = 250000
    net_2023 = gross_2023 - accum_2023  # Should be 750000

    print("\nManual Verification for 2023:")
    print(f"Gross PP&E: ${gross_2023:,.0f}")
    print(f"Less: Accumulated Depreciation: ${accum_2023:,.0f}")
    print(f"Net PP&E: ${net_2023:,.0f}")
    print(f"Calculation: {gross_2023:,.0f} - {accum_2023:,.0f} = {net_2023:,.0f}")


def demonstrate_html_output():
    """Demonstrate HTML output with contra styling."""
    print("\n=== HTML Output Demo ===\n")

    graph = create_sample_graph()
    statement = build_validated_statement_from_config(
        "examples/scripts/configs/contra_items_example.yaml"
    )
    populate_graph_from_statement(statement, graph)
    formatter = StatementFormatter(statement)

    # Generate HTML with custom styling
    html = formatter.format_html(
        graph=graph,
        apply_contra_formatting=True,
        css_styles={
            ".contra-item": "font-style: italic; color: #666; font-weight: bold;",
            ".asset-contra": "background-color: #f0f8f0; border-left: 3px solid #4CAF50;",
            ".revenue-contra": "background-color: #fff8f0; border-left: 3px solid #FF9800;",
            ".equity-contra": "background-color: #f8f0f0; border-left: 3px solid #F44336;",
        },
    )

    print("HTML Output (first 500 characters):")
    print(html[:500])
    print("...")
    print("\nFull HTML saved to contra_items_demo.html")

    # Save to file
    with open("contra_items_demo.html", "w") as f:
        f.write(html)


def main():
    """Main demonstration function."""
    print("Financial Statement Model - Contra Items Demo")
    print("=" * 50)

    try:
        demonstrate_contra_formatting()
        demonstrate_calculation_accuracy()
        demonstrate_html_output()

        print("\n=== Demo Complete ===")
        print("Key takeaways:")
        print("1. Contra items display intuitively (parentheses, etc.)")
        print("2. Calculations remain mathematically correct")
        print("3. CSS styling automatically applied")
        print("4. Multiple display styles supported")
        print("5. Clear separation of calculation vs. display logic")

    except Exception as e:
        print(f"Error during demo: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
