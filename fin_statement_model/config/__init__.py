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
]
