"""Financial Modeling Prep API Example.

This example demonstrates fetching financial data from the FMP API
and using it with the fin_statement_model library.
"""

import logging
import sys

from fin_statement_model.config import get_config, update_config
from fin_statement_model.io import read_data
from fin_statement_model.statements import create_statement_dataframe

# Get configuration
config = get_config()

# Override logging level for this example if needed
update_config({"logging": {"level": "INFO"}})


logger = logging.getLogger(__name__)

# Configuration
TICKER = "AAPL"  # Apple Inc.
STATEMENT_TYPE = "income_statement"  # income_statement, balance_sheet, or cash_flow
PERIOD_TYPE = "FY"  # FY (annual) or QTR (quarterly)
LIMIT = 5  # Number of periods to fetch

# API configuration from centralized config
# The API key can be set via:
# 1. Environment variable: FSM_API_FMP_API_KEY
# 2. Config file: api.fmp_api_key
# 3. Runtime: update_config({'api': {'fmp_api_key': 'your_key'}})
if not config.api.fmp_api_key:
    logger.error("FMP API key not configured!")
    logger.info("Set it using one of these methods:")
    logger.info("1. Environment variable: export FSM_API_FMP_API_KEY=your_key")
    logger.info("2. Config file: add 'fmp_api_key: your_key' under 'api:' section")
    logger.info("3. Runtime: update_config({'api': {'fmp_api_key': 'your_key'}})")
    sys.exit(1)

# FMP reader configuration using centralized settings
fmp_config = {
    "source": TICKER,
    "format_type": "fmp",
    "statement_type": STATEMENT_TYPE,
    "period_type": PERIOD_TYPE,
    "limit": LIMIT,
    "api_key": config.api.fmp_api_key,  # Use API key from config
}


def fetch_fmp_data() -> object:
    """Fetch financial data from FMP API."""
    logger.info(f"Fetching {STATEMENT_TYPE} data for {TICKER}...")

    # Use configured timeout and retry settings
    if hasattr(read_data, "_reader"):
        # Apply API configuration settings if reader supports them
        read_data._reader.timeout = config.api.api_timeout
        read_data._reader.retry_count = config.api.api_retry_count

    try:
        # Read data from FMP API
        graph = read_data(
            format_type="fmp",
            source=fmp_config,
        )

        logger.info(f"✓ Successfully fetched data for periods: {graph.periods}")
        logger.info(f"✓ Created {len(graph.nodes)} nodes")

        # Display sample data
        sample_node = next(iter(graph.nodes.values()))
        logger.info(f"\nSample node '{sample_node.name}':")
        for period in sorted(graph.periods)[:3]:  # Show first 3 periods
            value = sample_node.get_value(period)
            if value is not None:
                # Format using display config
                formatted_value = f"{value * config.display.scale_factor:{config.display.default_currency_format}}"
                logger.info(
                    f"  {period}: {formatted_value} {config.display.default_units}"
                )

        return graph

    except Exception as e:
        logger.exception(f"Error fetching data: {e}")
        raise


def main():
    """Run the FMP example."""
    logger.info("=" * 60)
    logger.info(f"FMP API EXAMPLE - {TICKER}")
    logger.info("=" * 60)

    # Fetch data from FMP
    graph = fetch_fmp_data()

    # Try to create a formatted statement if config exists
    try:
        config_path = f"configs/{STATEMENT_TYPE}.yaml"
        logger.info(f"\nCreating formatted statement using {config_path}...")

        statement_df = create_statement_dataframe(
            graph=graph,
            config_path_or_dir=config_path,
            format_kwargs={
                "number_format": config.display.default_currency_format,
                "should_apply_signs": True,
                "hide_zero_rows": config.display.hide_zero_rows,
            },
        )

        logger.info("\nFormatted Statement:")
        logger.info(statement_df.to_string(index=False))

    except Exception as e:
        logger.warning(f"Could not create formatted statement: {e}")
        logger.info("Note: To use statement formatting, create a statement config file")

    logger.info("\n" + "=" * 60)
    logger.info("EXAMPLE COMPLETE")
    logger.info("=" * 60)

    # Show cache info if caching is enabled
    if config.api.cache_api_responses:
        logger.info(
            f"\nNote: API responses are cached for {config.api.cache_ttl_hours} hours"
        )
        logger.info("To refresh data, clear cache or wait for TTL expiration")


if __name__ == "__main__":
    main()
