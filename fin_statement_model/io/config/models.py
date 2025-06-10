"""Pydantic models for IO reader and writer configuration.

This module provides declarative schemas for validating configuration passed to IO readers.
"""

from __future__ import annotations

from typing import Optional, Literal, Any, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

from fin_statement_model.config.helpers import cfg
from fin_statement_model.core.adjustments.models import (
    AdjustmentFilterInput,
)


# Define MappingConfig locally to avoid circular import
MappingConfig = Union[dict[str, str], dict[Optional[str], dict[str, str]]]


class BaseReaderConfig(BaseModel):
    """Base configuration for IO readers."""

    source: Any = Field(
        ..., description="URI or path to data source (file path, ticker, etc.)"
    )
    format_type: Literal["csv", "excel", "dataframe", "dict", "fmp"] = Field(
        ..., description="Type of reader (csv, excel, dataframe, dict, fmp)."
    )

    model_config = ConfigDict(extra="forbid", frozen=True)


class CsvReaderConfig(BaseReaderConfig):
    """CSV reader options."""

    # Falls back to cfg("io.default_csv_delimiter") when not supplied
    delimiter: str = Field(
        default_factory=lambda: cfg("io.default_csv_delimiter"),
        description="Field delimiter for CSV files.",
    )
    header_row: int = Field(
        1, description="Row number containing column names (1-indexed)."
    )
    index_col: Optional[int] = Field(
        None, description="1-indexed column for row labels."
    )
    mapping_config: Optional[MappingConfig] = Field(
        None, description="Optional configuration for mapping source item names."
    )

    # Runtime override options: these will override config defaults when provided at read-time
    statement_type: Optional[
        Literal["income_statement", "balance_sheet", "cash_flow"]
    ] = Field(
        None,
        description="Type of statement ('income_statement', 'balance_sheet', 'cash_flow') to select mapping scope.",
    )
    item_col: Optional[str] = Field(
        None, description="Name of the column containing item identifiers."
    )
    period_col: Optional[str] = Field(
        None, description="Name of the column containing period identifiers."
    )
    value_col: Optional[str] = Field(
        None, description="Name of the column containing numeric values."
    )
    pandas_read_csv_kwargs: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional kwargs for pandas.read_csv, overriding config defaults.",
    )

    @model_validator(mode="after")  # type: ignore[arg-type]
    def check_header_row(cls, cfg: CsvReaderConfig) -> CsvReaderConfig:
        """Ensure header_row is at least 1."""
        if cfg.header_row < 1:
            raise ValueError("header_row must be >= 1")
        return cfg


class ExcelReaderConfig(BaseReaderConfig):
    """Excel reader options."""

    # Uses cfg("io.default_excel_sheet") unless caller overrides
    sheet_name: Optional[str] = Field(
        default_factory=lambda: cfg("io.default_excel_sheet"),
        description="Worksheet name or index.",
    )
    items_col: int = Field(1, description="1-indexed column where item names reside.")
    periods_row: int = Field(1, description="1-indexed row where periods reside.")
    mapping_config: Optional[MappingConfig] = Field(
        None, description="Optional configuration for mapping source item names."
    )

    statement_type: Optional[
        Literal["income_statement", "balance_sheet", "cash_flow"]
    ] = Field(
        None,
        description="Type of statement ('income_statement', 'balance_sheet', 'cash_flow'). Used to select a mapping scope.",
    )
    header_row: Optional[int] = Field(
        None, description="1-indexed row for pandas header reading."
    )
    nrows: Optional[int] = Field(
        None, description="Number of rows to read from the sheet."
    )
    skiprows: Optional[int] = Field(
        None, description="Number of rows to skip at the beginning."
    )

    @model_validator(mode="after")  # type: ignore[arg-type]
    def check_indices(cls, cfg: ExcelReaderConfig) -> ExcelReaderConfig:
        """Ensure items_col and periods_row are at least 1."""
        if cfg.items_col < 1 or cfg.periods_row < 1:
            raise ValueError("items_col and periods_row must be >= 1")
        return cfg


