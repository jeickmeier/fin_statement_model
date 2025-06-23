"""Data reader for the Financial Modeling Prep (FMP) API.

This module provides the `FmpReader`, a `DataReader` for fetching financial
statement data directly from the Financial Modeling Prep API. It can retrieve
income statements, balance sheets, and cash flow statements for a given stock
ticker.

The reader handles API key validation, endpoint construction, and the transformation
of the JSON response into a `Graph` object. It also supports mapping of API field
names to the library's canonical node names.
"""

from functools import lru_cache
import logging
import re
from typing import Any, cast

import numpy as np
import requests

from fin_statement_model.config import cfg
from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import FinancialStatementItemNode
from fin_statement_model.io.config.models import FmpReaderConfig
from fin_statement_model.io.core.base import DataReader
from fin_statement_model.io.core.mixins import (
    ConfigurationMixin,
    MappingAwareMixin,
)
from fin_statement_model.io.core.registry import register_reader
from fin_statement_model.io.exceptions import ReadError

logger = logging.getLogger(__name__)


@register_reader("fmp", schema=FmpReaderConfig)
# pylint: disable=too-many-statements,too-many-branches
class FmpReader(DataReader, ConfigurationMixin, MappingAwareMixin):
    """Reads financial statement data from the FMP API into a Graph.

    Fetches data for a specific ticker and statement type (income statement,
    balance sheet, or cash flow). Requires a valid FMP API key, which can be
    provided via configuration, an environment variable (`FMP_API_KEY`), or
    at runtime.

    This reader supports mapping of FMP's API field names to the library's
    canonical node names. A default mapping is provided, but it can be
    customized via the `mapping_config` parameter in the `FmpReaderConfig`.
    It also provides a fallback mechanism to convert unmapped `camelCase` API
    fields to `snake_case`.

    Configuration is provided via an `FmpReaderConfig` object.

    For advanced use cases involving repeated API calls, a single `FmpReader`
    instance can be reused to leverage caching of API key validation.

    Example:
        ```python
        # from fin_statement_model.io import read_data
        # # Fetch Apple's annual income statement
        # config = {
        #     "statement_type": "income_statement",
        #     "period_type": "FY",
        #     "limit": 5,
        #     "api_key": "YOUR_FMP_API_KEY",
        # }
        # graph = read_data(format_type="fmp", source="AAPL", config=config)
        ```
    """

    # Base URL components - keeping version separate for easier future upgrade.
    _API_HOST = "https://financialmodelingprep.com/api"
    _API_VERSION = "v3"
    BASE_URL = f"{_API_HOST}/{_API_VERSION}"

    # Pre-compiled regex used for camelCase→snake_case fallback when no explicit
    # mapping entry exists.  Compiling once avoids repeated re-parsing in the
    # innermost loop of the API-response processing.
    _CAMEL_TO_SNAKE_RE = re.compile(r"(?<!^)(?=[A-Z])")

    @classmethod
    def _get_default_mapping_path(cls) -> str | None:
        """Specify the default mapping file for FMP."""
        return "fmp_default_mappings.yaml"

    def __init__(self, cfg: FmpReaderConfig) -> None:
        """Initialize the FmpReader with validated configuration.

        Args:
            cfg: A validated `FmpReaderConfig` instance containing parameters like
                 `source` (ticker), `api_key`, `statement_type`, `period_type`,
                 `limit`, and `mapping_config`.
        """
        # Initialise mixins to set up configuration context and mapping caches.
        ConfigurationMixin.__init__(self)
        MappingAwareMixin.__init__(self)  # currently a no-op but future-proof

        self.cfg = cfg

    @classmethod
    @lru_cache(maxsize=8)
    def _cached_validate_key(cls, api_key: str) -> None:
        """Cached helper that actually calls the FMP API once per key."""
        if not api_key:
            raise ValueError("Missing API key")
        from fin_statement_model.config import cfg

        test_url = f"{cls.BASE_URL}/profile/AAPL?apikey={api_key}"
        response = requests.get(test_url, timeout=cfg("api.api_timeout"))
        response.raise_for_status()
        if not response.json():
            raise ValueError("Validation endpoint returned empty JSON")

    def _validate_api_key(self, api_key: str) -> None:
        """Wrapper that converts cached validation errors to ReadError."""
        if not api_key:
            raise ReadError(
                "FMP API key is required for reading.",
                source="FMP API",
                reader_type="FmpReader",
            )
        try:
            self._cached_validate_key(api_key)
        except Exception as e:
            logger.exception("FMP API key validation failed")
            raise ReadError(
                f"FMP API key validation failed: {e}",
                source="FMP API",
                reader_type="FmpReader",
                original_error=e,
            ) from e

    def read(self, source: str, **kwargs: Any) -> Graph:
        """Fetch data from the FMP API and return a populated Graph.

        This high-level method now orchestrates four dedicated helpers to keep
        each concern isolated:

        1. _build_api_url            → Constructs the REST endpoint & query params
        2. _fetch_data               → Performs the HTTP request and returns JSON
        3. _parse_fmp_response       → Transforms raw JSON into tabular dict form
        4. _populate_graph           → Builds and returns the final Graph object

        The public behaviour (signature, raised exceptions, logging side-effects)
        remains unchanged.
        """
        ticker = source
        self.set_config_context(ticker=ticker, operation="api_read")

        # ------------------------------------------------------------------
        # Resolve runtime overrides vs. config defaults
        # ------------------------------------------------------------------
        statement_type = kwargs.get("statement_type", self.cfg.statement_type)
        period_type_arg = kwargs.get("period_type", self.cfg.period_type)
        limit = kwargs.get("limit", self.cfg.limit)
        api_key = kwargs.get("api_key", self.cfg.api_key)

        # ------------------------------------------------------------------
        # Validate inputs & API key
        # ------------------------------------------------------------------
        if not ticker or not isinstance(ticker, str):
            raise ReadError(
                "Invalid source (ticker) provided. Expected a non-empty string.",
                source=str(ticker),
                reader_type="FmpReader",
            )

        self._validate_api_key(cast("str", api_key))

        # Prepare field-name mapping for this request
        try:
            mapping = self._get_mapping(statement_type)
        except TypeError as te:
            raise ReadError(
                "Invalid mapping_config provided.",
                source=ticker,
                reader_type="FmpReader",
                original_error=te,
            ) from te

        # ------------------------------------------------------------------
        # 1. Build URL & params  -------------------------------------------------
        endpoint, params = self._build_api_request(
            ticker=ticker,
            statement_type=statement_type,
            period_type=period_type_arg,
            limit=limit,
            api_key=cast("str", api_key),
        )

        # ------------------------------------------------------------------
        # 2. Fetch JSON payload -------------------------------------------------
        api_data = self._fetch_data(endpoint, params, ticker, statement_type)

        # Shortcut: empty payload → empty graph
        if not api_data:
            logger.warning("FMP API returned empty list for %s %s.", ticker, statement_type)
            return Graph(periods=[])

        # ------------------------------------------------------------------
        # 3. Parse response → structured dict ----------------------------------
        periods, item_matrix = self._parse_fmp_response(api_data, mapping)

        # ------------------------------------------------------------------
        # 4. Transform to Graph -------------------------------------------------
        graph = self._populate_graph(periods, item_matrix)

        logger.info(
            "Successfully created graph with %s nodes from FMP API for %s %s.",
            len(graph.nodes),
            ticker,
            statement_type,
        )
        return graph

    # ------------------------------------------------------------------
    # Private helpers - extracted from the monolithic read() implementation
    # ------------------------------------------------------------------

    def _build_api_request(
        self,
        *,
        ticker: str,
        statement_type: str,
        period_type: str,
        limit: int,
        api_key: str,
    ) -> tuple[str, dict[str, Any]]:
        """Return endpoint URL and query-parameter dict for an FMP request."""
        endpoint_path = statement_type.replace("_", "-")
        url = f"{self.BASE_URL}/{endpoint_path}/{ticker}"
        params: dict[str, Any] = {"apikey": api_key, "limit": limit}
        if period_type == "QTR":
            params["period"] = "quarter"
        return url, params

    def _fetch_data(
        self,
        url: str,
        params: dict[str, Any],
        ticker: str,
        statement_type: str,
    ) -> list[dict[str, Any]]:
        """Perform the HTTP request and return the decoded JSON list.

        The method separates the network call (inside the ``try`` block) from the
        normal, exception-free return path (in the ``else`` block) to appease
        Ruff's TRY300 rule while keeping the logic clear and unchanged.
        """
        try:
            logger.info(
                "Fetching %s for %s from FMP API (%s periods)…",
                statement_type,
                ticker,
                params.get("limit"),
            )

            response = requests.get(url, params=params, timeout=cfg("api.api_timeout"))
            response.raise_for_status()

            payload = response.json()

            if not isinstance(payload, list):
                raise ReadError(
                    (f"Unexpected API response format. Expected list, got {type(payload).__name__}."),
                    source=f"FMP API ({ticker})",
                    reader_type="FmpReader",
                )

        except requests.exceptions.RequestException as rex:
            # Convert low-level network issues to domain-specific ReadError.
            raise ReadError(
                f"FMP API request failed: {rex}",
                source=f"FMP API ({ticker})",
                reader_type="FmpReader",
                original_error=rex,
            ) from rex
        else:
            # Only executed if no exception was raised in the ``try`` block.
            return payload

    def _parse_fmp_response(
        self,
        api_data: list[dict[str, Any]],
        mapping: dict[str, str],
    ) -> tuple[list[str], dict[str, dict[str, float]]]:
        """Convert raw FMP JSON payload to a period-indexed value matrix."""
        # FMP returns newest-first; reverse to chronological order
        api_data.reverse()

        # Extract period strings safely, ensuring correct type for static checker
        periods: list[str] = []
        for record in api_data:
            date_val = record.get("date")
            if isinstance(date_val, str) and date_val:
                periods.append(date_val)

        if not periods:
            raise ReadError(
                "Could not extract periods ('date' field) from FMP API response.",
                source="FMP API",
                reader_type="FmpReader",
            )

        # Pre-initialise matrix with NaN placeholders
        item_matrix: dict[str, dict[str, float]] = {}
        for record in api_data:
            period = record.get("date")
            if not period:
                continue
            for api_field, value in record.items():
                node_name = self._apply_mapping(api_field, mapping)
                if node_name == api_field:  # unmapped → try camel→snake fallback
                    node_name = self._camel_to_snake(api_field)

                if node_name not in item_matrix:
                    item_matrix[node_name] = dict.fromkeys(periods, np.nan)

                if isinstance(value, int | float):
                    item_matrix[node_name][period] = float(value)

        return periods, item_matrix

    def _populate_graph(
        self,
        periods: list[str],
        item_matrix: dict[str, dict[str, float]],
    ) -> Graph:
        """Create a Graph instance from the period/value matrix."""
        graph = Graph(periods=periods)
        import numpy as np

        for node_name, period_values in item_matrix.items():
            valid_values = {p: v for p, v in period_values.items() if not np.isnan(v)}
            if valid_values:
                graph.add_node(FinancialStatementItemNode(name=node_name, values=valid_values))
        return graph

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @classmethod
    def _camel_to_snake(cls, name: str) -> str:
        """Convert *CamelCase* or *camelCase* to *snake_case* quickly."""
        return cls._CAMEL_TO_SNAKE_RE.sub("_", name).lower()
