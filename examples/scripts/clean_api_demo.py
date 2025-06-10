"""Clean API Demonstration.

This example shows how the library uses centralized configuration
to provide a clean, simple API without requiring constant parameter passing.
"""

import logging
from fin_statement_model.config import get_config, update_config
from fin_statement_model.io import read_data
from fin_statement_model.io.validation import UnifiedNodeValidator
from fin_statement_model.statements import create_statement_dataframe
from fin_statement_model.core.nodes import (
    FixedGrowthForecastNode,
    standard_node_registry,
)

logger = logging.getLogger(__name__)


def main():
    """Demonstrate the clean API with automatic config usage."""
    print("=" * 80)
    print("CLEAN API DEMONSTRATION")
    print("Using centralized configuration for clean, simple code")
    print("=" * 80)

    # Set up some configuration
    update_config(
        {
            "display": {
                "default_units": "USD Millions",
                "scale_factor": 0.000001,
                "hide_zero_rows": True,
            },
            "validation": {"strict_mode": False, "auto_standardize_names": True},
            "forecasting": {"default_growth_rate": 0.05},  # 5% default growth
        }
    )

    config = get_config()
    print("\nCurrent Configuration:")
    print(f"  Display units: {config.display.default_units}")
    print(f"  Hide zero rows: {config.display.hide_zero_rows}")
    print(f"  Validation strict mode: {config.validation.strict_mode}")
    print(f"  Default growth rate: {config.forecasting.default_growth_rate}")

    # Sample data
    financial_data = {
        "revenue": {"2021": 100000000, "2022": 110000000, "2023": 121000000},
        "expenses": {"2021": 60000000, "2022": 65000000, "2023": 70000000},
        "net_income": {"2021": 40000000, "2022": 45000000, "2023": 51000000},
    }

    print("\n" + "=" * 60)
    print("AFTER: Clean API with automatic config usage")
    print("=" * 60)

    # The NEW way - clean and simple!

    # 1. Validation - automatically uses config defaults
    print("\n1. Node Validation (auto-uses config):")
    # Demo only: direct use of UnifiedNodeValidator; production code should use StatementConfig/StatementStructureBuilder for validation
    validator = UnifiedNodeValidator(standard_node_registry)  # That's it!

    result = validator.validate("gross revenue")
    print(f"   Validated 'gross revenue' -> '{result.standardized_name}'")
    print(
        f"   (Used config: strict_mode={validator.strict_mode}, "
        + f"auto_standardize={validator.auto_standardize})"
    )

    # 2. Data loading
    print("\n2. Loading Data:")
    graph = read_data(format_type="dict", source=financial_data)
    print(f"   Loaded {len(graph.nodes)} nodes")

    # 3. Forecasting - uses default growth rate
    print("\n3. Forecasting (auto-uses default growth rate):")
    revenue_node = graph.get_node("revenue")
    forecast = FixedGrowthForecastNode(
        revenue_node,
        "2023",
        ["2024", "2025"],
        # No growth_rate needed - uses config default!
    )
    print(f"   Created forecast with {forecast.growth_rate:.0%} growth (from config)")
    print(f"   2024 forecast: ${forecast.calculate('2024'):,.0f}")

    # 4. Statement formatting - automatically uses display config
    print("\n4. Statement Formatting (auto-uses display config):")

    # Define in-memory statement configuration
    statement_config = {
        "simple_income": {
            "id": "simple_income",
            "name": "Simple Income Statement",
            "sections": [
                {
                    "id": "main",
                    "name": "Income",
                    "items": [
                        {
                            "type": "line_item",
                            "id": "revenue",
                            "name": "Revenue",
                            "node_id": "revenue",
                        },
                        {
                            "type": "line_item",
                            "id": "expenses",
                            "name": "Expenses",
                            "node_id": "expenses",
                        },
                        {
                            "type": "line_item",
                            "id": "net_income",
                            "name": "Net Income",
                            "node_id": "net_income",
                        },
                    ],
                }
            ],
        }
    }

    # Create statement using in-memory config
    df_map = create_statement_dataframe(
        graph=graph,
        raw_configs=statement_config,
        format_kwargs={
            "should_apply_signs": True,
            "number_format": None,
        },
    )
    df = df_map["simple_income"]

    print("   Statement created with automatic config usage:")
    print(
        f"   - Scale factor: {config.display.scale_factor} (values in {config.display.default_units})"
    )
    print(f"   - Hide zero rows: {config.display.hide_zero_rows}")
    print(f"   - Number format: {config.display.default_number_format}")

    print("\n   Statement Output:")
    print(df.to_string(index=False))

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(
        """
The library now provides a much cleaner API by:

1. Using configuration defaults automatically
2. Only requiring overrides when needed
3. Reducing boilerplate code significantly
4. Making the code more readable and maintainable

Benefits:
✓ Less code to write and maintain
✓ Consistent behavior across the application
✓ Easy to change defaults globally
✓ Still flexible when you need overrides
"""
    )


if __name__ == "__main__":
    main()
