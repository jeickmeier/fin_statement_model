"""Simple Contra Items Demo.

This example demonstrates how contra items work in financial statements
without using the full statement framework.
"""

import logging
import pandas as pd
from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import FinancialStatementItemNode, CalculationNode
from fin_statement_model.core.calculations import AdditionCalculation

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_graph_with_contra_items() -> Graph:
    """Create a graph with contra items for demonstration."""
    graph = Graph()

    # Regular asset items
    gross_ppe = FinancialStatementItemNode("gross_ppe", {})
    gross_ppe.set_value("2023", 1000000)
    gross_ppe.set_value("2024", 1200000)
    graph.add_node(gross_ppe)

    # Contra asset item (Accumulated Depreciation)
    accum_depreciation = FinancialStatementItemNode("accumulated_depreciation", {})
    accum_depreciation.set_value("2023", -300000)  # Negative value
    accum_depreciation.set_value("2024", -400000)
    graph.add_node(accum_depreciation)

    # Net PP&E calculation
    net_ppe = CalculationNode(
        name="net_ppe",
        inputs=[gross_ppe, accum_depreciation],
        calculation=AdditionCalculation(),  # Since accum_dep is already negative
    )
    graph.add_node(net_ppe)

    # Revenue items
    gross_revenue = FinancialStatementItemNode("gross_revenue", {})
    gross_revenue.set_value("2023", 2000000)
    gross_revenue.set_value("2024", 2500000)
    graph.add_node(gross_revenue)

    # Contra revenue items
    sales_returns = FinancialStatementItemNode("sales_returns", {})
    sales_returns.set_value("2023", -100000)
    sales_returns.set_value("2024", -125000)
    graph.add_node(sales_returns)

    sales_discounts = FinancialStatementItemNode("sales_discounts", {})
    sales_discounts.set_value("2023", -50000)
    sales_discounts.set_value("2024", -75000)
    graph.add_node(sales_discounts)

    # Net Revenue calculation
    net_revenue = CalculationNode(
        name="net_revenue",
        inputs=[gross_revenue, sales_returns, sales_discounts],
        calculation=AdditionCalculation(),
    )
    graph.add_node(net_revenue)

    return graph


def format_contra_value(value: float, style: str = "parentheses") -> str:
    """Format a contra item value based on display style."""
    abs_value = abs(value)
    formatted = f"{abs_value:,.0f}"

    if style == "parentheses":  # noqa: SIM116
        return f"({formatted})"
    elif style == "brackets":
        return f"[{formatted}]"
    elif style == "negative":
        return f"-{formatted}"
    elif style == "indented":
        return f"    {formatted}"
    else:
        return formatted


def demo_contra_display_styles():
    """Demonstrate different contra item display styles."""
    logger.info("=== Contra Items Display Styles Demo ===\n")

    graph = create_graph_with_contra_items()

    # Define the financial statement structure
    statement_items = [
        ("Assets", None, False),
        ("Property, Plant & Equipment (Gross)", "gross_ppe", False),
        ("Less: Accumulated Depreciation", "accumulated_depreciation", True),
        ("Property, Plant & Equipment (Net)", "net_ppe", False),
        ("", None, False),  # Blank line
        ("Revenue", None, False),
        ("Gross Revenue", "gross_revenue", False),
        ("Less: Sales Returns", "sales_returns", True),
        ("Less: Sales Discounts", "sales_discounts", True),
        ("Net Revenue", "net_revenue", False),
    ]

    # Different display styles
    display_styles = ["parentheses", "brackets", "negative", "indented"]

    for style in display_styles:
        logger.info(f"\n--- Contra Display Style: {style} ---")
        logger.info(f"{'Line Item':<40} {'2023':>15} {'2024':>15}")
        logger.info("-" * 70)

        for item_name, node_id, is_contra in statement_items:
            if node_id is None:
                # Section header or blank line
                logger.info(f"{item_name:<40}")
            else:
                # Get values - use calculate for all nodes to be safe
                val_2023 = graph.calculate(node_id, "2023")
                val_2024 = graph.calculate(node_id, "2024")

                # Format values
                if is_contra and val_2023 < 0:
                    fmt_2023 = format_contra_value(val_2023, style)
                    fmt_2024 = format_contra_value(val_2024, style)
                else:
                    fmt_2023 = f"{val_2023:,.0f}"
                    fmt_2024 = f"{val_2024:,.0f}"

                logger.info(f"{item_name:<40} {fmt_2023:>15} {fmt_2024:>15}")


