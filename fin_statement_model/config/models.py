"""Configuration models for fin_statement_model.

This module defines the configuration schema using Pydantic models,
providing validation and type safety for all configuration options.
"""

from typing import Optional, Literal, Any
from pathlib import Path
from pydantic import BaseModel, Field, field_validator, ConfigDict


class LoggingConfig(BaseModel):
    """Logging configuration settings."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        "WARNING", description="Default logging level for the library"
    )
    format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format string",
    )
    detailed: bool = Field(
        False, description="Enable detailed logging with file and line numbers"
    )
    log_file_path: Optional[Path] = Field(
        None,
        description=(
            "If provided, logs are written to this path (rotating handler). "
            "If None, file logging is disabled."
        ),
    )

    model_config = ConfigDict(extra="forbid")


class IOConfig(BaseModel):
    """Input/Output configuration settings."""

    default_excel_sheet: str = Field(
        "Sheet1", description="Default sheet name for Excel operations"
    )
    default_csv_delimiter: str = Field(
        ",", description="Default delimiter for CSV files"
    )
    auto_create_output_dirs: bool = Field(
        True, description="Automatically create output directories if they don't exist"
    )
    validate_on_read: bool = Field(True, description="Validate data on read operations")
    default_mapping_configs_dir: Optional[Path] = Field(
        None, description="Directory containing custom mapping configuration files"
    )
    auto_standardize_columns: bool = Field(
        True, description="Automatically standardize column names when reading data"
    )
    skip_invalid_rows: bool = Field(
        False, description="Skip rows with invalid data instead of raising errors"
    )
    strict_validation: bool = Field(
        False, description="Use strict validation when reading data"
    )

    model_config = ConfigDict(extra="forbid")


class ForecastingConfig(BaseModel):
    """Forecasting configuration settings."""

    default_method: Literal[
        "simple", "historical_growth", "curve", "statistical", "ml"
    ] = Field("simple", description="Default forecasting method")
    default_periods: int = Field(5, description="Default number of periods to forecast")
    default_growth_rate: float = Field(
        0.0, description="Default growth rate for simple forecasting"
    )
    min_historical_periods: int = Field(
        3, description="Minimum historical periods required for forecasting"
    )
    allow_negative_forecasts: bool = Field(
        True, description="Allow negative values in forecasts"
    )

    @field_validator("default_periods")
    def validate_periods(cls, v: int) -> int:
        """Ensure periods is positive."""
        if v <= 0:
            raise ValueError("default_periods must be positive")
        return v

    model_config = ConfigDict(extra="forbid")


class PreprocessingConfig(BaseModel):
    """Data preprocessing configuration settings."""

    auto_clean_data: bool = Field(
        True, description="Automatically clean data on import"
    )
    fill_missing_with_zero: bool = Field(
        False, description="Fill missing values with zero instead of None"
    )
    remove_empty_periods: bool = Field(
        True, description="Remove periods with all empty values"
    )
    standardize_period_format: bool = Field(
        True, description="Standardize period names to consistent format"
    )
    default_normalization_type: Optional[
        Literal["percent_of", "minmax", "standard", "scale_by"]
    ] = Field(None, description="Default normalization method")

    model_config = ConfigDict(extra="forbid")


class DisplayConfig(BaseModel):
    """Display and formatting configuration settings."""

    default_number_format: str = Field(
        ",.2f", description="Default number format string"
    )
    default_currency_format: str = Field(
        ",.2f", description="Default currency format string"
    )
    default_percentage_format: str = Field(
        ".1%", description="Default percentage format string"
    )
    hide_zero_rows: bool = Field(
        False, description="Hide rows where all values are zero"
    )
    contra_display_style: Literal["parentheses", "brackets", "negative"] = Field(
        "parentheses", description="How to display contra items"
    )
    thousands_separator: str = Field(",", description="Thousands separator character")
    decimal_separator: str = Field(".", description="Decimal separator character")
    default_units: str = Field("USD", description="Default currency/units for display")
    scale_factor: float = Field(
        1.0, description="Default scale factor for display (e.g., 0.001 for thousands)"
    )

    # --- New advanced formatting options ---
    indent_character: str = Field(
        "  ", description="Indentation characters used for nested line items"
    )
    subtotal_style: str = Field(
        "bold", description="CSS/markup style keyword for subtotal rows"
    )
    total_style: str = Field(
        "bold", description="CSS/markup style keyword for total rows"
    )
    header_style: str = Field(
        "bold", description="CSS/markup style keyword for header cells"
    )
    contra_css_class: str = Field(
        "contra-item", description="Default CSS class name for contra items"
    )
    show_negative_sign: bool = Field(
        True,
        description="Whether to prefix negative numbers with a minus sign when not using parentheses",
    )

    @field_validator("scale_factor")
    def validate_scale_factor(cls, v: float) -> float:
        """Ensure scale factor is positive."""
        if v <= 0:
            raise ValueError("scale_factor must be positive")
        return v

    model_config = ConfigDict(extra="forbid")


class APIConfig(BaseModel):
    """API and external service configuration."""

    fmp_api_key: Optional[str] = Field(
        None, description="Financial Modeling Prep API key"
    )
    fmp_base_url: str = Field(
        "https://financialmodelingprep.com/api/v3", description="FMP API base URL"
    )
    api_timeout: int = Field(30, description="API request timeout in seconds")
    api_retry_count: int = Field(
        3, description="Number of retries for failed API requests"
    )
    cache_api_responses: bool = Field(
        True, description="Cache API responses to reduce API calls"
    )
    cache_ttl_hours: int = Field(24, description="Cache time-to-live in hours")

    @field_validator("api_timeout", "api_retry_count", "cache_ttl_hours")
    def validate_positive(cls, v: int) -> int:
        """Ensure values are positive."""
        if v <= 0:
            raise ValueError("Value must be positive")
        return v

    model_config = ConfigDict(extra="forbid")


class MetricsConfig(BaseModel):
    """Metrics configuration settings."""

    custom_metrics_dir: Optional[Path] = Field(
        None, description="Directory containing custom metric definitions"
    )
    validate_metric_inputs: bool = Field(
        True, description="Validate metric inputs exist in graph"
    )
    auto_register_metrics: bool = Field(
        True, description="Automatically register metrics from definition files"
    )

    model_config = ConfigDict(extra="forbid")


class ValidationConfig(BaseModel):
    """Data validation configuration settings."""

    strict_mode: bool = Field(False, description="Enable strict validation mode")
    auto_standardize_names: bool = Field(
        True, description="Automatically standardize node names to canonical form"
    )
    warn_on_non_standard: bool = Field(
        True, description="Warn when using non-standard node names"
    )
    check_balance_sheet_balance: bool = Field(
        True, description="Validate that Assets = Liabilities + Equity"
    )
    balance_tolerance: float = Field(
        1.0, description="Maximum acceptable difference for balance sheet validation"
    )
    warn_on_negative_assets: bool = Field(
        True, description="Warn when asset values are negative"
    )
    validate_sign_conventions: bool = Field(
        True, description="Validate that items follow expected sign conventions"
    )

    @field_validator("balance_tolerance")
    def validate_tolerance(cls, v: float) -> float:
        """Ensure tolerance is non-negative."""
        if v < 0:
            raise ValueError("balance_tolerance must be non-negative")
        return v

    model_config = ConfigDict(extra="forbid")


class Config(BaseModel):
    """Main configuration container for fin_statement_model."""

    # Sub-configurations
    logging: LoggingConfig = Field(
        default=LoggingConfig.model_validate({}), description="Logging configuration"
    )
    io: IOConfig = Field(
        default=IOConfig.model_validate({}), description="Input/Output configuration"
    )
    forecasting: ForecastingConfig = Field(
        default=ForecastingConfig.model_validate({}),
        description="Forecasting configuration",
    )
    preprocessing: PreprocessingConfig = Field(
        default=PreprocessingConfig.model_validate({}),
        description="Data preprocessing configuration",
    )
    display: DisplayConfig = Field(
        default=DisplayConfig.model_validate({}),
        description="Display and formatting configuration",
    )
    api: APIConfig = Field(
        default=APIConfig.model_validate({}),
        description="API and external service configuration",
    )
    metrics: MetricsConfig = Field(
        default=MetricsConfig.model_validate({}), description="Metrics configuration"
    )
    validation: ValidationConfig = Field(
        default=ValidationConfig.model_validate({}),
        description="Data validation configuration",
    )

    # Global settings
    project_name: str = Field(
        "fin_statement_model", description="Project name for identification"
    )
    config_file_path: Optional[Path] = Field(
        None, description="Path to user configuration file"
    )
    auto_save_config: bool = Field(
        False, description="Automatically save configuration changes to file"
    )

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump(exclude_none=True)

    def to_yaml(self) -> str:
        """Convert configuration to YAML string."""
        import yaml

        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create configuration from dictionary."""
        return cls(**data)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "Config":
        """Create configuration from YAML string."""
        import yaml

        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)

    @classmethod
    def from_file(cls, path: Path) -> "Config":
        """Load configuration from file."""
        if path.suffix in [".yaml", ".yml"]:
            return cls.from_yaml(path.read_text())
        elif path.suffix == ".json":
            import json

            return cls.from_dict(json.loads(path.read_text()))
        else:
            raise ValueError(f"Unsupported config file format: {path.suffix}")
