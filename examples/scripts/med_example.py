"""
This example demonstrates the core capabilities of the fin_statement_model library.
It includes:
- Basic setup and configuration
- Historical statement generation
- Forecasting
- Exporting to Excel
"""

import logging
from pathlib import Path
import sys
# --- Core Library Imports ---
# Assuming the library is installed or accessible in the Python path
# Adjust imports based on final package structure if needed
from fin_statement_model.core.graph import Graph
from fin_statement_model.core.errors import (
    FinancialModelError,
    ConfigurationError,
    StatementError,
    # ReadError, # Removed
    # WriteError, # Removed
)
# Add import for IO errors
from fin_statement_model.io.exceptions import ReadError, WriteError
from fin_statement_model.io import read_data
from fin_statement_model.statements import (
    create_statement_dataframe,
    export_statements_to_excel,
    # export_statements_to_json, # Alternative export
)
# Import forecasting components (adjust if API changes)
from fin_statement_model.forecasting.forecaster import StatementForecaster

# --- 1. Setup ---

# Configure logging for visibility
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("StarterExample")

# Create temporary directory for config files and output
# temp_dir = tempfile.TemporaryDirectory()
# CONFIG_DIR = Path(temp_dir.name) / "configs"
# OUTPUT_DIR = Path(temp_dir.name) / "output"

# --- START NEW DIR LOGIC --- 
SCRIPT_DIR = Path(__file__).parent
CONFIG_DIR = SCRIPT_DIR / "configs"
OUTPUT_DIR = SCRIPT_DIR / "output"
# --- END NEW DIR LOGIC --- 

CONFIG_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logger.info(f"Using temporary config directory: {CONFIG_DIR}")
logger.info(f"Using temporary output directory: {OUTPUT_DIR}")

# --- 2. Configuration Files (Simulated) ---

# Define statement structures as YAML strings
# (In a real project, these would be separate .yaml files)

income_statement_yaml = """
id: income_statement
name: Income Statement
description: Reports financial performance over a specific period.
sections:
  - id: revenue_section
    name: Revenue
    items:
      - id: revenue
        name: Total Revenue
        type: line_item
        node_id: Revenue # Maps to the node ID in the graph
        sign_convention: 1
  - id: cost_of_goods_sold
    name: Cost of Goods Sold
    items:
      - id: cogs
        name: Cost of Goods Sold
        type: line_item
        node_id: COGS
        sign_convention: -1 # Often shown as negative or subtracted
  - id: gross_profit_section
    name: Gross Profit
    items:
      - id: gross_profit
        name: Gross Profit
        type: calculated # This item is calculated
        calculation:
          type: addition # GP = Revenue + (-COGS) effectively Revenue - COGS
          inputs: [revenue, cogs] # Refers to the IDs of items above
        sign_convention: 1
    subtotal: # Example of section subtotal (same as the calculated item here)
      id: gross_profit_subtotal
      name: Gross Profit Subtotal
      type: subtotal
      items_to_sum: [gross_profit] # Sums items *within this section*
      sign_convention: 1
  - id: operating_expenses
    name: Operating Expenses
    items:
      - id: r_d
        name: Research & Development
        type: line_item
        node_id: R&D
        sign_convention: -1
      - id: sg_a
        name: Selling, General & Administrative
        type: line_item
        node_id: SG&A
        sign_convention: -1
    subtotal:
      id: total_operating_expenses
      name: Total Operating Expenses
      type: subtotal
      items_to_sum: [r_d, sg_a] # Sums R&D and SG&A
      sign_convention: -1
  - id: operating_income_section
    name: Operating Income
    items:
      - id: operating_income
        name: Operating Income (EBIT)
        type: calculated
        calculation:
          type: addition # OpInc = Gross Profit + Total Operating Expenses (which is negative)
          inputs: [gross_profit, total_operating_expenses]
        sign_convention: 1
"""

# Write the YAML string to a temporary file
income_stmt_path = CONFIG_DIR / "income_statement.yaml"
with open(income_stmt_path, "w") as f:
    f.write(income_statement_yaml)
logger.info(f"Created example config: {income_stmt_path}")

