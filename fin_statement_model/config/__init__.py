"""Centralized configuration management for fin_statement_model.

This module provides a unified interface for managing all library configurations,
including defaults, user overrides, and environment variables.

Example:
    >>> from fin_statement_model.config import get_config, update_config
    >>>
    >>> # Get current configuration
    >>> config = get_config()
    >>> print(config.logging.level)
    >>>
    >>> # Update configuration
    >>> update_config({
    ...     'forecasting': {
    ...         'default_method': 'historical_growth',
    ...         'default_periods': 5
    ...     }
    ... })
"""

from .manager import ConfigManager, get_config, update_config, reset_config
from .models import (
    Config,
    LoggingConfig,
    IOConfig,
    ForecastingConfig,
    PreprocessingConfig,
    DisplayConfig,
    APIConfig,
)
from .utils import (
    cfg,
    cfg_or_param,
    get_typed_config,
    list_config_paths,
    ConfigurationAccessError,
    # Convenience functions
    default_csv_delimiter,
    default_excel_sheet,
    default_periods,
    default_growth_rate,
    api_timeout,
    api_retry_count,
)
from .decorators import (
    uses_config_default,
    migrate_to_config,
    config_aware_init,
    warn_hardcoded_default,
)

__all__ = [
    # Config models
    "APIConfig",
    "Config",
    "ConfigManager",
    "DisplayConfig",
    "ForecastingConfig",
    "IOConfig",
    "LoggingConfig",
    "PreprocessingConfig",
    # Manager functions
    "get_config",
    "reset_config",
    "update_config",
    # Utils
    "cfg",
    "cfg_or_param",
    "get_typed_config",
    "list_config_paths",
    "ConfigurationAccessError",
    # Convenience functions
    "default_csv_delimiter",
    "default_excel_sheet", 
    "default_periods",
    "default_growth_rate",
    "api_timeout",
    "api_retry_count",
    # Decorators
    "uses_config_default",
    "migrate_to_config",
    "config_aware_init",
    "warn_hardcoded_default",
]
