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
import logging  # Added logging
import pandas as pd
from pathlib import Path  # Added Path

from fin_statement_model.core.errors import FinancialModelError
from fin_statement_model.core.adjustments.models import (
    AdjustmentType,
)  # Added AdjustmentType

from fin_statement_model.io import read_data
from fin_statement_model.statements import create_statement_dataframe
from fin_statement_model.forecasting.forecaster import StatementForecaster
from fin_statement_model.io import write_data

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- 1. Setup ---

# Use relative paths assuming script is run from workspace root
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]  # Adjust depth if needed
CONFIG_PATH = WORKSPACE_ROOT / "fin_statement_model/statements/config/mappings/test_statement.yaml"
MD_OUTPUT_PATH = WORKSPACE_ROOT / "examples/scripts/output/statement_with_adjustments.md"

if not CONFIG_PATH.is_file():
    logger.error(f"Configuration file not found: {CONFIG_PATH}")
    sys.exit(1)

MD_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# --- 2. Sample Data ---

# Sample historical data matching node_ids in test_statement.yaml
historical_data = {
    # Node ID: { Period: Value }
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

try:
    logger.info("Creating graph and loading initial data...")
    graph = read_data(format_type="dict", source=historical_data)
    logger.info(f"Graph created with initial periods: {graph.periods}")
except FinancialModelError as e:
    logger.error(f"Error creating graph or loading initial data: {e}", exc_info=True)
    sys.exit(1)

# --- 4. Forecasting Setup ---
logger.info("Setting up forecasting...")

historical_periods = sorted(list(graph.periods))
forecast_periods = ["2024", "2025", "2026", "2027", "2028"]
all_periods = sorted(historical_periods + forecast_periods)

logger.info(f"Historical periods: {historical_periods}")
logger.info(f"Forecast periods: {forecast_periods}")

# Define forecast configurations using node IDs from historical_data
forecast_configs = {
    "core.cash": {"method": "simple", "config": 0.05},
    "core.accounts_receivable": {"method": "historical_growth"},
    "core.ppe": {"method": "simple", "config": 0.02},
    "core.accounts_payable": {
        "method": "curve",
        "config": [0.04, 0.03, 0.03, 0.02, 0.02],
    },
    "core.debt": {"method": "simple", "config": 0.0},
    "core.common_stock": {"method": "simple", "config": 0.0},
    "core.prior_retained_earnings": {"method": "simple", "config": 0.0},
    "core.dividends": {"method": "historical_growth"},
    "core.revenue": {"method": "curve", "config": [0.10, 0.09, 0.08, 0.07, 0.06]},
    "core.cogs": {"method": "historical_growth"},
    "core.opex": {
        "method": "statistical",
        "config": {"distribution": "normal", "params": {"mean": 0.03, "std": 0.015}},
    },
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

# --- 5. Manually Add Gross Profit Node (Workaround) ---
logger.info("\n--- Manually Adding Gross Profit Node (Workaround) ---")
try:
    revenue_node = graph.get_node("core.revenue")
    cogs_node = graph.get_node("core.cogs")

    if revenue_node and cogs_node:
        # Use the calculate_metric helper function with proper node mapping
        from fin_statement_model.core.metrics import calculate_metric
        from fin_statement_model.core.nodes import FinancialStatementItemNode

        # Create a mapping for the metric inputs to actual node names
        metric_data_nodes = {
            "revenue": revenue_node,
            "cost_of_goods_sold": cogs_node,
        }

        # Calculate gross profit for all periods and create a node
        gross_profit_values = {}
        for period in graph.periods:
            try:
                gross_profit_values[period] = calculate_metric(
                    "gross_profit", metric_data_nodes, period
                )
            except Exception as e:
                logger.warning(f"Could not calculate gross_profit for period {period}: {e}")

        # Create a FinancialStatementItemNode with the calculated values
        gp_node = FinancialStatementItemNode(name="gross_profit", values=gross_profit_values)
        graph.add_node(gp_node)
        logger.info("Added 'gross_profit' node using calculate_metric helper to the graph.")
    else:
        logger.warning(
            "Skipping manual gross_profit node addition: Input nodes (core.revenue, core.cogs) not found."
        )

except FinancialModelError as e:
    logger.error(f"Error manually adding gross_profit node: {e}", exc_info=True)
    # Continue execution even if this fails, to see subsequent errors if any

# --- 6. Add Adjustments ---
logger.info("\n--- Adding Adjustments ---")

try:
    adj_id_1 = graph.add_adjustment(
        node_name="core.revenue",
        period="2023",  # Adjust historical data
        value=75.0,
        adj_type=AdjustmentType.ADDITIVE,
        reason="Late recognized revenue for 2023.",
        tags={"manual", "revenue_recognition"},
        user="AnalystX",
    )
    logger.info(f"Added additive adjustment {adj_id_1} for core.revenue 2023.")

    adj_id_2 = graph.add_adjustment(
        node_name="core.opex",
        period="2024",  # Adjust forecasted data
        value=-400.0,  # Note: OPEX is typically negative
        adj_type=AdjustmentType.REPLACEMENT,
        reason="Revised forecast for OPEX in 2024 based on restructuring.",
        tags={"forecast_revision", "restructuring"},
        user="AnalystY",
        priority=-10,
    )
    logger.info(f"Added replacement adjustment {adj_id_2} for core.opex 2024.")

except FinancialModelError as e:
    logger.error(f"Error adding adjustments: {e}", exc_info=True)
    sys.exit(1)

# --- 7. Statement Generation with Adjustments ---
logger.info("\n--- Generating Statement with Adjustments Applied ---")

try:
    statement_df = create_statement_dataframe(
        graph=graph,
        config_path_or_dir=str(CONFIG_PATH),
        format_kwargs={
            "should_apply_signs": True,
            "number_format": ",.1f",
            "adjustment_filter": None,  # Apply default scenario adjustments
            "add_is_adjusted_column": True,  # Show which values were adjusted
        },
    )

    logger.info("Statement DataFrame generated successfully.")
    with pd.option_context(
        "display.max_rows", None, "display.max_columns", None, "display.width", 1000
    ):
        print("\n--- Statement DataFrame with Adjustments ---")
        print(statement_df.to_string(index=False))

except FinancialModelError as e:
    logger.error(f"Error generating statement dataframe: {e}", exc_info=True)
    sys.exit(1)
except FileNotFoundError:
    logger.error(f"Statement configuration file not found: {CONFIG_PATH}", exc_info=True)
    sys.exit(1)

# --- 8. Write Output Data --- # Renumbered and Commented Out
logger.info(f"\nWriting output markdown to: {MD_OUTPUT_PATH}")
try:
    # Note: write_data might not inherently know adjustments were applied.
    # The markdown output will reflect the *final* graph state.
    # This currently fails due to MarkdownWriter requiring statement_config_path
    # which is not allowed by its config schema.
    write_data(
        format_type="markdown",
        graph=graph,
        target=str(MD_OUTPUT_PATH),
        statement_config_path=str(CONFIG_PATH),  # Causes validation error
        historical_periods=historical_periods,
        forecast_periods=forecast_periods,
        adjustment_filter=None,
        forecast_configs=forecast_configs,
    )
    logger.info("Markdown output written successfully.")
except Exception as e:
    logger.error(f"Error writing markdown output: {e}", exc_info=True)
    # Decide if this is critical enough to exit

logger.info("\nExample complete.")
