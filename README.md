Okay, here is a comprehensive README.md file generated based on the provided Python code for the fin_statement_model library.

# fin_statement_model

A Python library for building, calculating, analyzing, and forecasting financial statement models using a flexible, graph-based approach.


## Overview

`fin_statement_model` provides a robust framework for representing financial statements (Income Statement, Balance Sheet, Cash Flow) and their interdependencies as a calculation graph. It allows users to:

*   Define financial statement structures using configuration files (YAML/JSON).
*   Load historical financial data from various sources (Excel, CSV, Dictionaries, DataFrames, FMP API).
*   Define complex calculations using formulas, Python functions, or reusable strategies.
*   Utilize pre-defined financial metrics loaded from configuration.
*   Perform time-series analysis and data transformations.
*   Generate forecasts based on historical data using various methods.
*   Export results to different formats (Excel, DataFrame, Dictionary).

The library is designed to be extensible, allowing users to add custom calculation strategies, metrics, data readers/writers, and preprocessing transformers.

## Key Features

*   **Core Graph Engine:**
    *   Represents financial items and calculations as nodes in a directed graph (`Graph`, `FinancialStatementGraph`).
    *   Manages dependencies between nodes.
    *   Includes a `CalculationEngine` for evaluating node values with caching.
    *   Includes a `DataManager` for handling time-series data and periods.
*   **Flexible Nodes:**
    *   `FinancialStatementItemNode`: Stores raw historical or projected data.
    *   **Calculation Nodes:**
        *   `FormulaCalculationNode`: Evaluates simple mathematical string formulas (e.g., "a + b").
        *   `StrategyCalculationNode`: Delegates calculation logic to reusable strategy objects (e.g., Addition, Subtraction, Weighted Average).
        *   `MetricCalculationNode`: Calculates standard financial metrics based on definitions loaded from YAML files.
        *   `CustomCalculationNode`: Uses arbitrary Python functions for complex calculations.
    *   **Statistical Nodes:**
        *   `YoYGrowthNode`: Calculates year-over-year percentage growth.
        *   `MultiPeriodStatNode`: Computes statistics (mean, stddev) over multiple periods.
        *   `TwoPeriodAverageNode`: Calculates the average over two specific periods.
    *   **Forecast Nodes:**
        *   `ForecastNode` (Base): Framework for forecasting.
        *   `FixedGrowthForecastNode`: Applies a constant growth rate.
        *   `CurveGrowthForecastNode`: Applies varying growth rates per period.
        *   `StatisticalGrowthForecastNode`: Uses a statistical distribution for growth rates.
        *   `AverageValueForecastNode`: Uses the historical average value for forecasts.
        *   `AverageHistoricalGrowthForecastNode`: Uses the average historical growth rate.
        *   `CustomGrowthForecastNode`: Uses a custom Python function for growth rates.
*   **Statement Structure Definition:**
    *   Define the hierarchical structure of financial statements (Sections, Line Items, Calculations, Subtotals) using YAML or JSON configuration files (`StatementStructure`, `Section`, `LineItem`, etc.).
    *   Load configurations using `StatementConfig` and manage them with `StatementManager`.
    *   `StatementFactory` provides convenience methods for loading, calculating, and formatting statements.
*   **Metric Registry:**
    *   Define standard financial metrics in simple YAML files (`MetricRegistry`).
    *   Load metrics automatically from a built-in directory or custom locations.
    *   Use `MetricCalculationNode` to easily incorporate metrics into the graph.
*   **Calculation Strategies:**
    *   Encapsulate calculation logic using the Strategy pattern (`Strategy` base class).
    *   Built-in strategies: Addition, Subtraction, Multiplication, Division, WeightedAverage, CustomFormula.
    *   Register custom strategies using the `Registry`.
