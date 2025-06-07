"""Configuration System Demonstration.

This example shows how to use the centralized configuration system
in the fin_statement_model library.
"""

import logging
import os
from pathlib import Path
import tempfile

from fin_statement_model.config import get_config, update_config, reset_config, cfg
from fin_statement_model.io import read_data
from fin_statement_model.config.manager import generate_env_mappings

logger = logging.getLogger(__name__)


def demo_config_basics() -> None:
    """Demonstrate basic configuration usage."""
    print("=" * 60)
    print("CONFIGURATION BASICS")
    print("=" * 60)

    # Get current configuration
    config = get_config()

    print("Current Configuration Sources:")
    print(f"  Loaded from: {getattr(config, '_source', 'defaults')}")

    print("\nLogging Configuration:")
    print(f"  Level: {cfg('logging.level')}")
    print(f"  Format: {cfg('logging.format')[:50]}...")
    print(f"  Detailed: {cfg('logging.detailed')}")

    print("\nDisplay Configuration:")
    print(f"  Units: {cfg('display.default_units')}")
    print(f"  Currency Format: {cfg('display.default_currency_format')}")
    print(f"  Scale Factor: {cfg('display.scale_factor')}")

    print("\nValidation Configuration:")
    print(f"  Strict Mode: {cfg('validation.strict_mode')}")
    print(f"  Auto Standardize: {cfg('validation.auto_standardize_names')}")


def demo_runtime_updates() -> None:
    """Show how to update configuration at runtime."""
    print("\n" + "=" * 60)
    print("RUNTIME CONFIGURATION UPDATES")
    print("=" * 60)

    # Save original config
    original_units = get_config().display.default_units

    # Update configuration
    print("Updating display configuration...")
    update_config(
        {
            "display": {
                "default_units": "EUR Thousands",
                "scale_factor": 0.001,
                "default_currency_format": ",.2f",
            }
        }
    )

    config = get_config()
    print("\nUpdated Display Config:")
    print(f"  Units: {config.display.default_units}")
    print(f"  Scale Factor: {config.display.scale_factor}")
    print(f"  Format: {config.display.default_currency_format}")

    # Demonstrate effect on data display
    sample_value = 1234567.89
    scaled_value = sample_value * config.display.scale_factor
    print("\nExample value formatting:")
    print(f"  Original: ${sample_value:,.2f}")
    print(
        f"  Scaled: {scaled_value:{config.display.default_currency_format}} {config.display.default_units}"
    )

    # Reset to original
    update_config({"display": {"default_units": original_units}})


def demo_environment_variables() -> None:
    """Show how environment variables affect configuration."""
    print("\n" + "=" * 60)
    print("ENVIRONMENT VARIABLE CONFIGURATION")
    print("=" * 60)

    print("Supported environment variables (sample):")
    env_mappings = generate_env_mappings(get_config().__class__)
    for env_key, path in sorted(env_mappings.items())[:8]:
        print(f"  {env_key} -> {'.'.join(path)}")

    # Demonstrate setting an environment variable
    print("\nDemo: Setting FSM_DISPLAY_UNITS...")
    os.environ["FSM_DISPLAY_UNITS"] = "GBP Millions"

    # Reset config to pick up environment variable
    reset_config()
    config = get_config()

    print(f"Display units after reset: {config.display.default_units}")

    # Clean up
    del os.environ["FSM_DISPLAY_UNITS"]
    reset_config()