class FmpReaderConfig(BaseReaderConfig):
    """Financial Modeling Prep API reader options."""

    statement_type: Literal["income_statement", "balance_sheet", "cash_flow"] = Field(
        ..., description="Type of financial statement to fetch."
    )
    period_type: Literal["FY", "QTR"] = Field(
        "FY", description="Period type: 'FY' or 'QTR'."
    )
    limit: int = Field(5, description="Number of periods to fetch.")
    # Caller value → env var → cfg("api.fmp_api_key")
    api_key: Optional[str] = Field(
        default=None,
        description="Financial Modeling Prep API key.",
    )
    mapping_config: Optional[MappingConfig] = Field(
        None, description="Optional configuration for mapping source item names."
    )

    @field_validator("api_key", mode="before")
    def load_api_key_env(cls, value: Optional[str]) -> Optional[str]:
        """Cascade lookup: explicit param → env → global config."""
        if value:
            return value
        import os

        return os.getenv("FMP_API_KEY") or cfg("api.fmp_api_key", None)

    @model_validator(mode="after")  # type: ignore[arg-type]
    def check_api_key(cls, cfg: FmpReaderConfig) -> FmpReaderConfig:
        """Ensure an API key is provided."""
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

    source: Any = Field(..., description="In-memory pandas DataFrame source")
    format_type: Literal["dataframe"] = "dataframe"

    # Runtime override for read-time periods selection
    periods: Optional[list[str]] = Field(
        None,
        description="Optional list of periods (columns) to include when reading a DataFrame.",
    )


class DictReaderConfig(BaseReaderConfig):
    """Configuration for DictReader.

    Mirrors :class:`DataFrameReaderConfig` - no custom options yet.  The
    placeholder keeps the IO registry symmetric and future-proof.
    """

    source: dict[str, dict[str, float]] = Field(
        ..., description="In-memory dictionary source"
    )
    format_type: Literal["dict"] = "dict"

    # Runtime override for read-time periods selection
    periods: Optional[list[str]] = Field(
        None, description="Optional list of periods to include when reading a dict."
    )


# --- Writer-side Pydantic configuration models ---
class BaseWriterConfig(BaseModel):
    """Base configuration for IO writers."""

    target: Optional[str] = Field(
        None,
        description="URI or path to data target (file path, in-memory target, etc.)",
    )
    format_type: Literal["excel", "dataframe", "dict", "markdown"] = Field(
        ..., description="Type of writer (excel, dataframe, dict, markdown)."
    )

    model_config = ConfigDict(extra="forbid", frozen=True)


class ExcelWriterConfig(BaseWriterConfig):
    """Excel writer options."""

    # Default comes from cfg("io.default_excel_sheet")
    sheet_name: str = Field(
        default_factory=lambda: cfg("io.default_excel_sheet"),
        description="Name of the sheet to write to.",
    )
    recalculate: bool = Field(
        True, description="Whether to recalculate graph before export."
    )
    include_nodes: Optional[list[str]] = Field(
        None, description="Optional list of node names to include in export."
    )
    excel_writer_kwargs: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional kwargs for pandas.DataFrame.to_excel.",
    )


class DataFrameWriterConfig(BaseWriterConfig):
    """DataFrame writer options."""

    target: Optional[str] = Field(
        None, description="Optional target path (ignored by DataFrameWriter)."
    )
    recalculate: bool = Field(
        True, description="Whether to recalculate graph before export."
    )
    include_nodes: Optional[list[str]] = Field(
        None, description="Optional list of node names to include in export."
    )


class DictWriterConfig(BaseWriterConfig):
    """Dict writer has no additional options."""

    target: Optional[str] = Field(
        None, description="Optional target (ignored by DictWriter)."
    )


class MarkdownWriterConfig(BaseWriterConfig):
    """Markdown writer options.

    The writer can be configured in multiple ways:

    1. ``statement_config_path`` – Path to a YAML file containing the statement
       definition.  This mirrors historical behaviour where configurations were
       stored on disk.
    2. ``raw_configs`` – An *in-memory* mapping of statement IDs to their
       configuration dictionaries.  This is the preferred mechanism in the new
       API and aligns with ``create_statement_dataframe`` and other
       in-memory workflows.

    Only **one** of these two options is required.  If both are supplied the
    explicit ``raw_configs`` takes precedence.
    """

    # Either a file-based config …
    statement_config_path: Optional[str] = Field(
        None, description="Path to the statement definition YAML file."
    )

    # … or in-memory configs.
    raw_configs: Optional[dict[str, dict[str, Any]]] = Field(
        None,
        description=(
            "Mapping of statement IDs to configuration dictionaries.  This allows "
            "fully in-memory operation without relying on the filesystem."
        ),
    )

    historical_periods: Optional[list[str]] = Field(
        None, description="List of historical period names."
    )
    forecast_periods: Optional[list[str]] = Field(
        None, description="List of forecast period names."
    )
    adjustment_filter: Optional[AdjustmentFilterInput] = Field(
        None, description="Adjustment filter to apply."
    )
    forecast_configs: Optional[dict[str, Any]] = Field(
        None,
        description="Dictionary mapping node IDs to forecast configurations for notes.",
    )
    indent_spaces: int = Field(4, description="Number of spaces per indentation level.")
    target: Optional[str] = Field(
        None, description="Optional target path (ignored by MarkdownWriter)."
    )

    # Allow extra write() kwargs like 'statement_structure' to pass through without error
    model_config = ConfigDict(extra="ignore", frozen=True)
