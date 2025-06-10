"""Provide centralized configuration management for fin_statement_model.

This sub-package offers a single entry-point for accessing and mutating the
library's configuration during runtime.  It re-exports the most commonly used
helpers so that callers can interact with the configuration layer without
needing to know the underlying module structure.

Examples:
    >>> from fin_statement_model.config import get_config, update_config

    # Retrieve the current configuration
    >>> cfg = get_config()
    >>> cfg.logging.level
    'WARNING'

    # Apply an in-memory override (takes effect immediately)
    >>> update_config({
    ...     'forecasting': {
    ...         'default_method': 'historical_growth',
    ...         'default_periods': 5,
    ...     }
    ... })
    >>> get_config().forecasting.default_method
    'historical_growth'
"""

from .helpers import cfg, cfg_or_param, get_typed_config

# Importing helpers first ensures that "cfg" is available early, avoiding
# circular import issues when other modules import fin_statement_model.config
# during the initialization of sub-packages (e.g., io.formats.api.fmp).

from .models import Config
from .manager import get_config, update_config, reset_config

__all__ = [
    "Config",
    "cfg",
    "cfg_or_param",
    "get_config",
    "get_typed_config",
    "reset_config",
    "update_config",
]
