"""This example demonstrates using the detailed test_statement.yaml configuration.

and applying adjustments before generating the final statement.

It includes:
- Loading the complex statement configuration.
- Populating a graph with corresponding sample data.
- Running forecasts.
- Adding adjustments to specific nodes/periods.
- Generating the statement DataFrame showing the impact of adjustments.
"""

import sys
import logging
from pathlib import Path
import yaml

from fin_statement_model.core.errors import FinancialModelError
from fin_statement_model.core.adjustments.models import AdjustmentType

from fin_statement_model.io import read_data
from fin_statement_model.statements import create_statement_dataframe
from fin_statement_model.forecasting.forecaster import StatementForecaster
from fin_statement_model.statements.orchestration import export_statements_to_excel

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- 1. Setup ---

# Use relative paths assuming script is run from workspace root
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]  # Adjust depth if needed
CONFIG_PATH = WORKSPACE_ROOT / "examples/scripts/configs/test_statement.yaml"
MD_OUTPUT_PATH = (
    WORKSPACE_ROOT / "examples/scripts/output/statement_with_adjustments.md"
)

if not CONFIG_PATH.is_file():
    logger.error(f"Configuration file not found: {CONFIG_PATH}")
    sys.exit(1)

MD_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# --- 2. Sample Data ---

# Sample historical data matching node_ids in test_statement.yaml
historical_data = {
    # Node ID: { Period: Value }
    "cash_and_equivalents": {"2021": 90.0, "2022": 100.0, "2023": 120.0},
    "accounts_receivable": {"2021": 180.0, "2022": 200.0, "2023": 250.0},
    "property_plant_equipment": {"2021": 480.0, "2022": 500.0, "2023": 550.0},
    "accounts_payable": {"2021": 140.0, "2022": 150.0, "2023": 180.0},
    "total_debt": {"2021": 290.0, "2022": 300.0, "2023": 320.0},
    "common_stock": {"2021": 100.0, "2022": 100.0, "2023": 100.0},
    "prior_retained_earnings": {"2021": 80.0, "2022": 100.0, "2023": 125.0},
    "dividends": {"2021": -8.0, "2022": -10.0, "2023": -15.0},
    "revenue": {"2021": 900.0, "2022": 1000.0, "2023": 1200.0},
    "cost_of_goods_sold": {"2021": -350.0, "2022": -400.0, "2023": -500.0},
    "operating_expenses": {"2021": -280.0, "2022": -300.0, "2023": -350.0},
    "interest_expense": {"2021": -20.0, "2022": -25.0, "2023": -30.0},
    "income_tax": {"2021": -70.0, "2022": -80.0, "2023": -95.0},
}

# --- 3. Create Graph with Data ---
# First, create a graph with our data nodes using the dict reader
try:
    logger.info("Creating graph and loading initial data...")
    graph = read_data(format_type="dict", source=historical_data)
    logger.info(f"Graph created with initial periods: {graph.periods}")
except FinancialModelError as e:
    logger.error(f"Error creating graph or loading initial data: {e}", exc_info=True)
    sys.exit(1)

# --- 4. Build Statement Structure and Populate Graph ---
# Use create_statement_dataframe to properly build the statement structure,
# populate the graph with calculation nodes, and generate the initial dataframe
try:
    logger.info(
        "Building statement structure and populating graph with calculation nodes..."
    )

    # Load statement config into memory
    raw_config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    raw_configs = {raw_config.get("id", "statement"): raw_config}
    initial_df_map = create_statement_dataframe(
        graph=graph,
        raw_configs=raw_configs,
        format_kwargs={
            "should_apply_signs": True,
            "number_format": ",.1f",
        },
    )
    initial_df = initial_df_map.get(list(raw_configs.keys())[0])

    logger.info("Statement structure built and graph populated with calculation nodes.")

except FinancialModelError as e:
    logger.error(f"Error building statement structure: {e}", exc_info=True)
    sys.exit(1)

# --- 5. Forecasting Setup ---
logger.info("Setting up forecasting...")

historical_periods = sorted(list(graph.periods))
forecast_periods = ["2024", "2025", "2026", "2027", "2028"]
all_periods = sorted(historical_periods + forecast_periods)

logger.info(f"Historical periods: {historical_periods}")
logger.info(f"Forecast periods: {forecast_periods}")

