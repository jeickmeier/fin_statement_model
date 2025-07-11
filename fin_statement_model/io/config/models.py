"""Pydantic models for I/O reader and writer configuration.

This module defines a suite of Pydantic models that serve as declarative schemas
for configuring the various data readers and writers within the `fin_statement_model.io`
package. These models ensure that all configuration passed to I/O components is
well-formed, validated, and type-safe.

Each reader and writer (e.g., for CSV, Excel, FMP API) has a corresponding
configuration model (e.g., `CsvReaderConfig`, `ExcelWriterConfig`). These models
define format-specific options, handle default values, and can perform complex
validation logic, providing a robust and predictable interface for data import
and export operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from fin_statement_model.config.access import cfg

# -----------------------------------------------------------------------------
# Conditional imports for typing/runtime without reassigning the same identifiers
# -----------------------------------------------------------------------------

if TYPE_CHECKING:  # pragma: no cover - import solely for static type checking
    import pandas as pd  # pylint: disable=import-error

    from fin_statement_model.core.adjustments.models import AdjustmentFilterInput
    from fin_statement_model.io.core.types import MappingConfig
else:  # Runtime fallbacks to avoid hard dependencies during import time
    try:
        from fin_statement_model.core.adjustments.models import AdjustmentFilterInput  # type: ignore
    except ImportError:  # pragma: no cover
        AdjustmentFilterInput = Any  # type: ignore[misc,assignment]

    try:
        from fin_statement_model.io.core.types import MappingConfig  # type: ignore
    except ImportError:  # pragma: no cover
        MappingConfig = Any  # type: ignore[misc,assignment]

    import importlib

    try:
        pd = importlib.import_module("pandas")  # type: ignore
    except ModuleNotFoundError:  # pragma: no cover
        pd = Any  # type: ignore[misc]

# -----------------------------------------------------------------------------


class BaseReaderConfig(BaseModel):
    """Base configuration for IO readers."""

    source: Any = Field(..., description="URI, path, or in-memory object representing the data source.")
    format_type: Literal[
        "csv",
        "excel",
        "dataframe",
        "dict",
        "fmp",
        "graph_definition_dict",
    ] = Field(..., description="Reader format identifier.")

    model_config = ConfigDict(extra="forbid", frozen=True)


class CsvReaderConfig(BaseReaderConfig):
    """CSV reader options."""

    # Falls back to cfg("io.default_csv_delimiter") when not supplied
    delimiter: str = Field(
        default_factory=lambda: cfg("io.default_csv_delimiter"),
        description="Field delimiter for CSV files.",
    )
    header_row: int = Field(1, description="Row number containing column names (1-indexed).")
    index_col: int | None = Field(None, description="1-indexed column for row labels.")
    mapping_config: MappingConfig | None = Field(
        None, description="Optional configuration for mapping source item names."
    )

    # Runtime override options: these will override config defaults when provided at read-time
    statement_type: Literal["income_statement", "balance_sheet", "cash_flow"] | None = Field(
        None,
        description="Type of statement ('income_statement', 'balance_sheet', 'cash_flow') to select mapping scope.",
    )
    item_col: str | None = Field(None, description="Name of the column containing item identifiers.")
    period_col: str | None = Field(None, description="Name of the column containing period identifiers.")
    value_col: str | None = Field(None, description="Name of the column containing numeric values.")
    pandas_read_csv_kwargs: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional kwargs for pandas.read_csv, overriding config defaults.",
    )

    # Override with specific source type - file path
    source: str = Field(..., description="Path to the CSV file")

    @model_validator(mode="after")  # type: ignore[arg-type]
    @classmethod
    def check_header_row(cls, cfg: CsvReaderConfig) -> CsvReaderConfig:
        """Ensure `header_row` is a positive integer."""
        if cfg.header_row < 1:
            raise ValueError("header_row must be >= 1")
        return cfg


class ExcelReaderConfig(BaseReaderConfig):
    """Excel reader options."""

    # Uses cfg("io.default_excel_sheet") unless caller overrides
    sheet_name: str | None = Field(
        default_factory=lambda: cfg("io.default_excel_sheet"),
        description="Worksheet name or index.",
    )
    items_col: int = Field(1, description="1-indexed column where item names reside.")
    periods_row: int = Field(1, description="1-indexed row where periods reside.")
    mapping_config: MappingConfig | None = Field(
        None, description="Optional configuration for mapping source item names."
    )

    statement_type: Literal["income_statement", "balance_sheet", "cash_flow"] | None = Field(
        None,
        description="Type of statement ('income_statement', 'balance_sheet', 'cash_flow'). Used to select a mapping scope.",
    )
    header_row: int | None = Field(None, description="1-indexed row for pandas header reading.")
    nrows: int | None = Field(None, description="Number of rows to read from the sheet.")
    skiprows: int | None = Field(None, description="Number of rows to skip at the beginning.")

    # Explicit file-path source
    source: str = Field(..., description="Path to the Excel file")

    @model_validator(mode="after")  # type: ignore[arg-type]
    @classmethod
    def check_indices(cls, cfg: ExcelReaderConfig) -> ExcelReaderConfig:
        """Ensure indices are valid and that `header_row` and `periods_row` are exclusive."""
        if cfg.items_col < 1 or cfg.periods_row < 1:
            raise ValueError("items_col and periods_row must be >= 1")

        # Enforce XOR semantics between header_row and periods_row when both are *explicitly* supplied.
        # The default behaviour allows **one** of them (or none) but never both at the same time.
        if cfg.header_row is not None and cfg.periods_row is not None:
            # Detect user explicitly provided both values (even if identical)
            raise ValueError(
                "Provide either header_row **or** periods_row, not both. "
                "Set header_row=None to use periods_row as header, or vice-versa."
            )

        return cfg


class FmpReaderConfig(BaseReaderConfig):
    """Financial Modeling Prep API reader options."""

    # Source ticker symbol
    source: str = Field(..., description="Ticker symbol e.g., 'AAPL'")

    statement_type: Literal["income_statement", "balance_sheet", "cash_flow"] = Field(
        ..., description="Type of financial statement to fetch."
    )
    period_type: Literal["FY", "QTR"] = Field("FY", description="Period type: 'FY' or 'QTR'.")
    limit: int = Field(5, description="Number of periods to fetch.")
    # Caller value → env var → cfg("api.fmp_api_key")
    api_key: str | None = Field(
        default=None,
        description="Financial Modeling Prep API key.",
    )
    mapping_config: MappingConfig | None = Field(
        None, description="Optional configuration for mapping source item names."
    )

    @field_validator("api_key", mode="before")
    @classmethod
    def load_api_key_env(cls, value: str | None) -> str | None:
        """Load API key by cascading through explicit param, env var, and global config."""
        if value:
            return value
        import os

        return os.getenv("FMP_API_KEY") or cfg("api.fmp_api_key", None)

    @model_validator(mode="after")  # type: ignore[arg-type]
    @classmethod
    def check_api_key(cls, cfg: FmpReaderConfig) -> FmpReaderConfig:
        """Ensure an API key is provided after attempting to load from all sources."""
        if not cfg.api_key:
            raise ValueError("api_key is required (env var FMP_API_KEY or param)")
        return cfg


# --- New Reader Configs for DataFrame and Dict readers ---


class DataFrameReaderConfig(BaseReaderConfig):
    """Configuration for DataFrameReader.

    No additional reader-specific options are required at the moment because
    the reader consumes an in-memory :class:`pandas.DataFrame` supplied to
    :py:meth:`DataFrameReader.read`.  The `source` field therefore serves only
    to preserve a consistent registry-initialisation contract.
    """

    # Pydantic must allow arbitrary "pd.DataFrame" type
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    # Use forward reference to avoid hard dependency at import time
    source: pd.DataFrame = Field(..., description="In-memory pandas DataFrame source")
    format_type: Literal["dataframe"] = "dataframe"

    # Runtime override for read-time periods selection
    periods: list[str] | None = Field(
        None,
        description="Optional list of periods (columns) to include when reading a DataFrame.",
    )


class DictReaderConfig(BaseReaderConfig):
    """Configuration for DictReader.

    Mirrors :class:`DataFrameReaderConfig` - no custom options yet.  The
    placeholder keeps the IO registry symmetric and future-proof.
    """

    source: dict[str, dict[str, float]] = Field(..., description="In-memory dictionary source")
    format_type: Literal["dict"] = "dict"

    # Runtime override for read-time periods selection
    periods: list[str] | None = Field(None, description="Optional list of periods to include when reading a dict.")


# --- Writer-side Pydantic configuration models ---
class BaseWriterConfig(BaseModel):
    """Base configuration for IO writers."""

    target: Any | None = Field(
        None,
        description="Destination for write operation (path, buffer, in-memory object).",
    )
    format_type: Literal[
        "excel",
        "dataframe",
        "dict",
        "markdown",
        "graph_definition_dict",
    ] = Field(..., description="Writer format identifier.")

    model_config = ConfigDict(extra="forbid", frozen=True)


class ExcelWriterConfig(BaseWriterConfig):
    """Excel writer options."""

    # Worksheet name defaults to cfg value if not provided via config or call
    sheet_name: str = Field(
        default_factory=lambda: cfg("io.default_excel_sheet"),
        description="Worksheet name to use when exporting.",
    )

    format_type: Literal["excel"] = "excel"

    recalculate: bool = Field(True, description="Whether to recalculate graph before export.")
    include_nodes: list[str] | None = Field(None, description="Optional list of node names to include in export.")
    excel_writer_kwargs: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional kwargs for pandas.DataFrame.to_excel.",
    )

    # Output file path (optional when provided at write-time)
    target: str | None = Field(
        None,
        description="Path to the output Excel file. If None, must be supplied when calling write().",
    )


class DataFrameWriterConfig(BaseWriterConfig):
    """DataFrame writer options."""

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    target: pd.DataFrame | None = Field(None, description="Optional DataFrame target override (rare).")
    recalculate: bool = Field(True, description="Whether to recalculate graph before export.")
    include_nodes: list[str] | None = Field(None, description="Optional list of node names to include in export.")


class DictWriterConfig(BaseWriterConfig):
    """Dict writer has no additional options."""

    target: dict[str, dict[str, float]] | None = Field(
        None, description="Optional dict target (ignored by DictWriter)."
    )


class MarkdownWriterConfig(BaseWriterConfig):
    """Markdown writer options.

    The writer is configured via an in-memory mapping of statement IDs to
    configuration dictionaries.
    """

    # In-memory configs only.
    raw_configs: dict[str, dict[str, Any]] | None = Field(
        None,
        description=(
            "Mapping of statement IDs to configuration dictionaries.  This allows "
            "fully in-memory operation without relying on the filesystem."
        ),
    )

    historical_periods: list[str] | None = Field(None, description="List of historical period names.")
    forecast_periods: list[str] | None = Field(None, description="List of forecast period names.")
    adjustment_filter: AdjustmentFilterInput | None = Field(None, description="Adjustment filter to apply.")
    forecast_configs: dict[str, Any] | None = Field(
        None,
        description="Dictionary mapping node IDs to forecast configurations for notes.",
    )
    indent_spaces: int = Field(4, description="Number of spaces per indentation level.")
    target: str | None = Field(None, description="Optional target path (ignored by MarkdownWriter).")

    # Allow extra write() kwargs like 'statement_structure' to pass through without error
    model_config = ConfigDict(extra="ignore", frozen=True)


# -----------------------------------------------------------------------------
# Graph Definition (dict) Reader/Writer Configs - minimal requirements
# -----------------------------------------------------------------------------


class GraphDefinitionReaderConfig(BaseReaderConfig):
    """Configuration for GraphDefinitionReader.

    The *source* is expected to be an in-memory dictionary containing the keys
    ``periods`` and ``nodes`` (and optionally ``adjustments``).  No additional
    reader-specific options are supported.
    """

    source: Any = Field(..., description="Graph definition dictionary to import.")
    format_type: Literal["graph_definition_dict"] = "graph_definition_dict"


class GraphDefinitionWriterConfig(BaseWriterConfig):
    """Configuration for GraphDefinitionWriter.

    The writer returns the graph definition dictionary directly; *target* is
    therefore optional and typically ignored.
    """

    target: Any | None = Field(
        None,
        description=(
            "Unused placeholder - GraphDefinitionWriter returns the definition "
            "dict instead of writing to an external target."
        ),
    )
    strict: bool = Field(
        True,
        description=(
            "If True (default) the writer aborts on the first node that fails "
            "to serialise; if False it skips problematic nodes and continues."
        ),
    )
    format_type: Literal["graph_definition_dict"] = "graph_definition_dict"