# --- 3. Initial Data Loading ---

# Sample historical data (Node IDs match those in YAML `node_id` fields)
historical_data = {
    # Node ID: { Period: Value }
    "Revenue": {"2022": 1000.0, "2023": 1200.0},
    "COGS": {"2022": -400.0, "2023": -500.0}, # Input data can have its own sign
    "R&D": {"2022": -100.0, "2023": -120.0},
    "SG&A": {"2022": -200.0, "2023": -250.0},
}

# Create the core graph
graph = Graph()

# Load data using the IO layer's 'dict' reader
try:
    logger.info("Loading historical data into graph...")
    # read_data handles adding nodes and periods from the source dict
    graph = read_data(format_type="dict", source=historical_data)
    logger.info(f"Graph initialized with {len(graph.nodes)} nodes and periods: {graph.periods}")
    # Verify a node value
    logger.debug(f"Revenue in 2023 (raw): {graph.get_node('Revenue').get_value('2023')}") # Accessing node directly
except (ReadError, FinancialModelError) as e:
    logger.exception(f"Failed to load initial data: {e}")
    # Exit or handle error appropriately in a real application
    # temp_dir.cleanup()
    sys.exit()

# --- 4. Statement Generation (Historical) ---

# Use the high-level factory function to process the config and generate the DataFrame
try:
    logger.info("Generating historical Income Statement DataFrame...")
    # This function does the following:
    # 1. Reads 'income_statement.yaml'
    # 2. Validates the config using Pydantic models
    # 3. Builds the StatementStructure
    # 4. Registers the structure
    # 5. Populates the 'graph' with calculation nodes (gross_profit, total_operating_expenses, operating_income)
    # 6. Formats the statement data from the graph into a DataFrame
    income_statement_df_hist = create_statement_dataframe(
        graph=graph,
        config_path_or_dir=str(income_stmt_path), # Pass path to the single config file
        format_kwargs={
            'should_apply_signs': True, # Use new name
            'number_format': ',.0f' # Format numbers with commas, no decimals
        }
    )

    logger.info("Historical Income Statement DataFrame generated:")
    print("\n--- Historical Income Statement ---")
    print(income_statement_df_hist.to_string(index=False))
    print("-" * 35)

    # Verify a calculated value in the graph *after* population
    logger.debug(f"Gross Profit in 2023 (calculated): {graph.calculate('gross_profit', '2023')}")

except (FileNotFoundError, ConfigurationError, StatementError, FinancialModelError) as e:
    logger.exception(f"Failed to generate historical statement: {e}")
    # temp_dir.cleanup()
    exit()

# --- 5. Forecasting ---

logger.info("Setting up forecasting...")
forecast_periods = ["2024", "2025", "2026"]

# Define how different nodes should be forecasted
# Maps node_id to forecast configuration
forecast_configs = {
    "Revenue": {
        "method": "simple", # Corresponds to 'fixed' growth in NodeFactory
        "config": 0.10 # 10% fixed growth rate
    },
    "COGS": {
        "method": "historical_growth", # Use average historical growth
        "config": None # No specific config needed for this method
    },
    "R&D": {
        "method": "curve", # Different growth rates per period
        "config": [0.08, 0.06, 0.05] # 8%, 6%, 5% growth for 2024, 2025, 2026
    },
    "SG&A": {
        "method": "average", # Use historical average value
        "config": None # No specific config needed
    }
    # Note: Calculated items (like gross_profit) don't need forecast configs,
    # they will be recalculated based on their forecasted inputs.
}

# Use the StatementForecaster (adjust if API changes)
try:
    forecaster = StatementForecaster(fsg=graph) # Pass the core graph
    logger.info(f"Creating forecasts for periods: {forecast_periods}")

    # Apply the forecasts - this modifies the underlying data nodes in the graph
    forecaster.create_forecast(
        forecast_periods=forecast_periods,
        node_configs=forecast_configs,
        # historical_periods=None # Let it infer from graph.periods
    )

    logger.info("Forecasting complete. Graph data nodes updated.")
    logger.debug(f"Graph periods after forecast: {graph.periods}")
    # Check a forecasted value directly in the graph node
    logger.debug(f"Forecasted Revenue in 2025: {graph.get_node('Revenue').get_value('2025')}")
    # Check a recalculated value based on forecasted inputs
    # Note: graph.calculate will compute on the fly using updated inputs
    logger.debug(f"Recalculated Gross Profit in 2025: {graph.calculate('gross_profit', '2025')}")