# Define forecast configurations using node IDs from historical_data
forecast_configs = {
    "cash_and_equivalents": {"method": "simple", "config": 0.05},
    "accounts_receivable": {"method": "historical_growth", "config": {}},
    "property_plant_equipment": {"method": "simple", "config": 0.02},
    "accounts_payable": {
        "method": "curve",
        "config": [0.04, 0.03, 0.03, 0.02, 0.02],
    },
    "total_debt": {"method": "simple", "config": 0.0},
    "common_stock": {"method": "simple", "config": 0.0},
    "prior_retained_earnings": {"method": "simple", "config": 0.0},
    "dividends": {"method": "historical_growth", "config": {}},
    "revenue": {"method": "curve", "config": [0.10, 0.09, 0.08, 0.07, 0.06]},
    "cost_of_goods_sold": {"method": "historical_growth", "config": {}},
    "operating_expenses": {
        "method": "statistical",
        "config": {"distribution": "normal", "params": {"mean": 0.03, "std": 0.015}},
    },
    "interest_expense": {"method": "historical_growth", "config": {}},
    "income_tax": {"method": "simple", "config": 0.02},
}

# Use the StatementForecaster
try:
    forecaster = StatementForecaster(fsg=graph)
    logger.info(f"Applying forecasts for periods: {forecast_periods}")
    # Apply the forecasts using the defined configs
    forecaster.create_forecast(
        forecast_periods=forecast_periods,
        node_configs=forecast_configs,
        historical_periods=historical_periods,
    )
    logger.info(f"Forecasting complete. Graph now includes periods: {graph.periods}")
except FinancialModelError as e:
    logger.error(f"Error during forecasting: {e}", exc_info=True)
    sys.exit(1)

# --- 6. Add Adjustments ---
logger.info("\n--- Adding Adjustments ---")

try:
    adj_id_1 = graph.add_adjustment(
        node_name="revenue",
        period="2023",  # Adjust historical data
        value=75.0,
        adj_type=AdjustmentType.ADDITIVE,
        reason="Late recognized revenue for 2023.",
        tags={"manual", "revenue_recognition"},
        user="AnalystX",
    )
    logger.info(f"Added additive adjustment {adj_id_1} for revenue 2023.")

    adj_id_2 = graph.add_adjustment(
        node_name="operating_expenses",
        period="2024",  # Adjust forecasted data
        value=-400.0,  # Note: OPEX is typically negative
        adj_type=AdjustmentType.REPLACEMENT,
        reason="Revised forecast for OPEX in 2024 based on restructuring.",
        tags={"forecast_revision", "restructuring"},
        user="AnalystY",
        priority=-10,
    )
    logger.info(f"Added replacement adjustment {adj_id_2} for operating_expenses 2024.")

except FinancialModelError as e:
    logger.error(f"Error adding adjustments: {e}", exc_info=True)
    sys.exit(1)

# --- 7. Regenerate Statement with Adjustments ---
logger.info("\n--- Generating Statement with Adjustments Applied ---")

try:
    # Regenerate with adjustments using same raw_configs
    statement_df_map = create_statement_dataframe(
        graph=graph,
        raw_configs=raw_configs,
        format_kwargs={
            "should_apply_signs": True,
            "number_format": ",.1f",
            "adjustment_filter": None,
            "add_is_adjusted_column": True,
        },
    )
    statement_df = statement_df_map.get(list(raw_configs.keys())[0])

    logger.info("Statement DataFrame generated successfully.")
    # Display the results
    logger.info("\n--- Statement DataFrame with Adjustments ---")
    logger.info(statement_df.to_string(index=False))

    # Export the statement to Excel using the modern helper function
    export_statements_to_excel(
        graph=graph,
        raw_configs=raw_configs,
        output_dir=str(MD_OUTPUT_PATH.parent),
        format_kwargs={
            "should_apply_signs": True,
            "number_format": ",.1f",
            "adjustment_filter": None,
            "add_is_adjusted_column": True,
        },
    )
except FinancialModelError as e:
    logger.error(f"Error generating statement dataframe: {e}", exc_info=True)
    sys.exit(1)
except FileNotFoundError:
    logger.error(
        f"Statement configuration file not found: {CONFIG_PATH}", exc_info=True
    )
    sys.exit(1)

logger.info("\nExample complete.")
