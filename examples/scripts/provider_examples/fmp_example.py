"""FMP (Financial Modeling Prep) API Example.

This example demonstrates how to use the FMP API reader to fetch financial data
and load it into a financial statement graph.

Prerequisites:
- Set FMP_API_KEY environment variable with your API key
- Install requests library if not already installed
"""

import logging
import os
from fin_statement_model.io import read_data, write_data

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
TICKER = "AAPL"  # Stock ticker to fetch
STATEMENT_TYPE = "income"  # Options: 'income', 'balance', 'cash'
PERIOD_TYPE = "annual"  # Options: 'annual', 'quarter'

# FMP API configuration
FMP_API_KEY = os.environ.get("FMP_API_KEY")

# Example function to demonstrate FMP usage
def fetch_fmp_data():
    """Fetch financial data from FMP API and create a graph."""
    
    if not FMP_API_KEY:
        logger.error("FMP_API_KEY environment variable not set.")
        logger.error("Please set it with: export FMP_API_KEY='your_api_key'")
        return None
    
    # FMP reader configuration
    fmp_config = {
        "ticker": TICKER,
        "statement_type": STATEMENT_TYPE,
        "period_type": PERIOD_TYPE,
        "api_key": FMP_API_KEY,
        "limit": 5,  # Number of periods to fetch
    }
    
    try:
        logger.info(f"Fetching {PERIOD_TYPE} {STATEMENT_TYPE} data for {TICKER}...")
        
        # Use the FMP reader to fetch data
        graph = read_data(
            format_type="fmp",
            source=fmp_config,
            # Optional: provide custom node mappings
            node_mappings={
                "revenue": ["revenue", "totalRevenue"],
                "gross_profit": ["grossProfit"],
                "operating_income": ["operatingIncome"],
                "net_income": ["netIncome"],
            }
        )
        
        logger.info(f"Successfully fetched data. Graph has {len(graph.nodes)} nodes.")
        return graph
        
    except ValueError as e:
        if "fmp" in str(e).lower():
            logger.error("Error: The 'fmp' reader format is unavailable or not registered.")
            logger.error("Please ensure the FMP reader is properly installed.")
        else:
            logger.error(f"Error reading data from FMP API: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
    
    return None


def convert_to_dataframe(graph):
    """Convert graph to DataFrame for easy viewing."""
    if graph is None:
        return None
    
    try:
        logger.info("Converting graph to DataFrame...")
        df = write_data(
            format_type="dataframe",
            graph=graph,
            target=None,  # Return DataFrame instead of writing to file
        )
        logger.info("Conversion successful.")
        return df
    except Exception as e:
        logger.error(f"Error converting to DataFrame: {e}")
        return None


def main():
    """Main function to demonstrate FMP data fetching."""
    # Fetch data from FMP
    graph = fetch_fmp_data()
    
    if graph:
        # Convert to DataFrame for display
        df = convert_to_dataframe(graph)
        
        if df is not None:
            logger.info(f"\n--- FMP Data for {TICKER} ({STATEMENT_TYPE}, {PERIOD_TYPE}) ---")
            
            # Display specific rows if they exist
            if "revenue" in df.index:
                logger.info("\nRevenue:")
                try:
                    # Try to format numbers nicely
                    logger.info(df.loc[["revenue"]].map("{:,.0f}".format))
                except:
                    logger.info(df.loc[["revenue"]])  # Print raw if formatting fails
            
            logger.info("\n--- DataFrame Head ---")
            logger.info(df.head(10))  # Print head for brevity
    else:
        logger.info("\nCould not generate DataFrame due to previous errors.")


if __name__ == "__main__":
    main()