except (ValueError, FinancialModelError) as e:
     logger.exception(f"Forecasting failed: {e}")
     # temp_dir.cleanup()
     exit()

# --- 6. Statement Generation (Forecasted) ---

# Regenerate the DataFrame to include the new forecast periods
try:
    logger.info("Generating Income Statement DataFrame including forecasts...")
    income_statement_df_forecast = create_statement_dataframe(
        graph=graph, # Use the *same* graph instance, now updated with forecasts
        config_path_or_dir=str(income_stmt_path),
        format_kwargs={
            'should_apply_signs': True, # Use new name
            'number_format': ',.0f'
            # 'periods': graph.periods # Optionally specify all periods
        }
    )

    logger.info("Forecasted Income Statement DataFrame generated:")
    print("\n--- Income Statement (Historical + Forecast) ---")
    print(income_statement_df_forecast.to_string(index=False))
    print("-" * 50)

except (ConfigurationError, StatementError, FinancialModelError) as e:
    logger.exception(f"Failed to generate forecasted statement: {e}")
    # temp_dir.cleanup()
    exit()

# --- 7. Exporting ---

excel_output_path = OUTPUT_DIR / "financial_statements.xlsx"

try:
    logger.info(f"Exporting statements to Excel: {excel_output_path}")

    # Create a dummy Balance Sheet config for multi-sheet export demonstration
    balance_sheet_yaml = """
id: balance_sheet
name: Balance Sheet (Partial)
description: Snapshot of assets, liabilities, equity.
sections:
  - id: assets
    name: Assets
    items:
      - id: cash
        name: Cash & Equivalents
        type: line_item
        node_id: Cash
      - id: accounts_receivable
        name: Accounts Receivable
        type: line_item
        node_id: AR
    """
    bs_stmt_path = CONFIG_DIR / "balance_sheet.yaml"
    with open(bs_stmt_path, "w") as f:
        f.write(balance_sheet_yaml)
    # Add some dummy data for BS items to the graph
    graph.add_financial_statement_item("Cash", {"2022": 50, "2023": 60, "2024": 70, "2025": 80, "2026": 90})
    graph.add_financial_statement_item("AR", {"2022": 100, "2023": 110, "2024": 120, "2025": 130, "2026": 140})

    # Use the high-level export function
    # This will internally call create_statement_dataframe for all configs in CONFIG_DIR
    # and write each resulting DataFrame to a separate sheet in the Excel file.
    export_statements_to_excel(
        graph=graph,
        config_path_or_dir=str(CONFIG_DIR), # Process all YAML files in the dir
        output_dir=str(excel_output_path), # Specify the single output Excel file path
        format_kwargs={'number_format': ',.0f'}, # Formatting for the DataFrames before export
        # writer_kwargs={'freeze_panes': (1, 1)} # Example: Pass args to pandas.to_excel
    )
    logger.info(f"Successfully exported statements to {excel_output_path}")

    # --- Alternative: Export using write_data ---
    # You can also export the raw graph data directly
    # raw_data_path = OUTPUT_DIR / "graph_data.xlsx"
    # logger.info(f"Exporting raw graph data using write_data to {raw_data_path}")
    # write_data(
    #     format_type="excel",
    #     graph=graph,
    #     target=str(raw_data_path),
    #     # Optional kwargs for ExcelWriterConfig or write method:
    #     # sheet_name="RawData",
    #     # recalculate=False # Already calculated
    # )
    # logger.info(f"Successfully exported raw graph data to {raw_data_path}")


except (WriteError, FinancialModelError) as e:
    logger.exception(f"Failed to export data: {e}")

# --- 8. Cleanup ---
finally:
    logger.info("Cleaning up temporary directory...")
    # temp_dir.cleanup()
    logger.info("Example finished.")