def demo_config_file() -> None:
    """Show how to use a configuration file."""
    print("\n" + "=" * 60)
    print("CONFIGURATION FILE USAGE")
    print("=" * 60)

    # Create a sample config file
    config_content = """
# Example fin_statement_model.config settings
logging:
  level: INFO
  detailed: true

display:
  default_units: "USD Millions"
  scale_factor: 0.000001
  default_currency_format: ",.1f"
  default_percentage_format: ".1%"
  hide_zero_rows: true

validation:
  strict_mode: true
  auto_standardize_names: true
  check_balance_sheet_balance: true
  balance_tolerance: 0.01

io:
  default_excel_sheet: "FinancialData"
  skip_invalid_rows: false
  strict_validation: true

forecasting:
  default_method: "historical_growth"
  default_periods: 5
  default_growth_rate: 0.05
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(config_content)
        config_path = f.name

    print(f"Created config file: {config_path}")
    print("\nConfig file content (excerpt):")
    print(config_content[:300] + "...")

    # Load from file
    from fin_statement_model.config import Config

    loaded_config = Config.from_file(Path(config_path))
    file_config = loaded_config.to_dict()

    print("\nLoaded configuration sections:")
    for section in file_config:
        print(f"  - {section}")

    # Apply the file config
    update_config(file_config)
    config = get_config()

    print("\nApplied configuration:")
    print(f"  Display units: {config.display.default_units}")
    print(f"  Validation strict mode: {config.validation.strict_mode}")
    print(f"  Default forecast method: {config.forecasting.default_method}")

    # Clean up
    os.unlink(config_path)
    reset_config()


def demo_config_in_action() -> None:
    """Demonstrate config affecting actual operations."""
    print("\n" + "=" * 60)
    print("CONFIGURATION IN ACTION")
    print("=" * 60)

    # Create sample data
    sample_data = {
        "revenue": {"2022": 1000000, "2023": 1200000},
        "expenses": {"2022": 600000, "2023": 700000},
        "net_income": {"2022": 400000, "2023": 500000},
    }

    # Test 1: Default configuration
    print("Test 1: Default Configuration")
    print(f"  Units: {cfg('display.default_units')}")

    graph = read_data(format_type="dict", source=sample_data)
    revenue_node = graph.get_node("revenue")
    if revenue_node is None:
        print("  Error: Revenue node not found")
        return
    revenue_2023 = revenue_node.get_value("2023")
    print(f"  Revenue 2023: ${revenue_2023:,.2f}")

    # Test 2: European configuration
    print("\nTest 2: European Configuration")
    update_config(
        {
            "display": {
                "default_units": "EUR Thousands",
                "scale_factor": 0.001,
                "default_currency_format": ",.2f",
                "thousands_separator": ".",
                "decimal_separator": ",",
            }
        }
    )

    scaled_revenue = revenue_2023 * cfg("display.scale_factor")
    print(f"  Revenue 2023: {scaled_revenue:,.2f} {cfg('display.default_units')}")

    # Test 3: Validation configuration
    print("\nTest 3: Validation Configuration")
    update_config({"validation": {"strict_mode": True, "warn_on_non_standard": True}})

    # Try to add a node with non-standard name
    from fin_statement_model.io.validation import UnifiedNodeValidator

    validator = UnifiedNodeValidator(
        strict_mode=cfg("validation.strict_mode"),
        warn_on_non_standard=cfg("validation.warn_on_non_standard"),
    )

    test_names = ["Revenue 2023!", "net_income", "EBITDA"]
    print(f"  Validating node names with strict={cfg('validation.strict_mode')}:")
    for name in test_names:
        result = validator.validate(name)
        print(f"    {name}: {'✓' if result.is_valid else '✗'} {result.message}")

    # Reset
    reset_config()


def demo_config_serialization() -> None:
    """Show how to save and share configurations."""
    print("\n" + "=" * 60)
    print("CONFIGURATION SERIALIZATION")
    print("=" * 60)

    # Create a custom configuration
    update_config(
        {
            "display": {
                "default_units": "JPY Millions",
                "scale_factor": 0.000001,
                "default_currency_format": ",.0f",
            },
            "validation": {"strict_mode": False},
        }
    )

    config = get_config()

    # Export to dict
    config_dict = config.to_dict()
    print("Configuration as dictionary:")
    print(f"  Keys: {list(config_dict.keys())}")

    # Export to YAML
    yaml_str = config.to_yaml()
    print("\nConfiguration as YAML (first 200 chars):")
    print(yaml_str[:200] + "...")

    # Save to file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_str)
        saved_path = f.name

    print(f"\nSaved configuration to: {saved_path}")

    # Load it back
    from fin_statement_model.config import Config

    loaded_config = Config.from_file(Path(saved_path))

    print("\nLoaded configuration:")
    print(f"  Display units: {loaded_config.display.default_units}")

    # Clean up
    os.unlink(saved_path)
    reset_config()

    print("• Configurations can be serialized and shared")
    print("• Slim config API under fin_statement_model.config for concise access")


def main() -> None:
    """Run all configuration demonstrations."""
    print("FINANCIAL STATEMENT MODEL - CONFIGURATION SYSTEM DEMO")
    print("=" * 80)

    # Run demonstrations
    demo_config_basics()
    demo_runtime_updates()
    demo_environment_variables()
    demo_config_file()
    demo_config_in_action()
    demo_config_serialization()

    print("\n" + "=" * 80)
    print("CONFIGURATION DEMO COMPLETE")
    print("=" * 80)
    print("\nKey Takeaways:")
    print("• Configuration can be loaded from multiple sources with clear precedence")
    print("• Runtime updates allow dynamic behavior changes")
    print("• Environment variables provide deployment flexibility")
    print("• Configuration files enable reproducible setups")
    print("• All subsystems respect the centralized configuration")
    print("• Configurations can be serialized and shared")
    print("• Slim config API under fin_statement_model.config for concise access")


if __name__ == "__main__":
    main()
