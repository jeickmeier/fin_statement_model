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
    >>> config.to_dict()["logging"]["level"]
    'WARNING'
    >>> yaml_str = config.to_yaml()
    >>> isinstance(yaml_str, str)
    True
    >>> loaded = Config.from_yaml(yaml_str)
    >>> loaded.logging.level == config.logging.level
    True
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# Sub-config models are now defined in dedicated modules under
# ``fin_statement_model.config.subconfigs`` for better maintainability.
# Import them here so the public import path remains unchanged.
from fin_statement_model.config.subconfigs import (
    APIConfig,
    DisplayConfig,
    ForecastingConfig,
    IOConfig,
    LoggingConfig,
    MetricsConfig,
    PreprocessingConfig,
    ValidationConfig,
)

# Ensure sub-config models are fully initialized before we create default
# instances below; Pydantic may require an explicit rebuild when models are
# imported indirectly prior to utilisation.

for _model in (
    LoggingConfig,
    IOConfig,
    ForecastingConfig,
    PreprocessingConfig,
    DisplayConfig,
    APIConfig,
    MetricsConfig,
    ValidationConfig,
):
    _model.model_rebuild()


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
    logging: LoggingConfig = Field(default=LoggingConfig.model_validate({}), description="Logging configuration")
    io: IOConfig = Field(default=IOConfig.model_validate({}), description="Input/Output configuration")
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
    metrics: MetricsConfig = Field(default=MetricsConfig.model_validate({}), description="Metrics configuration")
    validation: ValidationConfig = Field(
        default=ValidationConfig.model_validate({}),
        description="Data validation configuration",
    )

    # Global settings
    project_name: str = Field("fin_statement_model", description="Project name for identification")
    config_file_path: Path | None = Field(None, description="Path to user configuration file")
    auto_save_config: bool = Field(False, description="Automatically save configuration changes to file")

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
            >>> "logging" in yaml_str
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
            >>> data = {"project_name": "test"}
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
            >>> config = Config.from_file(Path("config.yaml"))
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
