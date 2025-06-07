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
from .introspection import (
    generate_env_mappings,
    validate_env_mappings,
    get_field_type_info,
)
from .param_mapping import (
    ParamMapper,
    get_class_param_mappings,
    merge_param_mappings,
)
from .discovery import (
    list_all_config_paths,
    generate_env_var_documentation,
    generate_param_mapping_documentation,
    get_config_field_info,
    find_config_paths_by_type,
    validate_config_completeness,
    generate_config_summary,
)

__all__ = [
    # Config models
    "APIConfig",
    "Config",
    "ConfigManager",
    "ConfigurationAccessError",
    "DisplayConfig",
    "ForecastingConfig",
    "IOConfig",
    "LoggingConfig",
    # Parameter mapping utilities
    "ParamMapper",
    "PreprocessingConfig",
    "api_retry_count",
    "api_timeout",
    # Utils
    "cfg",
    "cfg_or_param",
    "config_aware_init",
    # Convenience functions
    "default_csv_delimiter",
    "default_excel_sheet",
    "default_growth_rate",
    "default_periods",
    "find_config_paths_by_type",
    "generate_config_summary",
    # Introspection utilities
    "generate_env_mappings",
    "generate_env_var_documentation",
    "generate_param_mapping_documentation",
    "get_class_param_mappings",
    # Manager functions
    "get_config",
    "get_config_field_info",
    "get_field_type_info",
    "get_typed_config",
    # Discovery utilities
    "list_all_config_paths",
    "list_config_paths",
    "merge_param_mappings",
    "migrate_to_config",
    "reset_config",
    "update_config",
    # Decorators
    "uses_config_default",
    "validate_config_completeness",
    "validate_env_mappings",
    "warn_hardcoded_default",
]
