"""Utility functions for accessing configuration values.

This module provides functions to retrieve application configuration
settings from the central config object, with optional type checking and
default values. It also includes utilities for parsing environment variable
strings into native Python types.
"""

from __future__ import annotations
from typing import Any, Optional, TypeVar, overload
from collections.abc import Sequence
from fin_statement_model.core.errors import FinancialModelError


class ConfigurationAccessError(FinancialModelError):
    """Raised when there's an error accessing configuration values."""


T = TypeVar("T")


@overload
def cfg(path: str) -> Any: ...


@overload
def cfg(path: str, default: T) -> T: ...


@overload
def cfg(path: Sequence[str]) -> Any: ...


@overload
def cfg(path: Sequence[str], default: T) -> T: ...


def cfg(path: str | Sequence[str], default: Any = None) -> Any:
    """Get a configuration value by dotted path.

    Retrieves a configuration value from the global config object using a
    dotted path or sequence of path segments.

    Args:
        path: Dotted path string or sequence of keys to traverse the config.
        default: Default value to return if the key is not found.

    Returns:
        The configuration value or the default if provided.

    Raises:
        ConfigurationAccessError: If the path is empty or a key does not exist
            and no default is provided.

    Examples:
        >>> cfg("database.host")
        "localhost"

        >>> cfg(["database", "port"], default=5432)
        5432
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
            if default is not None:
                return default
            raise ConfigurationAccessError(
                f"Configuration key '{full_path}' does not exist"
            )
        obj = getattr(obj, part)
    return obj if obj is not None else default


def get_typed_config(
    path: str | Sequence[str], expected_type: type[T], default: Optional[T] = None
) -> T:
    """Get a configuration value with type checking.

    Retrieves a configuration value and verifies it is of the expected type.

    Args:
        path: Dotted path string or sequence of keys to traverse the config.
        expected_type: Type that the returned value must match.
        default: Default value to use if the key is not present.

    Returns:
        The configuration value of type `expected_type`.

    Raises:
        ConfigurationAccessError: If the key is None and no default is provided.
        TypeError: If the value is not an instance of `expected_type`.

    Examples:
        >>> get_typed_config("features.enable_feature_x", bool, default=False)
        True
    """
    value = cfg(path, default)
    if value is None and default is None:
        raise ConfigurationAccessError(
            f"Configuration key '{path}' is None and no default provided"
        )
    if not isinstance(value, expected_type):
        raise TypeError(
            f"Configuration key '{path}' has type {type(value).__name__}, "
            f"expected {expected_type.__name__}"
        )
    return value


def cfg_or_param(config_path: str, param_value: Any) -> Any:
    """Return the parameter value if provided, otherwise get it from config.

    Args:
        config_path: Dotted path string to the configuration key.
        param_value: The value explicitly provided by the user.

    Returns:
        The `param_value` if it is not None, otherwise the configuration value.

    Examples:
        >>> cfg_or_param("logging.level", "DEBUG")
        "DEBUG"

        >>> cfg_or_param("logging.level", None)
        "INFO"
    """
    return param_value if param_value is not None else cfg(config_path)


def parse_env_value(value: str) -> bool | int | float | str:
    """Parse an environment variable string into bool, int, float, or str.

    Attempts to convert the input string to a boolean if it matches
    "true"/"false", then to an integer if it represents a whole number,
    then to a float if it appears numeric with decimal or exponent. Otherwise,
    returns the original string.

    Args:
        value: The environment variable value as a string.

    Returns:
        The parsed native Python type: bool, int, float, or str.

    Examples:
        >>> parse_env_value("true")
        True

        >>> parse_env_value("42")
        42

        >>> parse_env_value("-3.14")
        -3.14

        >>> parse_env_value("foo")
        "foo"
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
    # Fallback to string
    return val
