"""Data reader for the Financial Modeling Prep (FMP) API."""

import logging
import requests
from typing import Optional, Any
import numpy as np


from fin_statement_model.config import cfg
from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import FinancialStatementItemNode
from fin_statement_model.io.core.base import DataReader
from fin_statement_model.io.core.mixins import (
    MappingAwareMixin,
    ConfigurationMixin,
)
from fin_statement_model.io.core.registry import register_reader
from fin_statement_model.io.exceptions import ReadError

from fin_statement_model.io.config.models import FmpReaderConfig

logger = logging.getLogger(__name__)


@register_reader("fmp")
class FmpReader(DataReader, ConfigurationMixin, MappingAwareMixin):
    """Reads financial statement data from the FMP API into a Graph.

    Fetches data for a specific ticker and statement type.
    Requires an API key, either passed directly or via the FMP_API_KEY env var.

    Supports a `mapping_config` constructor parameter for mapping API field names to canonical node names,
    accepting either a flat mapping or a statement-type keyed mapping.

    Configuration (api_key, statement_type, period_type, limit, mapping_config)
    is passed via an `FmpReaderConfig` object during initialization (typically by
    the `read_data` facade). The `.read()` method currently takes no specific
    keyword arguments beyond the `source` (ticker).

    Stateful Use:
        For advanced use cases involving repeated API calls, consider instantiating
        and reusing a single `FmpReader` instance to avoid redundant API key
        validations and improve performance.
    """

    BASE_URL = "https://financialmodelingprep.com/api/v3"

    @classmethod
    def _get_default_mapping_path(cls) -> Optional[str]:
        """Specify the default mapping file for FMP."""
        return "fmp_default_mappings.yaml"

    def __init__(self, cfg: FmpReaderConfig) -> None:
        """Initialize the FmpReader with validated configuration.

        Args:
            cfg: A validated `FmpReaderConfig` instance containing parameters like
                 `source` (ticker), `api_key`, `statement_type`, `period_type`,
                 `limit`, and `mapping_config`.
        """
        self.cfg = cfg

    def _validate_api_key(self) -> None:
        """Perform a simple check if the API key seems valid."""
        # API key is now guaranteed by FmpReaderConfig validation
        api_key = self.cfg.api_key
        if not api_key:  # Should not happen if validation passed, but defensive check
            raise ReadError(
                "FMP API key is required for reading.",
                source="FMP API",
                reader_type="FmpReader",
            )
        try:
            # Use a cheap endpoint for validation
            test_url = f"{self.BASE_URL}/profile/AAPL?apikey={api_key}"  # Example
            response = requests.get(test_url, timeout=cfg("api.api_timeout"))
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
            # Basic check on response content if needed
            if not response.json():
                raise ReadError(
                    "API key validation returned empty response.",
                    source="FMP API",
                    reader_type="FmpReader",
                )
            logger.debug("FMP API key validated successfully.")
        except requests.exceptions.RequestException as e:
            logger.error(f"FMP API key validation failed: {e}", exc_info=True)
            raise ReadError(
                f"FMP API key validation failed: {e}",
                source="FMP API",
                reader_type="FmpReader",
                original_error=e,
            )

    def read(self, source: str, **kwargs: Any) -> Graph:
        """Fetch data from FMP API and return a Graph.

        Args:
            source (str): The stock ticker symbol (e.g., "AAPL").
            **kwargs: Currently unused. Configuration is handled by the `FmpReaderConfig`
                      object passed during initialization.

        Returns:
            A new Graph instance populated with FinancialStatementItemNodes.

        Raises:
            ReadError: If API key is missing/invalid, API request fails, or data format is unexpected.
        """
        ticker = source

        # Set configuration context for better error reporting
        self.set_config_context(ticker=ticker, operation="api_read")

        # Parameters now come directly from the validated config with enhanced access
        statement_type = self.require_config_value("statement_type", value_type=str)
        period_type_arg = self.require_config_value("period_type", value_type=str)
        limit = self.get_config_value(
            "limit", default=5, value_type=int, validator=lambda x: x > 0
        )
        api_key = self.get_config_with_env_fallback(
            "api_key", "FMP_API_KEY", value_type=str
        )

        # --- Validate Inputs ---
        if not ticker or not isinstance(ticker, str):
            raise ReadError(
                "Invalid source (ticker) provided. Expected a non-empty string.",
                source=ticker,
                reader_type="FmpReader",
            )
        # statement_type and period_type are validated by FmpReaderConfig

        self._validate_api_key()  # Ensure API key is usable

        # Determine mapping for this operation, allowing override via kwargs
        # Mapping is now determined solely by the config passed during __init__
        try:
            mapping = self._get_mapping(statement_type)
        except TypeError as te:
            raise ReadError(
                "Invalid mapping_config provided.",
                source=ticker,
                reader_type="FmpReader",
                original_error=te,
            )
        logger.debug(f"Using mapping for {ticker} {statement_type}: {mapping}")

        # --- Fetch API Data ---
        # Correct endpoint construction based on FMP v3 docs
        # e.g., /income-statement/AAPL, not /income_statement-statement/AAPL
        endpoint_path = statement_type.replace("_", "-")
        endpoint = f"{self.BASE_URL}/{endpoint_path}/{ticker}"
        params = {"apikey": api_key, "limit": limit}
        if period_type_arg == "QTR":
            params["period"] = "quarter"

        try:
            logger.info(
                f"Fetching {period_type_arg} {statement_type} for {ticker} from FMP API (limit={limit})."
            )
            response = requests.get(
                endpoint, params=params, timeout=cfg("api.api_timeout")
            )
            response.raise_for_status()  # Check for HTTP errors
            api_data = response.json()

            if not isinstance(api_data, list):
                raise ReadError(
                    f"Unexpected API response format. Expected list, got {type(api_data)}. Response: {str(api_data)[:100]}...",
                    source=f"FMP API ({ticker})",
                    reader_type="FmpReader",
                )
            if not api_data:
                logger.warning(
                    f"FMP API returned empty list for {ticker} {statement_type}."
                )
                # Return empty graph or raise? Returning empty for now.
                return Graph(periods=[])

        except requests.exceptions.RequestException as e:
            logger.error(
                f"FMP API request failed for {ticker} {statement_type}: {e}",
                exc_info=True,
            )
            raise ReadError(
                f"FMP API request failed: {e}",
                source=f"FMP API ({ticker})",
                reader_type="FmpReader",
                original_error=e,
            )
        except Exception as e:
            logger.error(f"Failed to process FMP API response: {e}", exc_info=True)
            raise ReadError(
                f"Failed to process FMP API response: {e}",
                source=f"FMP API ({ticker})",
                reader_type="FmpReader",
                original_error=e,
            )

        # --- Process Data and Populate Graph ---
        try:
            # FMP data is usually newest first, reverse to process chronologically
            api_data.reverse()

            # Extract periods (e.g., 'date' or 'fillingDate')
            # Using 'date' as it usually represents the period end date
            periods = [item.get("date") for item in api_data if item.get("date")]
            if not periods:
                raise ReadError(
                    "Could not extract periods ('date' field) from FMP API response.",
                    source=f"FMP API ({ticker})",
                    reader_type="FmpReader",
                )

            graph = Graph(periods=periods)
            all_item_data: dict[str, dict[str, float]] = {}

            # Collect data for all items across all periods
            for period_data in api_data:
                period = period_data.get("date")
                if not period:
                    continue  # Skip records without a date

                for api_field, value in period_data.items():
                    node_name = self._apply_mapping(api_field, mapping)

                    # Initialize node data dict if first time seeing this node
                    if node_name not in all_item_data:
                        all_item_data[node_name] = {
                            p: np.nan for p in periods
                        }  # Pre-fill with NaN

                    # Store value for this period
                    if isinstance(value, int | float):
                        all_item_data[node_name][period] = float(value)

            # Create nodes from collected data
            nodes_added = 0
            for node_name, period_values in all_item_data.items():
                # Filter out periods that only have NaN
                valid_period_values = {
                    p: v for p, v in period_values.items() if not np.isnan(v)
                }
                if valid_period_values:
                    new_node = FinancialStatementItemNode(
                        name=node_name, values=valid_period_values
                    )
                    graph.add_node(new_node)
                    nodes_added += 1

            logger.info(
                f"Successfully created graph with {nodes_added} nodes from FMP API for {ticker} {statement_type}."
            )
            return graph

        except Exception as e:
            logger.error(
                f"Failed to parse FMP data and build graph: {e}", exc_info=True
            )
            raise ReadError(
                message=f"Failed to parse FMP data: {e}",
                source=f"FMP API ({ticker})",
                reader_type="FmpReader",
                original_error=e,
            ) from e
