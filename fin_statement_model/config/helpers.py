"""Utility functions for accessing configuration values.

This module provides functions to retrieve application configuration
settings from the central config object, with optional type checking and
default values. It also includes utilities for parsing environment variable
strings into native Python types.

Examples:
    >>> from fin_statement_model.config.helpers import cfg, cfg_or_param, parse_env_value
    >>> cfg('logging.level')
    'WARNING'
    >>> cfg_or_param('logging.level', None)
    'WARNING'
    >>> parse_env_value('true')
    True
    >>> parse_env_value('42')
    42
    >>> parse_env_value('-3.14')
    -3.14
    >>> parse_env_value('foo')
    'foo'
"""

from __future__ import annotations
from typing import Any, TypeVar, overload
from collections.abc import Sequence
from fin_statement_model.core.errors import FinStatementModelError


class ConfigurationAccessError(FinStatementModelError):
    """Raised when there's an error accessing configuration values.

    Examples:
        >>> raise ConfigurationAccessError('Missing config')
        Traceback (most recent call last):
            ...
        fin_statement_model.core.errors.FinStatementModelError: Missing config
    """


T = TypeVar("T")


@overload
def cfg(path: str, *, strict: bool = False) -> Any:
    """Get a configuration value by dotted path.

    Args:
        path: Dotted path string to traverse the config.
        strict: If True, raise an error if the key is not found.

    Returns:
        The configuration value.

    Examples:
        >>> from fin_statement_model.config.helpers import cfg
        >>> cfg('logging.level')
        'WARNING'
    """
    ...


@overload
def cfg(path: str, default: T, *, strict: bool = False) -> T: ...


@overload
def cfg(path: Sequence[str], *, strict: bool = False) -> Any: ...


@overload
def cfg(path: Sequence[str], default: T, *, strict: bool = False) -> T: ...


def cfg(
    path: str | Sequence[str],
    default: Any = None,
    *,
    strict: bool = False,
) -> Any:
    """Get a configuration value by dotted path or sequence.

    Retrieves a configuration value from the global config object using a
    dotted path or sequence of path segments.

    Args:
        path: Dotted path string or sequence of keys to traverse the config.
        default: Default value to return if the key is not found.
        strict: If True, raise an error if the key is not found and no default is provided.

    Returns:
        The configuration value or the default if provided.

    Raises:
        ConfigurationAccessError: If the path is empty or a key does not exist
            and no default is provided (unless strict is True).

    Examples:
        >>> from fin_statement_model.config.helpers import cfg
        >>> cfg('logging.level')
        'WARNING'
        >>> cfg(['io', 'default_csv_delimiter'], default=';')
        ','
        >>> cfg('nonexistent.key', default=123)
        123
    """
    from .manager import get_config

    # Convert string path to sequence
    if isinstance(path, str):
        if not path:
            raise ConfigurationAccessError("Configuration path cannot be empty")
        parts = path.split(".")
    else:
        parts = list(path)

    if not parts:
        raise ConfigurationAccessError("Configuration path cannot be empty")

    obj = get_config()
    for i, part in enumerate(parts):
        full_path = ".".join(parts[: i + 1])
        if not hasattr(obj, part):
            if default is not None and not strict:
                return default
            raise ConfigurationAccessError(
                f"Configuration key '{full_path}' does not exist"
            )
        obj = getattr(obj, part)
    return obj if obj is not None else default


def cfg_or_param(config_path: str, param_value: Any) -> Any:
    """Return the parameter value if provided, otherwise get it from config.

    Args:
        config_path: Dotted path string to the configuration key.
        param_value: The value explicitly provided by the user.

    Returns:
        The `param_value` if it is not None, otherwise the configuration value.

    Examples:
        >>> from fin_statement_model.config.helpers import cfg_or_param
        >>> cfg_or_param('logging.level', 'DEBUG')
        'DEBUG'
        >>> cfg_or_param('logging.level', None)
        'WARNING'
    """
    return param_value if param_value is not None else cfg(config_path)


def parse_env_value(value: str) -> Any:
    """Parse an environment variable string into bool, int, float, or str.

    Attempts to convert the input string to a boolean if it matches
    "true"/"false", then to an integer if it represents a whole number,
    then to a float if it appears numeric with decimal or exponent. Otherwise,
    returns the original string or parses as JSON if possible.

    Args:
        value: The environment variable value as a string.

    Returns:
        The parsed native Python type: bool, int, float, list, dict, or str.

    Examples:
        >>> from fin_statement_model.config.helpers import parse_env_value
        >>> parse_env_value('true')
        True
        >>> parse_env_value('42')
        42
        >>> parse_env_value('-3.14')
        -3.14
        >>> parse_env_value('[1, 2, 3]')
        [1, 2, 3]
        >>> parse_env_value('foo')
        'foo'
    """
    val = value.strip()
    low = val.lower()
    # Boolean
    if low in ("true", "false"):
        return low == "true"
    # Integer (including negatives)
    if (val.startswith("-") and val[1:].isdigit()) or val.isdigit():
        try:
            return int(val)
        except ValueError:
            pass
    # Float
    try:
        float_val = float(val)
        if "." in val or "e" in low or "E" in value:
            return float_val
    except ValueError:
        pass
    # JSON fallback (lists/dicts/strings with quotes)
    try:
        import json

        parsed_json = json.loads(val)
        return parsed_json
    except Exception:  # noqa: BLE001
        # Fallback to original string
        return val