def demo_calculation_accuracy():
    """Demonstrate that calculations remain accurate regardless of display."""
    logger.info("\n=== Calculation Accuracy Demo ===\n")

    graph = create_graph_with_contra_items()

    # Show PP&E calculation
    logger.info("Property, Plant & Equipment Calculation:")

    gross_2023 = graph.get_node("gross_ppe").get_value("2023")
    accum_2023 = graph.get_node("accumulated_depreciation").get_value("2023")
    net_2023 = graph.calculate("net_ppe", "2023")

    logger.info(f"  Gross PP&E:                    ${gross_2023:,.0f}")
    logger.info(f"  Accumulated Depreciation:      ${accum_2023:,.0f} (stored as negative)")
    logger.info(f"  Net PP&E (calculated):         ${net_2023:,.0f}")
    logger.info(f"  Verification: {gross_2023:,.0f} + ({accum_2023:,.0f}) = {net_2023:,.0f}")

    # Show Revenue calculation
    logger.info("\nRevenue Calculation:")

    gross_rev_2023 = graph.get_node("gross_revenue").get_value("2023")
    returns_2023 = graph.get_node("sales_returns").get_value("2023")
    discounts_2023 = graph.get_node("sales_discounts").get_value("2023")
    net_rev_2023 = graph.calculate("net_revenue", "2023")

    logger.info(f"  Gross Revenue:                 ${gross_rev_2023:,.0f}")
    logger.info(f"  Sales Returns:                 ${returns_2023:,.0f} (stored as negative)")
    logger.info(f"  Sales Discounts:               ${discounts_2023:,.0f} (stored as negative)")
    logger.info(f"  Net Revenue (calculated):      ${net_rev_2023:,.0f}")
    logger.info(
        f"  Verification: {gross_rev_2023:,.0f} + ({returns_2023:,.0f}) + ({discounts_2023:,.0f}) = {net_rev_2023:,.0f}"
    )


def demo_dataframe_output():
    """Demonstrate creating a DataFrame with contra items."""
    logger.info("\n=== DataFrame Output Demo ===\n")

    graph = create_graph_with_contra_items()

    # Create data for DataFrame
    data = []

    # PP&E Section
    data.append(
        {
            "Section": "Assets",
            "Line Item": "Property, Plant & Equipment (Gross)",
            "2023": graph.get_node("gross_ppe").get_value("2023"),
            "2024": graph.get_node("gross_ppe").get_value("2024"),
            "Is Contra": False,
        }
    )

    accum_dep_2023 = graph.get_node("accumulated_depreciation").get_value("2023")
    accum_dep_2024 = graph.get_node("accumulated_depreciation").get_value("2024")
    data.append(
        {
            "Section": "Assets",
            "Line Item": "Less: Accumulated Depreciation",
            "2023": abs(accum_dep_2023),  # Show as positive in display
            "2024": abs(accum_dep_2024),
            "Is Contra": True,
        }
    )

    data.append(
        {
            "Section": "Assets",
            "Line Item": "Property, Plant & Equipment (Net)",
            "2023": graph.calculate("net_ppe", "2023"),
            "2024": graph.calculate("net_ppe", "2024"),
            "Is Contra": False,
        }
    )

    # Revenue Section
    data.append(
        {
            "Section": "Revenue",
            "Line Item": "Gross Revenue",
            "2023": graph.get_node("gross_revenue").get_value("2023"),
            "2024": graph.get_node("gross_revenue").get_value("2024"),
            "Is Contra": False,
        }
    )

    returns_2023 = graph.get_node("sales_returns").get_value("2023")
    returns_2024 = graph.get_node("sales_returns").get_value("2024")
    data.append(
        {
            "Section": "Revenue",
            "Line Item": "Less: Sales Returns",
            "2023": abs(returns_2023),
            "2024": abs(returns_2024),
            "Is Contra": True,
        }
    )

    discounts_2023 = graph.get_node("sales_discounts").get_value("2023")
    discounts_2024 = graph.get_node("sales_discounts").get_value("2024")
    data.append(
        {
            "Section": "Revenue",
            "Line Item": "Less: Sales Discounts",
            "2023": abs(discounts_2023),
            "2024": abs(discounts_2024),
            "Is Contra": True,
        }
    )

    data.append(
        {
            "Section": "Revenue",
            "Line Item": "Net Revenue",
            "2023": graph.calculate("net_revenue", "2023"),
            "2024": graph.calculate("net_revenue", "2024"),
            "Is Contra": False,
        }
    )

    # Create DataFrame
    df = pd.DataFrame(data)

    # Format the display
    def format_value(row: pd.Series) -> pd.Series:
        value_2023 = row["2023"]
        value_2024 = row["2024"]

        if row["Is Contra"]:
            # Show contra items in parentheses
            row["2023"] = f"({value_2023:,.0f})"
            row["2024"] = f"({value_2024:,.0f})"
        else:
            row["2023"] = f"{value_2023:,.0f}"
            row["2024"] = f"{value_2024:,.0f}"

        return row

    df_display = df.apply(format_value, axis=1)

    logger.info("Financial Statement with Contra Items:")
    logger.info(df_display[["Section", "Line Item", "2023", "2024"]].to_string(index=False))


def main():
    """Run all contra item demonstrations."""
    try:
        logger.info("Financial Statement Model - Simple Contra Items Demo")
        logger.info("=" * 70)

        # Run demonstrations
        demo_contra_display_styles()
        demo_calculation_accuracy()
        demo_dataframe_output()

        logger.info("\n=== Demo Complete ===")
        logger.info("\nKey takeaways:")
        logger.info("1. Contra items are stored as negative values in the graph")
        logger.info("2. Display formatting is separate from calculation logic")
        logger.info("3. Multiple display styles are supported (parentheses, brackets, etc.)")
        logger.info("4. Calculations work correctly with negative values")
        logger.info("5. DataFrames can show contra items with appropriate formatting")

    except Exception:
        logger.exception("Error during demo")


if __name__ == "__main__":
    main()
