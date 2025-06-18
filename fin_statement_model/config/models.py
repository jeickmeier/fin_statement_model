"""Define configuration schemas for fin_statement_model.

This module provides Pydantic models to validate and type-check the
application's configuration settings, including logging, I/O, forecasting,
preprocessing, display, API, metrics, validation, and statement options.

Each sub-config is a Pydantic model with field-level validation and
descriptions. The root `Config` model aggregates all sub-configurations and
provides serialization helpers.

Examples:
    >>> from fin_statement_model.config.models import Config
    >>> config = Config()
    >>> config.logging.level
    'WARNING'
    >>> config.display.flags.include_notes_column
    False
    >>> config.to_dict()['logging']['level']
    'WARNING'
    >>> yaml_str = config.to_yaml()
    >>> isinstance(yaml_str, str)
    True
    >>> loaded = Config.from_yaml(yaml_str)
    >>> loaded.logging.level == config.logging.level
    True
"""

from typing import Optional, Literal, Any, Union
from pathlib import Path
from pydantic import BaseModel, Field, field_validator, ConfigDict
from fin_statement_model.statements.configs.models import AdjustmentFilterSpec
from fin_statement_model.preprocessing.config import (
    StatementFormattingConfig,
    TransformationType,
)


class LoggingConfig(BaseModel):
    """Settings for library logging.

    Attributes:
        level (Literal): Default logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR', or 'CRITICAL').
        format (str): Log message format string.
        detailed (bool): Enable detailed logging with file and line numbers.
        log_file_path (Optional[Path]): Path for rotating log files; None disables file logging.

    Example:
        >>> LoggingConfig(level='DEBUG').level
        'DEBUG'
    """

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
    """Configuration for input/output operations.

    Attributes:
        default_excel_sheet (str): Default sheet name for Excel operations.
        default_csv_delimiter (str): Default delimiter for CSV files.
        auto_create_output_dirs (bool): Automatically create output directories.
        validate_on_read (bool): Validate data when reading.
        default_mapping_configs_dir (Optional[Path]): Directory for mapping configs.
        auto_standardize_columns (bool): Standardize column names on read.
        skip_invalid_rows (bool): Skip rows with invalid data.
        strict_validation (bool): Enforce strict data validation on read.

    Example:
        >>> IOConfig(default_csv_delimiter=';').default_csv_delimiter
        ';'
    """

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
    """Settings for forecasting behavior.

    Attributes:
        default_method (Literal): Default forecasting method ('simple', 'historical_growth', 'curve',
            'statistical', or 'ml').
        default_periods (int): Default number of periods to forecast.
        default_growth_rate (float): Default growth rate for simple forecasting.
        min_historical_periods (int): Minimum historical periods required.
        allow_negative_forecasts (bool): Allow negative forecast values.
        add_missing_periods (bool): Add missing forecast periods.
        default_bad_forecast_value (float): Value for invalid forecasts.
        continue_on_error (bool): Continue forecasting other nodes if one fails.
        historical_growth_aggregation (Literal['mean', 'median']): Aggregation method.
        random_seed (Optional[int]): Seed for statistical forecasting.
        base_period_strategy (Literal): Strategy for selecting base period.

    Example:
        >>> ForecastingConfig(default_periods=10).default_periods
        10
    """

    default_method: Literal[
        "simple", "average_growth", "curve", "statistical", "ml"
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
    add_missing_periods: bool = Field(
        True, description="Whether to add missing forecast periods to the graph"
    )
    default_bad_forecast_value: float = Field(
        0.0, description="Default value to use for NaN, Inf, or error forecasts"
    )
    continue_on_error: bool = Field(
        True,
        description="Whether to continue forecasting other nodes if one node fails",
    )
    historical_growth_aggregation: Literal["mean", "median"] = Field(
        "mean",
        description="Aggregation method for historical growth rate: 'mean' or 'median'",
    )
    random_seed: Optional[int] = Field(
        None,
        description="Random seed for statistical forecasting to ensure reproducible results",
    )
    base_period_strategy: Literal[
        "preferred_then_most_recent", "most_recent", "last_historical"
    ] = Field(
        "preferred_then_most_recent",
        description=(
            "Strategy for selecting base period: 'preferred_then_most_recent' (default), "
            "'most_recent' (ignore preferred, pick most recent with data), or "
            "'last_historical' (always use last historical period)."
        ),
    )

    @field_validator("default_periods")
    def validate_periods(cls, v: int) -> int:
        """Validate that `default_periods` is positive.

        Args:
            v (int): Number of periods.

        Returns:
            The validated period count.

        Raises:
            ValueError: If `v` is not positive.

        Example:
            >>> ForecastingConfig.validate_periods(5)
            5
        """
        if v <= 0:
            raise ValueError("default_periods must be positive")
        return v

    model_config = ConfigDict(extra="forbid")


class PreprocessingConfig(BaseModel):
    """Settings for data preprocessing operations.

    Attributes:
        auto_clean_data (bool): Automatically clean data on import.
        fill_missing_with_zero (bool): Fill missing values with zero.
        remove_empty_periods (bool): Remove periods with no data.
        standardize_period_format (bool): Standardize period name formats.
        default_normalization_type (Optional[Literal[...] ): Default normalization method.
        default_transformation_type (TransformationType): Default time series transformation.
        default_time_series_periods (int): Number of periods for transformations.
        default_time_series_window_size (int): Window size for transformations.
        default_conversion_aggregation (str): Aggregation method for period conversion.
        statement_formatting (StatementFormattingConfig): Formatting settings.

    Example:
        >>> PreprocessingConfig(auto_clean_data=False).auto_clean_data
        False
    """

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
    default_transformation_type: TransformationType = Field(
        TransformationType.GROWTH_RATE,
        description="Default time series transformation type",
    )
    default_time_series_periods: int = Field(
        1, description="Default number of periods for time series transformations"
    )
    default_time_series_window_size: int = Field(
        3, description="Default window size for time series transformations"
    )
    default_conversion_aggregation: str = Field(
        "sum", description="Default aggregation method for period conversion"
    )
    statement_formatting: StatementFormattingConfig = Field(
        default=StatementFormattingConfig.model_validate({}),
        description="Default statement formatting configuration for preprocessing",
    )

    model_config = ConfigDict(extra="forbid")


# -----------------------------------------------------------------------------
# Display sub-config models


class DisplayFlags(BaseModel):
    """Boolean feature flags for statement display.

    These granular switches control optional features during statement formatting.
    Grouping them in a dedicated model keeps `DisplayConfig` manageable while
    still exposing properties for ergonomic access (e.g., `cfg.display.include_empty_items`).

    Example:
        >>> DisplayFlags(include_notes_column=True).include_notes_column
        True
    """

    apply_sign_conventions: bool = Field(
        True, description="Whether to apply sign conventions by default"
    )
    include_empty_items: bool = Field(
        False, description="Whether to include items with no data by default"
    )
    include_metadata_cols: bool = Field(
        False, description="Whether to include metadata columns by default"
    )
    add_is_adjusted_column: bool = Field(
        False, description="Whether to add an 'is_adjusted' column by default"
    )
    include_units_column: bool = Field(
        False, description="Whether to include units column by default"
    )
    include_css_classes: bool = Field(
        False, description="Whether to include CSS class column by default"
    )
    include_notes_column: bool = Field(
        False, description="Whether to include notes column by default"
    )
    apply_item_scaling: bool = Field(
        True, description="Whether to apply item-specific scaling by default"
    )
    apply_item_formatting: bool = Field(
        True, description="Whether to apply item-specific formatting by default"
    )
    apply_contra_formatting: bool = Field(
        True, description="Whether to apply contra-specific formatting by default"
    )
    add_contra_indicator_column: bool = Field(
        False, description="Whether to add a contra indicator column by default"
    )

    model_config = ConfigDict(extra="forbid")


# pylint: disable=too-many-public-methods
class DisplayConfig(BaseModel):
    """Settings for formatting and displaying statement outputs.

    Attributes:
        default_number_format (str): Format string for numbers.
        default_currency_format (str): Format string for currency.
        default_percentage_format (str): Format string for percentages.
        hide_zero_rows (bool): Hide rows with all zero values.
        contra_display_style (Literal['parentheses', 'brackets','negative']): Style for contra items.
        thousands_separator (str): Character for thousands separator.
        decimal_separator (str): Character for decimal separator.
        default_units (str): Default currency or unit label.
        scale_factor (float): Scale factor applied to values.
        indent_character (str): Characters used for indentation.
        subtotal_style (str): Style keyword for subtotal rows.
        total_style (str): Style keyword for total rows.
        header_style (str): Style keyword for headers.
        contra_css_class (str): CSS class for contra items.
        show_negative_sign (bool): Show minus sign instead of parentheses.
        flags (DisplayFlags): Grouped boolean feature flags.

    Example:
        >>> DisplayConfig(default_number_format='.1%').default_number_format
        '.1%'
    """

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
    flags: DisplayFlags = Field(
        default_factory=DisplayFlags,
        description="Grouped boolean feature flags controlling optional display behaviour",
    )

    @field_validator("scale_factor")
    def validate_scale_factor(cls, v: float) -> float:
        """Ensure scale factor is positive.

        Args:
            v: The scale factor.
        Returns:
            The validated scale factor.
        Raises:
            ValueError: If scale factor is not positive.
        Example:
            >>> DisplayConfig.validate_scale_factor(1.0)
            1.0
        """
        if v <= 0:
            raise ValueError("scale_factor must be positive")
        return v

    model_config = ConfigDict(extra="forbid")

    def __getattr__(self, item: str) -> Any:
        """Delegate unknown attribute access to `flags` for convenience.

        This maintains compatibility with existing code that referenced
        attributes such as `config.display.include_empty_items` before the
        flags were nested.

        Args:
            item: The attribute name.
        Returns:
            The value from flags if present.
        Raises:
            AttributeError: If the attribute is not found.
        Example:
            >>> dc = DisplayConfig()
            >>> dc.include_empty_items == dc.flags.include_empty_items
            True
        """
        if item in self.flags.__fields__:
            return getattr(self.flags, item)
        raise AttributeError(item)


class APIConfig(BaseModel):
    """Settings for external API integrations.

    Attributes:
        fmp_api_key (Optional[str]): Financial Modeling Prep API key.
        fmp_base_url (str): Base URL for FMP API.
        api_timeout (int): HTTP request timeout in seconds.
        api_retry_count (int): Number of retries for failed requests.
        cache_api_responses (bool): Cache API responses to reduce calls.
        cache_ttl_hours (int): Time-to-live for cache entries in hours.

    Example:
        >>> APIConfig(api_timeout=60).api_timeout
        60
    """

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
        """Ensure values are positive.

        Args:
            v: The value to check.
        Returns:
            The validated value.
        Raises:
            ValueError: If value is not positive.
        Example:
            >>> APIConfig.validate_positive(10)
            10
        """
        if v <= 0:
            raise ValueError("Value must be positive")
        return v

    model_config = ConfigDict(extra="forbid")


class MetricsConfig(BaseModel):
    """Settings for metric registry behavior.

    Attributes:
        custom_metrics_dir (Optional[Path]): Directory for custom metric definitions.
        validate_metric_inputs (bool): Check that metric input nodes exist.
        auto_register_metrics (bool): Auto-register metrics from definition files.

    Example:
        >>> MetricsConfig(validate_metric_inputs=False).validate_metric_inputs
        False
    """

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
    """Settings for data validation within the graph.

    Attributes:
        strict_mode (bool): Enable strict validation mode.
        auto_standardize_names (bool): Standardize node names to canonical form.
        warn_on_non_standard (bool): Warn on non-standard names.
        check_balance_sheet_balance (bool): Validate Assets = Liabilities + Equity.
        balance_tolerance (float): Tolerance for balance sheet validation.
        warn_on_negative_assets (bool): Warn on negative asset values.
        validate_sign_conventions (bool): Enforce expected sign conventions.

    Example:
        >>> ValidationConfig(strict_mode=True).strict_mode
        True
    """

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
        """Ensure tolerance is non-negative.

        Args:
            v: The tolerance value.
        Returns:
            The validated tolerance.
        Raises:
            ValueError: If tolerance is negative.
        Example:
            >>> ValidationConfig.validate_tolerance(1.0)
            1.0
        """
        if v < 0:
            raise ValueError("balance_tolerance must be non-negative")
        return v

    model_config = ConfigDict(extra="forbid")


class StatementsConfig(BaseModel):
    """Settings for building and formatting financial statements.

    Attributes:
        default_adjustment_filter (Optional[Union[AdjustmentFilterSpec,list[str]]]): Default filter spec or tag list.
        enable_node_validation (bool): Enable node ID validation during building.
        node_validation_strict (bool): Treat validation failures as errors.

    Example:
        >>> StatementsConfig(enable_node_validation=True).enable_node_validation
        True
    """

    default_adjustment_filter: Optional[Union[AdjustmentFilterSpec, list[str]]] = Field(
        None,
        description="Default adjustment filter spec or list of tags to apply when building statements",
    )
    enable_node_validation: bool = Field(
        False,
        description="Whether to enable node ID validation during statement building by default",
    )
    node_validation_strict: bool = Field(
        False,
        description="Whether to treat node validation failures as errors (strict) by default",
    )

    model_config = ConfigDict(extra="forbid")


class Config(BaseModel):
    """Primary configuration container aggregating all sub-configurations.

    Attributes:
        logging (LoggingConfig): Logging configuration.
        io (IOConfig): I/O configuration.
        forecasting (ForecastingConfig): Forecasting settings.
        preprocessing (PreprocessingConfig): Data preprocessing settings.
        display (DisplayConfig): Display and formatting settings.
        api (APIConfig): API integration settings.
        metrics (MetricsConfig): Metrics registry settings.
        validation (ValidationConfig): Data validation settings.
        statements (StatementsConfig): Statement building settings.
        project_name (str): Identifier for the project.
        config_file_path (Optional[Path]): Path to the loaded config file.
        auto_save_config (bool): Auto-save overrides to file.

    Example:
        >>> from fin_statement_model.config.models import Config
        >>> config = Config()
        >>> config.to_dict()
        {...}
    """

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
    statements: StatementsConfig = Field(
        default=StatementsConfig.model_validate({}),
        description="Statement structure and formatting configuration",
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
        """Convert configuration to a JSON-serializable dict.

        Uses Pydantic's `model_dump` in JSON mode to convert complex types
        to primitive representations.

        Returns:
            A dict with no None values and JSON-compatible types.

        Example:
            >>> isinstance(Config().to_dict(), dict)
            True
        """
        return self.model_dump(exclude_none=True, mode="json")

    def to_yaml(self) -> str:
        """Serialize configuration to a YAML formatted string.

        Returns:
            YAML string representing the configuration.

        Example:
            >>> yaml_str = Config().to_yaml()
            >>> 'logging' in yaml_str
            True
        """
        import yaml

        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Instantiate Config from a dictionary.

        Args:
            data: Dictionary with configuration values.

        Returns:
            A validated Config instance.

        Example:
            >>> data = {'project_name': 'test'}
            >>> isinstance(Config.from_dict(data), Config)
            True
        """
        return cls(**data)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "Config":
        """Instantiate Config from a YAML-formatted string.

        Args:
            yaml_str: YAML string containing configuration.

        Returns:
            A validated Config instance.

        Example:
            >>> yaml_str = Config().to_yaml()
            >>> isinstance(Config.from_yaml(yaml_str), Config)
            True
        """
        import yaml

        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)

    @classmethod
    def from_file(cls, path: Path) -> "Config":
        """Load and parse configuration from a file.

        Args:
            path: Path to a .yaml, .yml, or .json configuration file.

        Returns:
            A validated Config instance.

        Raises:
            ValueError: If the file suffix is not supported.

        Example:
            >>> from pathlib import Path
            >>> config = Config.from_file(Path('config.yaml'))
            >>> isinstance(config, Config)
            True
        """
        if path.suffix in [".yaml", ".yml"]:
            return cls.from_yaml(path.read_text())
        elif path.suffix == ".json":
            import json

            return cls.from_dict(json.loads(path.read_text()))
        else:
            raise ValueError(f"Unsupported config file format: {path.suffix}")
