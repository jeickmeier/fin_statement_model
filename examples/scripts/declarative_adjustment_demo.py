#!/usr/bin/env python3
"""Demonstration of Declarative Adjustment Handling in Statement Configurations.

This script shows how to use the new declarative adjustment handling feature
that allows specifying default adjustment filters directly in statement
configuration files.
"""

import sys
from typing import Any
import pandas as pd

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.adjustments.models import (
    AdjustmentFilter,
    AdjustmentType,
)
from fin_statement_model.statements import (
    StatementStructureBuilder,
    StatementConfig,
    StatementFormatter,
)


def create_sample_graph_with_adjustments() -> Graph:
    """Create a sample graph with nodes and adjustments for demonstration."""
    graph = Graph()

    # Add base data nodes
    graph.add_financial_statement_item(
        "revenue_gross", {"2023Q1": 1000, "2023Q2": 1100, "2023Q3": 1200}
    )
    graph.add_financial_statement_item(
        "revenue_deductions", {"2023Q1": 50, "2023Q2": 55, "2023Q3": 60}
    )
    graph.add_financial_statement_item(
        "cogs_materials", {"2023Q1": 300, "2023Q2": 330, "2023Q3": 360}
    )
    graph.add_financial_statement_item(
        "cogs_labor", {"2023Q1": 200, "2023Q2": 220, "2023Q3": 240}
    )
    graph.add_financial_statement_item(
        "opex_salaries", {"2023Q1": 150, "2023Q2": 155, "2023Q3": 160}
    )

    # Add some adjustments
    # Budget adjustments for revenue
    graph.add_adjustment(
        node_name="revenue_gross",
        period="2023Q1",
        value=50,
        adj_type=AdjustmentType.ADDITIVE,
        tags={"budget", "forecast"},
        reason="Budget increase for Q1",
    )
    graph.add_adjustment(
        node_name="revenue_gross",
        period="2023Q2",
        value=75,
        adj_type=AdjustmentType.ADDITIVE,
        tags={"budget", "forecast"},
        reason="Budget increase for Q2",
    )
    # Management estimates for labor
    graph.add_adjustment(
        node_name="cogs_labor",
        period="2023Q1",
        value=20,
        adj_type=AdjustmentType.ADDITIVE,
        tags={"management", "estimate"},
        reason="Management labor cost estimate",
    )
    # Approved adjustments for materials
    graph.add_adjustment(
        node_name="cogs_materials",
        period="2023Q1",
        value=-10,
        adj_type=AdjustmentType.ADDITIVE,
        tags={"approved"},
        reason="Approved material cost reduction",
    )
    # Preliminary adjustment (should be excluded in some views)
    graph.add_adjustment(
        node_name="revenue_deductions",
        period="2023Q1",
        value=5,
        adj_type=AdjustmentType.ADDITIVE,
        tags={"preliminary"},
        reason="Preliminary adjustment",
    )

    return graph


def create_sample_config() -> dict[str, Any]:
    """Create a sample statement configuration with declarative adjustment filters."""
    config_data = {
        "id": "demo_income_statement",
        "name": "Demo Income Statement with Declarative Adjustments",
        "description": "Demonstrates declarative adjustment handling",
        "sections": [
            {
                "id": "revenue_section",
                "name": "Revenue",
                "description": "Revenue items with budget/forecast adjustments",
                # Section-level filter: show budget and forecast adjustments
                "default_adjustment_filter": {
                    "include_tags": ["budget", "forecast"],
                    "exclude_tags": ["preliminary"],
                },
                "items": [
                    {
                        "type": "line_item",
                        "id": "gross_revenue",
                        "name": "Gross Revenue",
                        "node_id": "revenue_gross",
                        "description": "Uses section filter: budget/forecast, excludes preliminary",
                        # Inherits section filter
                    },
                    {
                        "type": "line_item",
                        "id": "revenue_deductions",
                        "name": "Revenue Deductions",
                        "node_id": "revenue_deductions",
                        "sign_convention": -1,
                        "description": "Override to show no adjustments (actuals only)",
                        # Override section filter - show actuals only
                        "default_adjustment_filter": [],
                    },
                    {
                        "type": "calculated",
                        "id": "net_revenue",
                        "name": "Net Revenue",
                        "description": "Calculated item using section filter",
                        "calculation": {
                            "type": "subtraction",
                            "inputs": ["gross_revenue", "revenue_deductions"],
                        },
                        # Uses section filter by inheritance
                    },
                ],
            },
            {
                "id": "cost_section",
                "name": "Cost of Goods Sold",
                "description": "Cost items with different adjustment strategies",
                # Section-level filter: approved adjustments only
                "default_adjustment_filter": {"include_tags": ["approved"]},
                "items": [
                    {
                        "type": "line_item",
                        "id": "material_costs",
                        "name": "Material Costs",
                        "node_id": "cogs_materials",
                        "description": "Uses section filter: approved adjustments only",
                        # Inherits section filter: approved only
                    },
                    {
                        "type": "line_item",
                        "id": "labor_costs",
                        "name": "Direct Labor",
                        "node_id": "cogs_labor",
                        "description": "Override to show management estimates",
                        # Override section filter - show management estimates
                        "default_adjustment_filter": ["management", "estimate"],
                    },
                    {
                        "type": "calculated",
                        "id": "total_cogs",
                        "name": "Total COGS",
                        "description": "Sum of materials and labor",
                        "calculation": {
                            "type": "addition",
                            "inputs": ["material_costs", "labor_costs"],
                        },
                        # Uses section filter: approved only
                    },
                ],
            },
            {
                "id": "other_section",
                "name": "Other Items",
                "description": "Items with no section-level filter",
                # No section-level filter specified
                "items": [
                    {
                        "type": "line_item",
                        "id": "salaries",
                        "name": "Salaries",
                        "node_id": "opex_salaries",
                        "description": "No adjustments - shows actuals only",
                        # No item or section filter - shows raw data
                    }
                ],
            },
        ],
    }

    return config_data