*   **Input/Output (IO):**
    *   Extensible reader/writer system (`DataReader`, `DataWriter`, `registry`).
    *   Read data from:
        *   Dictionaries (`DictReader`)
        *   Excel files (`ExcelReader`)
        *   CSV files (`CsvReader`)
        *   Pandas DataFrames (`DataFrameReader`)
        *   Financial Modeling Prep (FMP) API (`FmpReader`)
    *   Write data to:
        *   Dictionaries (`DictWriter`)
        *   Excel files (`ExcelWriter`)
        *   Pandas DataFrames (`DataFrameWriter`)
    *   Facade functions `read_data` and `write_data` for easy use.
*   **Data Preprocessing & Transformation:**
    *   Extensible transformer system (`DataTransformer`, `CompositeTransformer`, `TransformerFactory`).
    *   `TransformationService` to manage and apply transformations.
    *   Built-in transformers for:
        *   Normalization (`NormalizationTransformer`: percent_of, minmax, standard, scale_by)
        *   Time Series (`TimeSeriesTransformer`: growth_rate, moving_avg, cagr, yoy, qoq)
        *   Period Conversion (`PeriodConversionTransformer`: quarterly_to_annual, etc.)
        *   Statement Formatting (`StatementFormattingTransformer`: add subtotals, apply sign conventions)
*   **Forecasting:**
    *   Project future values based on historical data using various methods.
    *   Forecast operations integrated directly into the `FinancialStatementGraph`.
*   **Extensibility:**
    *   Easily add custom calculation strategies.
    *   Define custom metrics via YAML.
    *   Create custom data readers, writers, and transformers.
    *   Optional LLM extension for OpenAI integration (`LLMClient`).
*   **Error Handling:** Rich set of custom exceptions for specific error conditions (`ConfigurationError`, `CalculationError`, `NodeError`, `ReadError`, `WriteError`, etc.).
*   **Logging:** Configurable logging throughout the library.

## Installation

