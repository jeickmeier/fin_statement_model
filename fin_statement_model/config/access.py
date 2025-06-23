"""Access helpers for fin_statement_model configuration.

This module centralises the tiny but widely-used helper functions for reading
configuration values and parsing environment variables/values.  It replaces the
older *helpers.py* and *utils.py* modules to flatten the package structure
while keeping the original public API intact.

Public surface:
    - `cfg`: Read a value from the global configuration.
    - `cfg_or_param`: Return a parameter if provided, else read from config.
    - `parse_env_value`: Coerce a string (from env var) to a Python type.
    - `parse_env_var`: Split an environment variable key into config path parts.
    - `ConfigurationAccessError`: Exception for access errors.

These helpers are re-exported by `fin_statement_model.config` and are safe to
import at any time, as they contain no complex or slow top-level imports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar, overload

from fin_statement_model.core.errors import FinStatementModelError

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "ConfigurationAccessError",
    "cfg",
    "cfg_or_param",
    "parse_env_value",
    "parse_env_var",
]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ConfigurationAccessError(FinStatementModelError):
    """Raised when configuration values cannot be accessed."""


# ---------------------------------------------------------------------------
# cfg helpers - formerly config.helpers
# ---------------------------------------------------------------------------

T = TypeVar("T")


@overload
def cfg(path: str, *, strict: bool = False) -> Any: ...


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
    """Retrieve a configuration value by dotted path or sequence.

    This is a thin wrapper around :pyfunc:`fin_statement_model.config.get_config`.
    It exists in a standalone module so it can be imported very early during
    package initialisation without causing circular-import issues.

    Examples:
        Assuming a default configuration where `logging.level` is 'WARNING':

        >>> from fin_statement_model.config import cfg
        >>> cfg("logging.level")
        'WARNING'
        >>> cfg("api.timeout", default=30)
        30
        >>> cfg(["display", "flags", "include_notes_column"])
        False
    """
    from .store import get_config  # local import to avoid cycles

    # Convert string path → list of segments
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
            raise ConfigurationAccessError(f"Configuration key '{full_path}' does not exist")
        obj = getattr(obj, part)
    return obj if obj is not None else default


def cfg_or_param(config_path: str, param_value: Any) -> Any:
    """Return `param_value` if provided, otherwise fall back to cfg().

    This is useful for functions that allow per-call overrides of a default
    value that is stored in the global configuration.

    Examples:
        >>> from fin_statement_model.config import cfg_or_param
        >>> # param_value is used if not None
        >>> cfg_or_param("logging.level", "DEBUG")
        'DEBUG'
        >>> # Falls back to config if param_value is None
        >>> cfg_or_param("logging.level", None)
        'WARNING'
    """
    return param_value if param_value is not None else cfg(config_path)


# ---------------------------------------------------------------------------
# Environment value & variable parsing - formerly helpers/utils
# ---------------------------------------------------------------------------


def parse_env_value(value: str) -> Any:
    """Parse an environment variable *value* into a native Python type.

    Tries to interpret the string as a boolean, integer, float, or JSON
    object/array. If all attempts fail, returns the original string.

    Examples:
        >>> from fin_statement_model.config.access import parse_env_value
        >>> parse_env_value("true")
        True
        >>> parse_env_value("123")
        123
        >>> parse_env_value("3.14")
        3.14
        >>> parse_env_value('[1, "a", null]')
        [1, 'a', None]
        >>> parse_env_value("just a string")
        'just a string'
    """
    val = value.strip()
    low = val.lower()

    # Booleans
    if low in ("true", "false"):
        return low == "true"

    # Integers (including negatives)
    if (val.startswith("-") and val[1:].isdigit()) or val.isdigit():
        try:
            return int(val)
        except ValueError:
            pass

    # Floats
    try:
        float_val = float(val)
        if "." in val or "e" in low or "E" in value:
            return float_val
    except ValueError:
        pass

    # JSON lists/dicts/strings
    try:
        import json

        # Only catch JSON decoding errors; other issues should propagate.
        return json.loads(val)
    except json.JSONDecodeError:
        # Fallback to raw string when the value is not valid JSON.
        return val


# ---------------------------------------------------------------------------
# Key parsing helper (moved from utils.parse_env_var)
# ---------------------------------------------------------------------------


def parse_env_var(key: str, *, prefix: str = "FSM_") -> list[str]:
    """Split an env-var `key` into lower-case config path segments.

    It strips the given `prefix` and splits the remainder by `__` (preferred)
    or `_` (fallback), returning a list of lower-case strings.

    Examples:
        >>> from fin_statement_model.config.access import parse_env_var
        >>> parse_env_var("FSM_LOGGING__LEVEL")
        ['logging', 'level']
        >>> parse_env_var("FSM_IO_DEFAULT_CSV_DELIMITER")
        ['io', 'default', 'csv', 'delimiter']
        >>> parse_env_var("MY_APP_SETTING", prefix="MY_APP_")
        ['setting']
    """
    # Remove prefix if present
    key_body = key[len(prefix) :] if key.startswith(prefix) else key

    # Prefer double underscore separator, fallback to single underscore
    parts = key_body.split("__") if "__" in key_body else key_body.split("_")

    return [segment.lower() for segment in parts if segment]