def demonstrate_declarative_adjustments():
    """Demonstrate the declarative adjustment handling feature."""
    print("=" * 80)
    print("Declarative Adjustment Handling Demonstration")
    print("=" * 80)

    # Create sample data
    graph = create_sample_graph_with_adjustments()
    config_data = create_sample_config()

    print("\n1. CONFIGURATION OVERVIEW")
    print("-" * 40)
    print(f"Statement: {config_data['name']}")
    print(f"Sections: {len(config_data['sections'])}")

    for section in config_data["sections"]:
        print(f"\n  Section: {section['name']}")
        section_filter = section.get("default_adjustment_filter")
        if section_filter:
            print(f"    Section Filter: {section_filter}")
        else:
            print("    Section Filter: None")

        for item in section["items"]:
            item_filter = item.get("default_adjustment_filter")
            print(
                f"    - {item['name']}: {item_filter if item_filter is not None else 'Inherits section filter'}"
            )

    # Build statement structure
    config = StatementConfig(config_data)
    validation_errors = config.validate_config()

    if validation_errors:
        print(f"\nConfiguration validation errors: {validation_errors}")
        return

    builder = StatementStructureBuilder()
    statement = builder.build(config)
    formatter = StatementFormatter(statement)

    print("\n2. DATA FETCHING WITH DEFAULT FILTERS")
    print("-" * 40)

    # Generate dataframe using default filters from configuration
    df_with_defaults = formatter.generate_dataframe(
        graph=graph, include_empty_items=True, include_metadata_cols=True
    )

    print("Generated DataFrame with default adjustment filters:")
    print(df_with_defaults.to_string())

    print("\n3. OVERRIDE WITH GLOBAL FILTER")
    print("-" * 40)

    # Override all default filters with a global filter
    global_filter = AdjustmentFilter(include_tags={"management"})
    df_with_override = formatter.generate_dataframe(
        graph=graph,
        adjustment_filter=global_filter,  # Overrides all defaults
        include_empty_items=True,
        include_metadata_cols=True,
    )

    print("Generated DataFrame with global filter override (management only):")
    print(df_with_override.to_string())

    print("\n4. RAW DATA (NO ADJUSTMENTS)")
    print("-" * 40)

    # Show raw data without any adjustments
    empty_filter = AdjustmentFilter()  # Empty filter
    df_raw = formatter.generate_dataframe(
        graph=graph,
        adjustment_filter=empty_filter,
        include_empty_items=True,
        include_metadata_cols=True,
    )

    print("Generated DataFrame with no adjustments (raw data):")
    print(df_raw.to_string())

    print("\n5. FILTER ANALYSIS")
    print("-" * 40)

    print("Examining default filters in the built statement structure:")

    for section in statement.sections:
        print(f"\nSection '{section.name}':")
        print(f"  Default filter: {section.default_adjustment_filter}")

        for item in section.items:
            if hasattr(item, "default_adjustment_filter"):
                print(f"  Item '{item.name}': {item.default_adjustment_filter}")

    print("\n6. COMPARISON SUMMARY")
    print("-" * 40)

    # Compare key values across different filter scenarios
    comparison_data = [
        {
            "Period": period,
            "Gross Revenue (Default)": (
                df_with_defaults.loc[
                    df_with_defaults["ID"] == "gross_revenue", period
                ].iloc[0]
                if len(df_with_defaults.loc[df_with_defaults["ID"] == "gross_revenue"])
                > 0
                else "N/A"
            ),
            "Gross Revenue (Raw)": (
                df_raw.loc[df_raw["ID"] == "gross_revenue", period].iloc[0]
                if len(df_raw.loc[df_raw["ID"] == "gross_revenue"]) > 0
                else "N/A"
            ),
            "Labor Costs (Default)": (
                df_with_defaults.loc[
                    df_with_defaults["ID"] == "labor_costs", period
                ].iloc[0]
                if len(df_with_defaults.loc[df_with_defaults["ID"] == "labor_costs"])
                > 0
                else "N/A"
            ),
            "Labor Costs (Management)": (
                df_with_override.loc[
                    df_with_override["ID"] == "labor_costs", period
                ].iloc[0]
                if len(df_with_override.loc[df_with_override["ID"] == "labor_costs"])
                > 0
                else "N/A"
            ),
        }
        for period in ["2023Q1", "2023Q2", "2023Q3"]
        if period in df_with_defaults.columns
    ]

    comparison_df = pd.DataFrame(comparison_data)
    print("Value Comparison Across Filter Scenarios:")
    print(comparison_df.to_string(index=False))

    print("\n" + "=" * 80)
    print("Demonstration Complete!")
    print("\nKey Takeaways:")
    print("- Each item can have its own default adjustment filter")
    print("- Section-level filters apply to all items that don't override")
    print("- Global filters passed to generate_dataframe() override all defaults")
    print("- Filter precedence: Global > Item > Section > None")
    print("=" * 80)


if __name__ == "__main__":
    try:
        demonstrate_declarative_adjustments()
    except Exception as e:
        print(f"Demonstration failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
