"""Fetches FMP data, converts to graphs, and displays as DataFrame.

Demonstrates fetching data using the FMP reader, converting the raw
data graph into a FinancialStatementGraph, and finally presenting
the information as a pandas DataFrame.

Requires:
- fin_statement_model library installed.
- FMP_API_KEY environment variable set with your Financial Modeling Prep API key.

"""

import logging
import os
import pandas as pd
from typing import Optional

from fin_statement_model.core.graph import Graph
from fin_statement_model.io import (
    read_data,
    write_data,
    ReadError,
    FormatNotSupportedError,
)
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Basic logging configuration (optional, can be removed if desired)
logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")

TICKER = "AAPL"  # Example ticker
STATEMENT_TYPE = "income_statement"  # Options: 'income_statement', 'balance_sheet', 'cash_flow'
PERIOD_TYPE = "FY"  # Options: 'FY' (annual), 'QTR' (quarterly)
LIMIT = 5  # Number of past periods to fetch


# --- Main Script ---
def main():
    """Runs the FMP data fetching and conversion example."""
    print(f"Fetching {PERIOD_TYPE} {STATEMENT_TYPE} data for {TICKER}...")

    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        print("Error: FMP_API_KEY environment variable not set.")
        return

    graph: Optional[Graph] = None  # Renamed from core_graph for simplicity
    df: Optional[pd.DataFrame] = None

    try:
        # 1. Read data from FMP API into a core Graph object
        graph = read_data(
            format_type="fmp",
            source=TICKER,
            api_key=api_key,
            statement_type=STATEMENT_TYPE,
            period_type=PERIOD_TYPE,
            limit=LIMIT,
        )
        print(f"Successfully fetched data. Graph has {len(graph.nodes)} nodes.")

        # 3. Convert Graph to DataFrame using the utility
        print("Converting graph to DataFrame...")
        # Use the write_data facade, which handles configuration
        df = write_data(format_type="dataframe", graph=graph, target=None)
        print("Conversion successful.")

    except FormatNotSupportedError:
        print("Error: The 'fmp' reader format is unavailable or not registered.")
    except ReadError as e:
        print(f"Error reading data from FMP API: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        # Optionally re-raise if debugging: raise e

    # 4. Display results if successful
    if df is not None:
        print(f"\n--- FMP Data for {TICKER} ({STATEMENT_TYPE}, {PERIOD_TYPE}) ---")
        # Example: Accessing specific data if needed
        if "revenue" in df.index:
            print("\nRevenue:")
            # Ensure correct formatting, applymap might error if columns aren't numeric
            try:
                print(df.loc[["revenue"]].map("{:,.0f}".format))
            except (TypeError, ValueError):
                print(df.loc[["revenue"]])  # Print raw if formatting fails

        print("\n--- DataFrame Head ---")
        print(df.head(10))  # Print head for brevity
    else:
        print("\nCould not generate DataFrame due to previous errors.")


if __name__ == "__main__":
    main()
