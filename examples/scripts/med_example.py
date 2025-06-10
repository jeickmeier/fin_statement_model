"""This example demonstrates the core capabilities of the fin_statement_model library.

It includes:
- Basic setup and configuration
- Historical statement generation
- Forecasting
- Exporting to Excel
"""

import logging
from pathlib import Path
import sys
import yaml
from typing import Any

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.errors import (
    FinancialModelError,
)

from fin_statement_model.io.exceptions import WriteError
from fin_statement_model.io import read_data
from fin_statement_model.statements import (
    create_statement_dataframe,
    export_statements_to_excel,
)
from fin_statement_model.forecasting.forecaster import StatementForecaster
from fin_statement_model.core.metrics.registry import metric_registry
from pathlib import Path as MetricPath
from fin_statement_model.statements.structure.builder import StatementStructureBuilder
from fin_statement_model.statements.registry import StatementRegistry
from fin_statement_model.statements.orchestration.orchestrator import populate_graph
from fin_statement_model.statements.orchestration.loader import (
    load_build_register_statements,
)

# --- 1. Setup ---

# Configure logging for visibility
logging.basicConfig(
    level=logging.WARNING, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
CONFIG_DIR = SCRIPT_DIR / "configs"
OUTPUT_DIR = SCRIPT_DIR / "output"

CONFIG_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logger.info(f"Using temporary config directory: {CONFIG_DIR}")
logger.info(f"Using temporary output directory: {OUTPUT_DIR}")

# --- 2. Configuration Files removed; using code-only StatementStructure in Step 4 ---

# --- 3. Initial Data Loading ---

# Sample historical data (Node IDs match those in YAML `node_id` fields)
historical_data = {
    # Node ID: { Period: Value }
    "Revenue": {"2022": 1000.0, "2023": 1200.0},
    "COGS": {"2022": -400.0, "2023": -500.0},
    "R&D": {"2022": -100.0, "2023": -120.0},
    "SG&A": {"2022": -200.0, "2023": -250.0},
    "Interest Expense": {"2022": -50.0, "2023": -60.0},
    "Taxes": {"2022": -75.0, "2023": -90.0},
    "D&A": {"2022": -30.0, "2023": -35.0},
    # Added entries for balance sheet example
    "core.cash": {"2022": 100.0, "2023": 120.0},
    "core.accounts_receivable": {"2022": 200.0, "2023": 250.0},
    "core.ppe": {"2022": 500.0, "2023": 550.0},
    "core.accounts_payable": {"2022": 150.0, "2023": 180.0},
    "core.debt": {"2022": 300.0, "2023": 320.0},
    "core.common_stock": {"2022": 100.0, "2023": 100.0},
    "core.prior_retained_earnings": {"2022": 130.0, "2023": 150.0},
    "core.dividends": {"2022": -20.0, "2023": -25.0},
}

# Create the core graph
graph = Graph()
graph = read_data(format_type="dict", source=historical_data)

# --- 4. Statement Generation (Historical) using file-based StatementStructure ---

# Define the income statement configuration as a Python dict
income_statement_config = {
    "id": "income_statement",
    "name": "Income Statement",
    "description": "Reports financial performance over a specific period.",
    "sections": [
        {
            "id": "revenue_section",
            "name": "Revenue",
            "items": [
                {
                    "id": "revenue",
                    "name": "Total Revenue",
                    "type": "line_item",
                    "node_id": "Revenue",
                    "sign_convention": 1,
                }
            ],
        },
        {
            "id": "cost_of_goods_sold",
            "name": "Cost of Goods Sold",
            "items": [
                {
                    "id": "cogs",
                    "name": "Cost of Goods Sold",
                    "type": "line_item",
                    "node_id": "COGS",
                    "sign_convention": -1,
                }
            ],
        },
        {
            "id": "gross_profit_section",
            "name": "Gross Profit",
            "items": [
                {
                    "id": "gross_profit",
                    "name": "Gross Profit",
                    "type": "metric",
                    "metric_id": "gross_profit",
                    "inputs": {"revenue": "revenue", "cost_of_goods_sold": "cogs"},
                    "sign_convention": 1,
                }
            ],
        },
    ],
}

# Save configuration to a temporary YAML file for consistency across examples
income_stmt_path = CONFIG_DIR / "income_statement.yaml"
with open(income_stmt_path, "w", encoding="utf-8") as f:
    yaml.safe_dump(income_statement_config, f, sort_keys=False)

# Load the YAML back into memory and prepare for dataframe creation
raw_config = yaml.safe_load(income_stmt_path.read_text(encoding="utf-8"))
raw_configs = {raw_config.get("id", "statement"): raw_config}

# Build the statement, populate the graph, and generate the dataframe
df_map = create_statement_dataframe(
    graph=graph,
    raw_configs=raw_configs,
    format_kwargs={
        "should_apply_signs": True,
        "number_format": ",.0f",
    },
)

income_statement_df_hist = df_map[raw_config.get("id", "statement")]

logger.info("✓ Statement structure built successfully")
logger.info("\nIncome Statement:")
logger.info(income_statement_df_hist.to_string(index=False))

# --- 5. Forecasting ---

logger.info("Setting up forecasting...")
forecast_periods = ["2024", "2025", "2026"]

# Define how different nodes should be forecasted
# Maps node_id to forecast configuration
forecast_configs = {
    "Revenue": {
        "method": "simple",  # Simple growth method
        "config": 0.10,  # 10% growth rate
    },
    "COGS": {
        "method": "historical_growth",  # Use average historical growth
        "config": None,  # No specific config needed for this method
    },
    "R&D": {
        "method": "curve",  # Different growth rates per period
        "config": [0.08, 0.06, 0.15],  # 8%, 6%, 5% growth for 2024, 2025, 2026
    },
    "SG&A": {
        "method": "statistical",  # Correct method name recognized by StatementForecaster
        "config": {  # Config structure expected by StatementForecaster for statistical
            "distribution": "normal",
            "params": {  # Parameters nested under 'params'
                "mean": 0.02,  # Mean growth rate (2%)
                "std": 0.05,  # Standard deviation key is 'std'
            },
        },
    },
    "Interest Expense": {  # Added forecast
        "method": "simple",
        "config": 0.05,  # 5% growth rate (increase in expense)
    },
    "Taxes": {  # Added forecast
        "method": "historical_growth",  # Assume taxes grow similarly to past trends
        "config": None,
    },
    "D&A": {  # Added forecast
        "method": "simple",  # Simple growth method
        "config": 0.03,  # 3% growth rate (increase in expense)
    },
    # Note: Calculated items (like gross_profit, ebitda, ebit, net_income) don't need forecast configs,
    # they will be recalculated based on their forecasted inputs.
}

# Use the StatementForecaster (adjust if API changes)
try:
    forecaster = StatementForecaster(fsg=graph)  # Pass the core graph
    logger.info(f"Creating forecasts for periods: {forecast_periods}")

    # Apply the forecasts - this modifies the underlying data nodes in the graph
    forecaster.create_forecast(
        forecast_periods=forecast_periods,
        node_configs=forecast_configs,
        historical_periods=["2022", "2023"],  # Explicitly provide historical periods
    )

    logger.info("Forecasting complete. Graph data nodes updated.")
    # logger.debug(f"Graph periods after forecast: {graph.periods}") # Already added periods
    # logger.debug(f"Forecasted Revenue in 2025: {graph.get_node('Revenue').calculate('2025')}")
    # logger.debug(f"Recalculated Gross Profit in 2025: {graph.calculate('gross_profit', '2025')}")

except (ValueError, FinancialModelError):
    logger.exception("Forecasting failed")
    sys.exit()

# --- 6. Statement Generation (Forecasted) using code-only StatementStructure ---
# TODO: Implement forecasted statement generation using code-only StatementStructure.

# --- 7. Exporting ---

# Reload the special metrics directory to pick up the newly added retained_earnings metric
special_dir = (
    MetricPath(__file__).parent.parent.parent
    / "fin_statement_model/core/metrics/metric_defn/special"
)
metric_count = metric_registry.load_metrics_from_directory(special_dir)
logger.info(
    f"Reloaded {metric_count} metrics from special directory to include retained_earnings"
)

md_output_path = OUTPUT_DIR / "financial_statements.md"  # Added Markdown path

try:
    logger.info(f"Exporting statements to Excel into directory: {OUTPUT_DIR}")

    # Create a dummy Balance Sheet config for multi-sheet export demonstration
    # Use core. prefixes for node_ids and add required totals/metrics
    balance_sheet_yaml = """
id: balance_sheet
name: Balance Sheet (Complete)
description: Snapshot of assets, liabilities, equity.
sections:
  - id: current_assets
    name: Current Assets
    items:
      - id: cash
        name: Cash & Equivalents
        type: line_item
        node_id: core.cash # Use core prefix
        sign_convention: 1
      - id: ar
        name: Accounts Receivable
        type: line_item
        node_id: core.accounts_receivable # Use core prefix
        sign_convention: 1
    subtotal:
      id: current_assets_subtotal
      name: Total Current Assets
      type: subtotal
      items_to_sum: [cash, ar]
      sign_convention: 1

  - id: non_current_assets
    name: Non-Current Assets
    items:
      - id: ppe
        name: Property, Plant & Equipment
        type: line_item
        node_id: core.ppe # Use core prefix
        sign_convention: 1
    # Add subtotal if there were more items

  - id: total_assets_section # Section for the final total
    name: Total Assets
    items:
      - id: total_assets
        name: Total Assets
        type: calculated
        calculation:
          type: addition
          inputs: [current_assets_subtotal, ppe]
        sign_convention: 1

  - id: current_liabilities
    name: Current Liabilities
    items:
      - id: ap
        name: Accounts Payable
        type: line_item
        node_id: core.accounts_payable # Use core prefix
        sign_convention: 1 # Liabilities shown positive
    # Add subtotal if there were more items

  - id: non_current_liabilities
    name: Non-Current Liabilities
    items:
      - id: debt
        name: Long-Term Debt
        type: line_item
        node_id: core.debt # Use core prefix
        sign_convention: 1 # Liabilities shown positive

  - id: total_liabilities_section # Section for total liabilities
    name: Total Liabilities
    items:
      - id: total_liabilities
        name: Total Liabilities
        type: calculated
        calculation:
          type: addition
          inputs: [ap, debt]
        sign_convention: 1

  - id: equity
    name: Equity
    items:
      - id: common_stock
        name: Common Stock
        type: line_item
        node_id: core.common_stock # Use core prefix
        sign_convention: 1
      - id: net_income
        name: Net Income
        type: metric
        metric_id: net_income
        inputs:
          operating_income: gross_profit
          interest_expense: "Interest Expense"
          income_tax: "Taxes"
        sign_convention: 1
      - id: retained_earnings # Metric item
        name: Retained Earnings
        type: metric
        metric_id: retained_earnings # Use the built-in metric
        inputs:
          # Map metric inputs to statement item IDs or node IDs
          # Need core.prior_retained_earnings, core.net_income, core.dividends
          # Assume net_income from income statement can be used
          prior_retained_earnings: core.prior_retained_earnings
          net_income: net_income # Reference IS net income (if available in graph)
          dividends: core.dividends
        sign_convention: 1
    subtotal:
      id: total_equity
      name: Total Equity
      type: subtotal
      items_to_sum: [common_stock, retained_earnings]
      sign_convention: 1

  - id: total_liabilities_equity_section # Section for balancing check
    name: Total Liabilities & Equity
    items:
      - id: total_liabs_equity
        name: Total Liabilities & Equity
        type: calculated
        calculation:
          type: addition
          inputs: [total_liabilities, total_equity]
        sign_convention: 1
"""
    bs_stmt_path = CONFIG_DIR / "balance_sheet.yaml"
    with open(bs_stmt_path, "w", encoding="utf-8") as f:
        f.write(balance_sheet_yaml)

    # Load all YAML configs in CONFIG_DIR into memory
    all_configs: dict[str, dict[str, Any]] = {}
    # Only load the example statement configs for this script
    for yaml_path in [income_stmt_path, bs_stmt_path]:
        cfg_dict = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        stmt_id = cfg_dict.get("id", yaml_path.stem)
        all_configs[stmt_id] = cfg_dict

    # Use the high-level export function
    # This will internally call create_statement_dataframe for all configs in CONFIG_DIR
    # and write each resulting DataFrame to a separate sheet in the Excel file.
    export_statements_to_excel(
        graph=graph,
        raw_configs=all_configs,
        output_dir=str(OUTPUT_DIR),  # Excel files will be written into this directory
        format_kwargs={
            "number_format": ",.0f"
        },  # Formatting for the DataFrames before export
        # writer_kwargs={'freeze_panes': (1, 1)} # Example: Pass args to pandas.to_excel
    )
    logger.info(f"Successfully exported statements to {OUTPUT_DIR}")

    # --- Add Markdown Export ---
    logger.info(f"Exporting statements to Markdown: {md_output_path}")
    # Prepare registry and builder for balance sheet
    bs_registry = StatementRegistry()
    builder = StatementStructureBuilder()
    # Load, validate, build, and register the balance_sheet config from in-memory dict
    bs_raw_config = all_configs.get("balance_sheet") or yaml.safe_load(
        bs_stmt_path.read_text(encoding="utf-8")
    )
    load_build_register_statements(
        {bs_raw_config.get("id", "balance_sheet"): bs_raw_config}, bs_registry, builder
    )
    statement_structure = bs_registry.get("balance_sheet")
    # Populate graph with balance sheet calculation and metric nodes
    populate_graph(bs_registry, graph)
    # Use direct MarkdownWriter with config to avoid facade schema limitations
    from fin_statement_model.io.config.models import MarkdownWriterConfig
    from fin_statement_model.io.formats.markdown.writer import MarkdownWriter

    # Build MarkdownWriterConfig (statement_config_path required by schema)
    md_cfg = MarkdownWriterConfig(
        format_type="markdown",
        target=str(md_output_path),
        statement_config_path=str(bs_stmt_path),
        historical_periods=["2022", "2023"],
        forecast_periods=forecast_periods,
        forecast_configs=forecast_configs,
    )
    # Instantiate MarkdownWriter with Pydantic config
    md_writer = MarkdownWriter(config=md_cfg)
    # Render markdown content using modern StatementStructure approach
    md_content = md_writer.write(
        graph,
        statement_structure=statement_structure,
    )
    # Write to file
    try:
        with open(md_output_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        logger.info(f"Successfully wrote Markdown to {md_output_path}")
    except Exception:
        logger.exception("Failed to write Markdown to file")

except (WriteError, FinancialModelError):
    logger.exception("Failed to export data")

# --- 8. Cleanup ---
finally:
    logger.info("Cleaning up temporary directory...")
    # temp_dir.cleanup()
    logger.info("Example finished.")