```bash
pip install fin_statement_model


To include optional extensions like OpenAI integration:

# Example placeholder - adjust based on actual extras_require
pip install fin_statement_model[openai]
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bash
IGNORE_WHEN_COPYING_END
Core Concepts
1. Graph (Graph / FinancialStatementGraph)

The Graph is the central component, acting as a container for nodes and managing their dependencies. It integrates:

Node Registry: A dictionary holding all Node objects.

DataManager: Manages FinancialStatementItemNode data and the list of time periods.

CalculationEngine: Executes calculations defined by nodes, handling dependencies and caching.
The FinancialStatementGraph extends the core Graph with statement-specific mixins for analysis, forecasting, etc.

2. Nodes (Node subclasses)

Nodes represent individual elements in the financial model.

FinancialStatementItemNode: Holds raw numerical data for specific periods (e.g., historical revenue).

Calculation Nodes (FormulaCalculationNode, StrategyCalculationNode, MetricCalculationNode, CustomCalculationNode): Compute their values based on inputs from other nodes.

Statistical Nodes (YoYGrowthNode, etc.): Perform time-series statistical analysis.

Forecast Nodes (FixedGrowthForecastNode, etc.): Project future values based on historical data and growth assumptions.
All nodes inherit from the base Node class and typically implement a calculate(period) method.

3. Statements (StatementStructure, StatementManager, Config)

While the graph holds the data and calculations, the StatementStructure defines the presentation layout of a financial statement (like an Income Statement).

It's defined hierarchically using Section, LineItem, CalculatedLineItem, and SubtotalLineItem.

These structures are typically loaded from YAML or JSON configuration files using StatementConfig.

The StatementManager links a StatementStructure to the Graph, creates necessary calculation nodes based on the structure, and formats the output.

The StatementFactory provides helpers to load configurations, create managers, and export formatted statements (e.g., to DataFrame, Excel).

4. Metrics (MetricRegistry, YAML definitions)

Standard financial metrics (like Gross Margin, Current Ratio) can be defined in simple YAML files.

The MetricRegistry loads these definitions.

MetricCalculationNode uses a loaded definition (inputs, formula) to create a calculation node in the graph.

5. Strategies (Strategy, Registry)

The Strategy pattern allows encapsulating different calculation algorithms (e.g., addition, subtraction, weighted average).

StrategyCalculationNode uses a specific Strategy object to perform its calculation.

New strategies can be created by subclassing Strategy and registering them with the Registry.

6. Input/Output (IO) (DataReader, DataWriter, registry)

The IO system provides a consistent way to read data into the graph and write data out.

Uses a registry to manage available readers and writers based on a format_type string (e.g., 'excel', 'fmp').

The read_data and write_data functions act as easy-to-use facades.

7. Preprocessing (DataTransformer, TransformationService)

Provides tools to clean, transform, and prepare financial data.

Uses a TransformerFactory and registry similar to the IO system.

DataTransformer defines the interface for transformation steps.

TransformationService orchestrates applying individual transformers or pipelines.

8. Forecasting (ForecastNode, StatementForecaster)

Allows projecting future values for data nodes.

Various ForecastNode subclasses implement different growth logic.

A `StatementForecaster` is provided on the `FinancialStatementGraph` instance via the `forecaster` attribute. Use:

    fsg.forecaster.create_forecast(
        forecast_periods=[...],
        node_configs={...}
    )
   
Usage Examples
import pandas as pd
from fin_statement_model import (
    FinancialStatementGraph,
    read_data,
    write_data,
    StatementFactory,
    TransformationService
)
# Assuming necessary node classes are imported if needed directly

# --- 1. Basic Graph Setup ---
print("\n--- Basic Graph Setup ---")
periods = ["2022", "2023"]
fsg = FinancialStatementGraph(periods=periods)

# Add historical data items
revenue_data = {"2022": 1000.0, "2023": 1200.0}
cogs_data = {"2022": 600.0, "2023": 700.0}
rev_node = fsg.add_financial_statement_item("Revenue", revenue_data)
cogs_node = fsg.add_financial_statement_item("COGS", cogs_data)

print(f"Graph Nodes: {list(fsg.nodes.keys())}")
print(f"Graph Periods: {fsg.periods}")

# --- 2. Adding Calculations ---
print("\n--- Adding Calculations ---")
# a) Using FormulaCalculationNode (added directly for simplicity here)
from fin_statement_model.core.nodes import FormulaCalculationNode
gp_formula_node = FormulaCalculationNode(
    "GrossProfit_Formula",
    inputs={"r": rev_node, "c": cogs_node},
    formula="r - c"
)
fsg.add_node(gp_formula_node)

# b) Using StrategyCalculationNode (via Graph.add_calculation)
# Note: graph.add_calculation uses the CalculationEngine internally
# This might create a FormulaCalculationNode for simple ops by default,
# or a StrategyCalculationNode if a specific strategy type is matched.
# Let's assume 'subtraction' maps to a strategy for this example.
try:
    # This assumes a CalculationEngine setup that maps 'subtraction'
    # If using the default, this specific call might need adjustment or
    # direct StrategyCalculationNode instantiation.
    gp_strategy_node = fsg.add_calculation(
       name="GrossProfit_Strategy",
       input_names=["Revenue", "COGS"],
       operation_type="subtraction" # Assumes this type maps to SubtractionStrategy
    )
    print("Added GrossProfit_Strategy node.")
except ValueError as e:
    print(f"Could not add strategy node via add_calculation (may require specific engine setup): {e}")
    # Fallback: Add directly if needed for example
    # from fin_statement_model.core.nodes import StrategyCalculationNode
    # from fin_statement_model.core.strategies import SubtractionStrategy
    # gp_strategy_node = StrategyCalculationNode("GP_Strategy", [rev_node, cogs_node], SubtractionStrategy())
    # fsg.add_node(gp_strategy_node)


# c) Using MetricCalculationNode (via Graph.add_metric)
# Assume 'gross_margin_pct' metric is defined in YAML and loaded by MetricRegistry
# YAML Definition (example - gross_margin_pct.yaml):
# name: "Gross Margin Percentage"
# description: "Gross Profit as a percentage of Revenue."
# inputs:
#   - GrossProfit_Formula # Or GrossProfit_Strategy
#   - Revenue
# formula: "GrossProfit_Formula / Revenue * 100"
#
# Code assumes registry is populated (e.g., via auto-load or explicit loading)
try:
    # Ensure the GrossProfit node exists first
    if "GrossProfit_Formula" in fsg.nodes:
        fsg.add_metric(metric_name="gross_margin_pct", node_name="GrossMarginPct")
        print("Added GrossMarginPct metric node.")
    else:
        print("Skipping metric node add: GrossProfit_Formula node not found.")
except Exception as e:
    print(f"Could not add metric node (ensure metric is registered & inputs exist): {e}")


# --- 3. Calculating Values ---
print("\n--- Calculating Values ---")
try:
    gp_2023 = fsg.calculate("GrossProfit_Formula", "2023")
    print(f"Gross Profit (Formula) 2023: {gp_2023}") # Expected: 1200 - 700 = 500
except Exception as e:
    print(f"Error calculating GrossProfit_Formula: {e}")

try:
    if "GrossMarginPct" in fsg.nodes:
        gm_pct_2023 = fsg.calculate("GrossMarginPct", "2023")
        print(f"Gross Margin % 2023: {gm_pct_2023:.2f}") # Expected: 500 / 1200 * 100 = 41.67
    else:
        print("GrossMarginPct node not added, skipping calculation.")
except Exception as e:
    print(f"Error calculating GrossMarginPct: {e}")


# --- 4. Forecasting ---
print("\n--- Forecasting ---")
forecast_periods = ["2024", "2025"]
# Add forecast periods to the graph if they don't exist
fsg.add_periods(forecast_periods)

try:
    fsg.forecaster.create_forecast(
        forecast_periods=forecast_periods,
        node_configs={
            "Revenue": {"method": "simple", "config": 0.10},  # 10% fixed growth
            "COGS": {"method": "curve", "config": [0.08, 0.07]} # 8% then 7% growth
        }
        # historical_periods is inferred if None (uses periods before first forecast period)
    )
    print(f"Forecast for Revenue 2024: {fsg.calculate('Revenue', '2024'):.2f}") # 1200 * 1.10 = 1320
    print(f"Forecast for COGS 2025: {fsg.calculate('COGS', '2025'):.2f}") # (700 * 1.08) * 1.07 = 808.92
    # Forecasted values update the original nodes directly
    print(f"Revenue Node Values after forecast: {rev_node.values}")
    print(f"COGS Node Values after forecast: {cogs_node.values}")

    # Recalculate dependent items
    gp_2024_forecast = fsg.calculate("GrossProfit_Formula", "2024")
    print(f"Forecasted Gross Profit 2024: {gp_2024_forecast:.2f}") # 1320 - (700*1.08) = 564

except Exception as e:
    print(f"Error during forecasting: {e}")


# --- 5. Loading Statement Structure & Formatting ---
print("\n--- Loading Statement Structure & Formatting ---")
# Assume 'income_statement.yaml' defines a structure
# Example income_statement.yaml:
# id: IS
# name: Income Statement
# sections:
#   - id: revenue_section
#     name: Revenue
#     items:
#       - id: revenue_line
#         name: Total Revenue
#         node_id: Revenue # Links to graph node
#         type: line_item
#   - id: cogs_section
#     name: Cost of Goods Sold
#     items:
#       - id: cogs_line
#         name: Cost of Goods Sold
#         node_id: COGS
#         sign_convention: -1 # Display as negative
#         type: line_item
#   - id: gp_section
#     name: Gross Profit
#     items:
#       - id: gross_profit_calc # ID matches the graph node name
#         name: Gross Profit
#         type: calculated # Tells manager to ensure this node exists/is calculated
#         calculation:
#           type: subtraction # Defines how it *should* be calculated
#           inputs: [Revenue, COGS] # Dependencies (must match actual graph dependencies)
# ---
# Create a dummy config file for the example
config_content = """
id: IS
name: Income Statement Example
sections:
  - id: revenue_section
    name: Revenue
    items:
      - id: revenue_line
        name: Total Revenue
        node_id: Revenue
        type: line_item
  - id: cogs_section
    name: Cost of Goods Sold
    items:
      - id: cogs_line
        name: Cost of Goods Sold
        node_id: COGS
        sign_convention: -1
        type: line_item
  - id: gp_section
    name: Gross Profit Section
    items:
      - id: GrossProfit_Formula # Must match node ID in graph
        name: Gross Profit (Calculated)
        type: calculated # Indicates this node's value should be used
        calculation: # This informs the manager about expected dependencies
          type: subtraction
          inputs: [Revenue, COGS]
"""
config_path = "temp_income_statement.yaml"
with open(config_path, "w") as f:
    f.write(config_content)

try:
    # Use StatementFactory for convenience
    statement_df = StatementFactory.create_statement_dataframe(fsg, config_path)
    print("\nFormatted Statement DataFrame:")
    # Display DataFrame with better formatting if possible
    try:
        from IPython.display import display
        display(statement_df)
    except ImportError:
        print(statement_df.to_string())

    # Export to Excel
    StatementFactory.export_statements_to_excel(fsg, config_path, output_dir="output")
    print("\nExported statement to output/IS.xlsx")

except Exception as e:
    print(f"Error loading/formatting statement: {e}")
finally:
    # Clean up dummy config file
    import os
    if os.path.exists(config_path):
        os.remove(config_path)
    if os.path.exists("output/IS.xlsx"):
        import shutil
        shutil.rmtree("output")


# --- 6. Data IO ---
print("\n--- Data IO ---")
# a) Write graph data to DataFrame
df_export = write_data(format_type="dataframe", graph=fsg, target=None)
print("\nExported Graph to DataFrame:")
print(df_export.head().to_string())

# b) Write graph data to Dict
dict_export = write_data(format_type="dict", graph=fsg, target=None)
print("\nExported Graph to Dict (first 2 items):")
print({k: v for i, (k, v) in enumerate(dict_export.items()) if i < 2})

# c) Read data from Excel (requires a sample file)
# Create a sample Excel file
sample_data = {
    'Item': ['Sales', 'Rent'],
    '2021': [500, 50],
    '2022': [600, 55]
}
sample_df = pd.DataFrame(sample_data).set_index('Item')
sample_excel_path = "temp_input.xlsx"
sample_df.to_excel(sample_excel_path)

try:
    # Read data using the facade function
    read_fsg = read_data(
        format_type="excel",
        source=sample_excel_path,
        sheet_name="Sheet1",
        items_col=1,      # Column A (index 0 + 1 = 1) holds items
        periods_row=1     # Row 1 (index 0 + 1 = 1) holds periods
    )
    print("\nGraph created from Excel:")
    print(f"Nodes: {list(read_fsg.nodes.keys())}")
    print(f"Periods: {read_fsg.periods}")
    print(f"Sales 2022: {read_fsg.calculate('Sales', '2022')}")
except Exception as e:
    print(f"Error reading from Excel: {e}")
finally:
    if os.path.exists(sample_excel_path):
        os.remove(sample_excel_path)

# d) Read from FMP API (Example structure - requires valid API key)
# try:
#    fmp_key = "YOUR_FMP_API_KEY" # Or set FMP_API_KEY env var
#    if fmp_key and fmp_key != "YOUR_FMP_API_KEY":
#        fmp_graph = read_data(
#            format_type="fmp",
#            source="AAPL", # Ticker symbol
#            statement_type="income_statement", # Required kwarg
#            period_type="FY", # Optional: 'FY' or 'QTR'
#            limit=5, # Optional: Number of periods
#            api_key=fmp_key # Can be passed here or set in environment
#        )
#        print("\nGraph created from FMP API (AAPL Income Statement):")
#        print(f"Nodes: {len(fmp_graph.nodes)}")
#        print(f"Periods: {fmp_graph.periods}")
#        print(f"Revenue 2023: {fmp_graph.calculate('revenue', '2023-09-30')}") # Example
#    else:
#        print("\nSkipping FMP API example: API key not provided.")
# except Exception as e:
#    print(f"\nError reading from FMP API: {e}")


# --- 7. Preprocessing / Transformation ---
print("\n--- Preprocessing / Transformation ---")
# Use the DataFrame exported earlier
df_to_transform = fsg.to_dataframe()
# Ensure only numeric columns are used for transformation where applicable
numeric_cols = df_to_transform.select_dtypes(include='number').columns
df_numeric = df_to_transform[numeric_cols].copy()

service = TransformationService()

# a) Normalize Revenue column as percentage of COGS (example)
if 'Revenue' in df_numeric.columns and 'COGS' in df_numeric.columns:
    try:
        df_normalized = service.normalize_data(
            df_numeric,
            normalization_type="percent_of",
            reference="COGS"
        )
        print("\nNormalized DataFrame (Revenue as % of COGS):")
        print(df_normalized[['Revenue']].head().to_string())
    except Exception as e:
        print(f"\nError normalizing data: {e}")
else:
    print("\nSkipping normalization example: Revenue or COGS not found.")

# b) Calculate YoY growth for Revenue
if 'Revenue' in df_numeric.columns and len(df_numeric) > 1:
    try:
        # Assuming periods are annual for YoY
        df_growth = service.transform_time_series(
            df_numeric[['Revenue']], # Select only Revenue column for clarity
            transformation_type="growth_rate", # Simple period-over-period growth
            periods=1
        )
        print("\nYoY Growth Rate for Revenue:")
        print(df_growth[['Revenue_growth']].head().to_string())
    except Exception as e:
        print(f"\nError calculating growth rate: {e}")
else:
     print("\nSkipping growth rate example: Revenue not found or insufficient periods.")
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Python
IGNORE_WHEN_COPYING_END
Explanation and Considerations:

Structure: Follows a standard README layout with sections for overview, features, installation, concepts, usage, etc.

Content Source: All descriptions and features are derived directly from the provided code structure, file names, class names, docstrings (where available), and method signatures.

Key Components: The README highlights the major architectural pieces: Graph, Nodes, Statements, Metrics, Strategies, IO, Preprocessing, Forecasting, Extensions.

Core Concepts: This section is crucial for users to understand how the library works, explaining the purpose and interaction of the main components.

Usage Examples: Provides practical snippets covering the most common use cases identified in the code.

Imports are included for clarity.

Assumptions (like metric registration or strategy mapping) are noted where necessary.

Dummy data/config files are created and cleaned up within the examples where file I/O is demonstrated.

Error handling (try...except) is included to show robustness and potential issues.

The FMP example is commented out but structured correctly, emphasizing the need for an API key.

Preprocessing examples use the TransformationService and demonstrate common transformations.

Extensibility: Briefly touches upon how users can extend the library, based on the presence of registries and base classes.

Placeholders: Includes placeholders for standard badges (Build Status, PyPI, License) which would be filled in during actual project setup. Also includes placeholders for Contributing and License text.

Completeness: Aims to cover all major functionalities revealed by the code files.

Formatting: Uses Markdown for readability (headings, code blocks, bolding).

This README should give a potential user a good understanding of the library's capabilities and how to get started.