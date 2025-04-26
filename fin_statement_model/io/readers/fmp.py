"""Data reader for the Financial Modeling Prep (FMP) API."""

import logging
import os
import requests
from typing import Optional, ClassVar, Any
import numpy as np
import yaml
from pathlib import Path

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import FinancialStatementItemNode
from fin_statement_model.io.base import DataReader
from fin_statement_model.io.registry import register_reader
from fin_statement_model.io.exceptions import ReadError
from fin_statement_model.io.readers.base import MappingConfig, normalize_mapping

logger = logging.getLogger(__name__)


@register_reader("fmp")
class FmpReader(DataReader):
    """Reads financial statement data from the FMP API into a Graph.

    Fetches data for a specific ticker and statement type.
    Requires an API key, either passed directly or via the FMP_API_KEY env var.

    Supports a `mapping_config` constructor parameter for mapping API field names to canonical node names,
    accepting either a flat mapping or a statement-type keyed mapping.

    Note:
        When using the `read_data` facade, pass `api_key` and `mapping_config` via init,
        and reader-specific options (`statement_type`, `period_type`, `limit`) to the `read()` method.
        Direct instantiation of `FmpReader` is also supported.

    Stateful Use:
        For advanced use cases involving repeated API calls, consider instantiating
        and reusing a single `FmpReader` instance to avoid redundant API key
        validations and improve performance.
    """

    BASE_URL = "https://financialmodelingprep.com/api/v3"

    # Load default mappings from YAML configuration
    DEFAULT_MAPPINGS: ClassVar[dict[str, dict[str, str]]] = {}

    @classmethod
    def _load_default_mappings(cls) -> None:
        """Load default mapping configurations from YAML file into DEFAULT_MAPPINGS."""
        # Load mapping YAML from config directory relative to this file
        config_path = Path(__file__).parent / "config" / "fmp_default_mappings.yaml"
        with config_path.open("r", encoding="utf-8") as f:
            cls.DEFAULT_MAPPINGS = yaml.safe_load(f)

    # Default statement types requested from FMP API
    _STATEMENT_TYPES: ClassVar[dict[str, str]] = {
        "income_statement": "income-statement",
        "balance_sheet": "balance-sheet-statement",
        "cash_flow": "cash-flow-statement",
    }
    # Mapping from API field names to standard node names
    _API_ENDPOINTS: ClassVar[dict[str, str]] = {
        "income_statement": "income-statement",
        "balance_sheet": "balance-sheet-statement",
        "cash_flow": "cash-flow-statement",
    }
    # Default required parameters for the API
    _REQUIRED_PARAMS: ClassVar[list[str]] = ["apikey"]

    def __init__(
        self,
        api_key: Optional[str] = None,
        mapping_config: MappingConfig = None,
    ) -> None:
        """Initialize the FmpReader.

        Args:
            api_key: FMP API key. If None, attempts to use FMP_API_KEY env var.
            mapping_config (MappingConfig): Optional mapping configuration to
                override default API field mappings. Can be either:
                  - Dict[str, str] for a flat mapping.
                  - Dict[Optional[str], Dict[str, str]] for scoped mappings
                    keyed by statement type (or None for default).
        """
        self.api_key = api_key or os.environ.get("FMP_API_KEY")
        if not self.api_key:
            logger.warning(
                "FMP API key not provided via init or FMP_API_KEY env var."
            )

        # Store raw mapping_config for later resolution
        self.mapping_config = mapping_config

    def _get_mapping(
        self,
        statement_type: Optional[str],
        mapping_config: MappingConfig = None,
    ) -> dict[str, str]:
        """Get the appropriate mapping based on statement type and optional override config."""
        # Start with defaults based on statement type loaded from config
        mapping = dict(self.DEFAULT_MAPPINGS.get(statement_type, {}))

        # Choose override config if provided, else use instance config
        config = mapping_config if mapping_config is not None else self.mapping_config
        # Normalize and overlay user-provided mappings
        user_map = normalize_mapping(config, context_key=statement_type)
        mapping.update(user_map)
        return mapping

    def _validate_api_key(self):
        """Perform a simple check if the API key seems valid."""
        if not self.api_key:
            raise ReadError(
                "FMP API key is required for reading.",
                source="FMP API",
                reader_type="FmpReader",
            )
        try:
            # Use a cheap endpoint for validation
            test_url = f"{self.BASE_URL}/profile/AAPL?apikey={self.api_key}"  # Example
            response = requests.get(test_url, timeout=10)
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

    def read(self, source: str, **kwargs: dict[str, Any]) -> Graph:
        """Fetch data from FMP API and return a Graph.

        Args:
            source (str): The stock ticker symbol (e.g., "AAPL").
            **kwargs: Required keyword arguments:
                statement_type (str): Type of statement ('income_statement', 'balance_sheet', 'cash_flow').
            Optional keyword arguments:
                period_type (str): 'FY' for annual (default) or 'QTR' for quarterly.
                limit (int): Number of past periods to fetch (default: 50).
                mapping_config (MappingConfig): Overrides the mapping configuration provided at init.
                    Accepts either a flat `Dict[str, str]` or a scoped `Dict[Optional[str], Dict[str, str]]`.
                api_key (str): Overrides the API key provided at init.

        Returns:
            A new Graph instance populated with FinancialStatementItemNodes.

        Raises:
            ReadError: If API key is missing/invalid, API request fails, or data format is unexpected.
        """
        ticker = source
        statement_type = kwargs.get("statement_type")
        period_type_arg = kwargs.get("period_type", "FY")
        limit = kwargs.get("limit", 50)
        self.api_key = kwargs.get("api_key", self.api_key)

        # --- Validate Inputs ---
        if not ticker or not isinstance(ticker, str):
            raise ReadError(
                "Invalid source (ticker) provided. Expected a non-empty string.",
                source=ticker,
                reader_type="FmpReader",
            )
        if statement_type not in ["income_statement", "balance_sheet", "cash_flow"]:
            raise ReadError(
                "Missing or invalid required argument: 'statement_type'. Must be one of: income_statement, balance_sheet, cash_flow.",
                source=ticker,
                reader_type="FmpReader",
            )
        if period_type_arg not in ["FY", "QTR"]:
            raise ReadError(
                "Invalid 'period_type'. Must be 'FY' or 'QTR'.",
                source=ticker,
                reader_type="FmpReader",
            )

        self._validate_api_key()  # Ensure API key is usable

        # Determine mapping for this operation, allowing override via kwargs
        current_mapping_config = kwargs.get("mapping_config")
        try:
            mapping = self._get_mapping(
                statement_type,
                mapping_config=current_mapping_config,
            )
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
        params = {"apikey": self.api_key, "limit": limit}
        if period_type_arg == "QTR":
            params["period"] = "quarter"

        try:
            logger.info(
                f"Fetching {period_type_arg} {statement_type} for {ticker} from FMP API (limit={limit})."
            )
            response = requests.get(endpoint, params=params, timeout=30)  # Increased timeout
            response.raise_for_status()  # Check for HTTP errors
            api_data = response.json()

            if not isinstance(api_data, list):
                raise ReadError(
                    f"Unexpected API response format. Expected list, got {type(api_data)}. Response: {str(api_data)[:100]}...",
                    source=f"FMP API ({ticker})",
                    reader_type="FmpReader",
                )
            if not api_data:
                logger.warning(f"FMP API returned empty list for {ticker} {statement_type}.")
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
                    node_name = mapping.get(api_field, api_field)  # Use mapping or fallback

                    # Initialize node data dict if first time seeing this node
                    if node_name not in all_item_data:
                        all_item_data[node_name] = {p: np.nan for p in periods}  # Pre-fill with NaN

                    # Store value for this period
                    if isinstance(value, (int, float)):
                        all_item_data[node_name][period] = float(value)

            # Create nodes from collected data
            nodes_added = 0
            for node_name, period_values in all_item_data.items():
                # Filter out periods that only have NaN
                valid_period_values = {p: v for p, v in period_values.items() if not np.isnan(v)}
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
            logger.error(f"Failed to parse FMP data and build graph: {e}", exc_info=True)
            raise ReadError(
                message=f"Failed to parse FMP data: {e}",
                source=f"FMP API ({ticker})",
                reader_type="FmpReader",
                original_error=e,
            ) from e

# After class definition, load default mappings
FmpReader._load_default_mappings()
