"""This example demonstrates using the detailed test_statement.yaml configuration.

It includes:
- Loading the complex statement configuration.
- Populating a graph with corresponding sample data.
- Generating the statement DataFrame based on the config.
"""

import sys
import pandas as pd
from fin_statement_model.core.errors import FinancialModelError

from fin_statement_model.io import read_data
from fin_statement_model.statements import create_statement_dataframe
from fin_statement_model.io import write_data  # Import the forecaster
from fin_statement_model.forecasting.forecaster import StatementForecaster

# --- 1. Setup ---

# Hardcoded paths (as modified by user)
md_output_path = (
    "/Users/joneickmeier/projects/fin_statement_model/examples/scripts/output/test_statement.md"
)
TEST_CONFIG_PATH = (
    "/Users/joneickmeier/projects/fin_statement_model/examples/scripts/configs/test_statement.yaml"
)

# --- 2. Sample Data ---

# Sample historical data matching node_ids in test_statement.yaml
# Note: The keys must match the 'node_id' or 'metric_id'/'inputs' references
historical_data = {
    # Node ID: { Period: Value }
    # Add a 2021 data point for better historical average calculations
    "core.cash": {"2021": 90.0, "2022": 100.0, "2023": 120.0},
    "core.accounts_receivable": {"2021": 180.0, "2022": 200.0, "2023": 250.0},
    "core.ppe": {"2021": 480.0, "2022": 500.0, "2023": 550.0},
    "core.accounts_payable": {"2021": 140.0, "2022": 150.0, "2023": 180.0},
    "core.debt": {"2021": 290.0, "2022": 300.0, "2023": 320.0},
    "core.common_stock": {"2021": 100.0, "2022": 100.0, "2023": 100.0},
    "core.prior_retained_earnings": {"2021": 80.0, "2022": 100.0, "2023": 125.0},
    "core.dividends": {"2021": -8.0, "2022": -10.0, "2023": -15.0},
    "core.revenue": {"2021": 900.0, "2022": 1000.0, "2023": 1200.0},
    "core.cogs": {"2021": -350.0, "2022": -400.0, "2023": -500.0},
    "core.opex": {"2021": -280.0, "2022": -300.0, "2023": -350.0},
}

# --- 3. Graph Creation and Initial Data Loading ---

# Restore try-except block
try:
    print("Creating graph and loading initial data...")
    graph = read_data(format_type="dict", source=historical_data)
    print(f"Graph created with initial periods: {graph.periods}")
except FinancialModelError as e:
    print(f"Error creating graph or loading initial data: {e}", file=sys.stderr)
    sys.exit(1)


# --- 3b. Forecasting Setup ---
print("Setting up forecasting...")

historical_periods = sorted(list(graph.periods))
forecast_periods = ["2024", "2025", "2026", "2027", "2028"]  # Hardcoded as per user changes
all_periods = sorted(historical_periods + forecast_periods)

print(f"Historical periods: {historical_periods}")
print(f"Forecast periods: {forecast_periods}")


# Define forecast configurations using node IDs from historical_data
forecast_configs = {
    "core.cash": {"method": "simple", "config": 0.05},  # Fixed 5% growth
    "core.accounts_receivable": {"method": "historical_growth"},  # Average historical
    "core.ppe": {"method": "simple", "config": 0.02},  # Fixed 2% growth
    "core.accounts_payable": {
        "method": "curve",
        "config": [0.04, 0.03, 0.03, 0.02, 0.02],
    },  # Declining curve
    "core.debt": {"method": "simple", "config": 0.0},  # Assume flat debt
    "core.common_stock": {"method": "simple", "config": 0.0},  # Assume flat common stock
    "core.prior_retained_earnings": {
        "method": "simple",
        "config": 0.0,
    },  # Usually calculated, but forecast base if needed
    "core.dividends": {"method": "historical_growth"},  # Grow based on historical trend
    "core.revenue": {
        "method": "curve",
        "config": [0.10, 0.09, 0.08, 0.07, 0.06],
    },  # Declining revenue growth
    "core.cogs": {"method": "historical_growth"},  # COGS based on historical growth
    "core.opex": {
        "method": "statistical",
        "config": {
            "distribution": "normal",
            "params": {"mean": 0.03, "std": 0.015},  # Normal dist around 3% mean
        },
    },
    # Note: Items calculated by metrics (like retained_earnings) or statement calculations
    # do not need explicit forecast configs here if their inputs are forecasted.
}

# Use the StatementForecaster
# Restore try-except block
forecaster = StatementForecaster(fsg=graph)  # fsg likely stands for financial statement graph
print(f"Applying forecasts for periods: {forecast_periods}")

# Apply the forecasts using the defined configs
forecaster.create_forecast(
    forecast_periods=forecast_periods,
    node_configs=forecast_configs,
    historical_periods=historical_periods,
)

# --- 4. Statement Generation ---

# Restore try-except block
statement_df = create_statement_dataframe(
    graph=graph,
    config_path_or_dir=str(TEST_CONFIG_PATH),  # Pass the path to the config file
    format_kwargs={
        "should_apply_signs": True,  # Apply sign conventions from config
        "number_format": ",.1f",  # Format numbers with commas, 1 decimal place
    },
)

with pd.option_context(
    "display.max_rows", None, "display.max_columns", None, "display.width", 1000
):
    print(statement_df.to_string(index=False))

# Write output data
write_data(
    format_type="markdown",
    graph=graph,
    target=str(md_output_path),
    statement_config_path=str(TEST_CONFIG_PATH),
    historical_periods=historical_periods,
    forecast_configs=forecast_configs,
)
