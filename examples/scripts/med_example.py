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

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.errors import (
    FinancialModelError,
    ConfigurationError,
    StatementError,
)

from fin_statement_model.io.exceptions import WriteError
from fin_statement_model.io import read_data, write_data
from fin_statement_model.statements import (
    create_statement_dataframe,
    export_statements_to_excel,
)
from fin_statement_model.forecasting.forecaster import StatementForecaster
from fin_statement_model.core.metrics.registry import metric_registry
from pathlib import Path as MetricPath

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
  - id: gross_profit_section # Section ID
    name: Gross Profit # Section name
    items:
      - id: gross_profit # Item ID
        name: Gross Profit
        type: metric
        metric_id: gross_profit
        inputs:
          revenue: revenue
          cost_of_goods_sold: cogs
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
      - id: depreciation_amortization
        name: Depreciation & Amortization
        type: line_item
        node_id: D&A
        sign_convention: -1
    subtotal:
      id: total_operating_expenses
      name: Total Operating Expenses
      type: subtotal
      items_to_sum: [r_d, sg_a, depreciation_amortization]
      sign_convention: -1
  - id: ebitda_section
    name: EBITDA
    items:
      - id: ebitda
        name: EBITDA
        type: calculated
        calculation:
          type: addition
          inputs: [gross_profit, r_d, sg_a]
        sign_convention: 1
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
  - id: interest_expense_section
    name: Interest Expense
    items:
      - id: interest_expense
        name: Interest Expense
        type: line_item
        node_id: Interest Expense
        sign_convention: -1 # Shown as negative
  - id: ebt_section
    name: Earnings Before Tax (EBT)
    items:
      - id: ebt
        name: Earnings Before Tax
        type: calculated
        calculation:
          type: addition # EBT = Operating Income + Interest Expense (which is negative)
          inputs: [operating_income, interest_expense]
        sign_convention: 1
  - id: taxes_section
    name: Income Tax Expense
    items:
      - id: taxes
        name: Income Tax Expense
        type: line_item
        node_id: Taxes
        sign_convention: -1 # Shown as negative
  - id: net_income_section
    name: Net Income
    items:
      - id: net_income
        name: Net Income
        type: calculated
        calculation:
          type: addition # Net Income = EBT + Taxes (which is negative)
          inputs: [ebt, taxes]
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
    "COGS": {"2022": -400.0, "2023": -500.0},
    "R&D": {"2022": -100.0, "2023": -120.0},
    "SG&A": {"2022": -200.0, "2023": -250.0},
    "Interest Expense": {"2022": -50.0, "2023": -60.0},
    "Taxes": {"2022": -75.0, "2023": -90.0},
    "D&A": {"2022": -30.0, "2023": -35.0},
}

# Create the core graph
graph = Graph()
graph = read_data(format_type="dict", source=historical_data)

# --- 4. Statement Generation (Historical) ---
income_statement_df_hist = create_statement_dataframe(
    graph=graph,
    config_path_or_dir=str(income_stmt_path),  # Pass path to the single config file
    format_kwargs={
        "should_apply_signs": True,  # Use new name
        "number_format": ",.0f",  # Format numbers with commas, no decimals
    },
)

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
    # logger.debug(f"Forecasted Revenue in 2025: {graph.get_node('Revenue').get_value('2025')}")
    # logger.debug(f"Recalculated Gross Profit in 2025: {graph.calculate('gross_profit', '2025')}")

except (ValueError, FinancialModelError):
    logger.exception("Forecasting failed")
    sys.exit()

# --- 6. Statement Generation (Forecasted) ---

# Regenerate the DataFrame to include the new forecast periods
try:
    logger.info("Generating Income Statement DataFrame including forecasts...")
    income_statement_df_forecast = create_statement_dataframe(
        graph=graph,  # Use the *same* graph instance, now updated with forecasts
        config_path_or_dir=str(income_stmt_path),
        format_kwargs={
            "should_apply_signs": True,  # Use new name
            "number_format": ",.0f",
            # 'periods': graph.periods # Optionally specify all periods
        },
    )

    logger.info("Forecasted Income Statement DataFrame generated:")
    logger.info("\n--- Income Statement (Historical + Forecast) ---")
    logger.info(income_statement_df_forecast.to_string(index=False))
    logger.info("-" * 50)

except (ConfigurationError, StatementError, FinancialModelError):
    logger.exception("Failed to generate forecasted statement")
    # temp_dir.cleanup()
    sys.exit()

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

excel_output_path = OUTPUT_DIR / "financial_statements.xlsx"
md_output_path = OUTPUT_DIR / "financial_statements.md"  # Added Markdown path

