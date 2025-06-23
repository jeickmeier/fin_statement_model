"""Provide centralized configuration management for fin_statement_model.

This sub-package offers a single entry-point for accessing and mutating the
library's configuration during runtime.  It re-exports the most commonly used
helpers so that callers can interact with the configuration layer without
needing to know the underlying module structure.

Examples:
    >>> from fin_statement_model.config import get_config, update_config, cfg
    >>> cfg_obj = get_config()
    >>> cfg_obj.logging.level
    'WARNING'
    >>> update_config({'logging': {'level': 'DEBUG'}})
    >>> get_config().logging.level
    'DEBUG'
    >>> from fin_statement_model.config import cfg
    >>> cfg('logging.level')
    'DEBUG'
"""

from .access import cfg, cfg_or_param, ConfigurationAccessError

# Importing helpers first ensures that "cfg" is available early, avoiding
# circular import issues when other modules import fin_statement_model.config
# during the initialization of sub-packages (e.g., io.formats.api.fmp).

from .models import Config
from .store import get_config, update_config

__all__ = [
    "Config",
    "cfg",
    "cfg_or_param",
    "ConfigurationAccessError",
    "get_config",
    "update_config",
]

# ---
# Docstrings for re-exported symbols
