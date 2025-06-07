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

from .models import Config
from .manager import get_config, update_config, reset_config
from .helpers import cfg, cfg_or_param, get_typed_config

__all__ = [
    "Config",
    "cfg",
    "cfg_or_param",
    "get_config",
    "get_typed_config",
    "reset_config",
    "update_config",
]