try:
    logger.info(f"Exporting statements to Excel: {excel_output_path}")

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
    with open(bs_stmt_path, "w") as f:
        f.write(balance_sheet_yaml)

    # Add all required BS item data to the graph, using core prefixes
    # and including all historical + forecast periods
    all_periods_list = list(graph.periods)

    # Define some simple forecast logic for the new BS items
    bs_forecasts = {
        "core.cash": 0.10,  # 10% growth
        "core.accounts_receivable": 0.12,  # 12% growth
        "core.ppe": 0.05,  # 5% growth
        "core.accounts_payable": 0.08,  # 8% growth
        "core.debt": 0.02,  # 2% growth (increase)
        "core.common_stock": 0.0,  # No change
        "core.prior_retained_earnings": 0.0,  # This will be calculated by metric usually
        "core.dividends": 0.05,  # Increase dividends by 5%
    }

    # Function to generate data across all periods with simple growth
    def generate_data(
        node_id: str, start_val: float, growth_rate: float
    ) -> dict[str, float]:
        """Generate data for a node across periods with simple growth."""
        data: dict[str, float] = {}
        current_val = start_val
        for i, period in enumerate(all_periods_list):
            if i > 1:  # Apply growth after first two historical periods
                current_val *= 1 + growth_rate
            data[period] = current_val
        return data

    # Add data ensuring all periods exist
    graph.add_financial_statement_item(
        "core.cash", generate_data("core.cash", 50.0, bs_forecasts["core.cash"])
    )
    graph.add_financial_statement_item(
        "core.accounts_receivable",
        generate_data(
            "core.accounts_receivable", 100.0, bs_forecasts["core.accounts_receivable"]
        ),
    )
    graph.add_financial_statement_item(
        "core.ppe", generate_data("core.ppe", 300.0, bs_forecasts["core.ppe"])
    )
    graph.add_financial_statement_item(
        "core.accounts_payable",
        generate_data(
            "core.accounts_payable", 80.0, bs_forecasts["core.accounts_payable"]
        ),
    )
    graph.add_financial_statement_item(
        "core.debt", generate_data("core.debt", 150.0, bs_forecasts["core.debt"])
    )
    graph.add_financial_statement_item(
        "core.common_stock",
        generate_data("core.common_stock", 100.0, bs_forecasts["core.common_stock"]),
    )
    # Need prior RE and dividends for the Retained Earnings metric
    # Let's assume prior RE grows with net income (simple approximation for example)
    # We need net income data in the graph first. Net income IS calculated from IS items.
    # Let's use the previously calculated net income node values
    # TODO: This is tricky - Retained Earnings depends on Net Income, which is calculated.
    # The metric expects 'net_income' as an input node ID. We have 'net_income' as a calculated item ID.
    # We might need to ensure 'net_income' node exists or map differently. For now, assume graph.calculate works.
    # Add dummy prior RE - usually this links period to period
    prior_re = {"2022": 100.0, "2023": 100.0 + 945}  # Start + Previous NI
    prior_re["2024"] = prior_re["2023"] + 1145
    prior_re["2025"] = prior_re["2024"] + 1354  # Use NI values from previous run
    prior_re["2026"] = prior_re["2025"] + 1628  # Use NI values from previous run
    graph.add_financial_statement_item("core.prior_retained_earnings", prior_re)

    graph.add_financial_statement_item(
        "core.dividends",
        generate_data(
            "core.dividends", -10.0, bs_forecasts["core.dividends"]
        ),  # Negative value
    )

    # Use the high-level export function
    # This will internally call create_statement_dataframe for all configs in CONFIG_DIR
    # and write each resulting DataFrame to a separate sheet in the Excel file.
    export_statements_to_excel(
        graph=graph,
        config_path_or_dir=str(CONFIG_DIR),  # Process all YAML files in the dir
        output_dir=str(excel_output_path),  # Specify the single output Excel file path
        format_kwargs={
            "number_format": ",.0f"
        },  # Formatting for the DataFrames before export
        # writer_kwargs={'freeze_panes': (1, 1)} # Example: Pass args to pandas.to_excel
    )
    logger.info(f"Successfully exported statements to {excel_output_path}")

    # --- Add Markdown Export ---
    logger.info(f"Exporting statement to Markdown: {md_output_path}")
    # Assuming write_data handles writing the string returned by MarkdownWriter to the target file
    write_data(
        format_type="markdown",
        graph=graph,
        target=str(md_output_path),
        forecast_configs=forecast_configs,
        historical_periods=["2022", "2023"],
        statement_config_path=str(income_stmt_path),
    )
    logger.info(f"Successfully exported statement to {md_output_path}")
    # --- End Markdown Export ---

except (WriteError, FinancialModelError):
    logger.exception("Failed to export data")

# --- 8. Cleanup ---
finally:
    logger.info("Cleaning up temporary directory...")
    # temp_dir.cleanup()
    logger.info("Example finished.")
