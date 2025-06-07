"""Utility functions for accessing configuration values."""

from __future__ import annotations
from typing import Any, Optional, TypeVar, overload
from collections.abc import Sequence
from .manager import get_config
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
    """Get a configuration value by dotted path."""
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
        full_path = ".".join(parts[:i+1])
        if not hasattr(obj, part):
            if default is not None:
                return default
            raise ConfigurationAccessError(f"Configuration key '{full_path}' does not exist")
        obj = getattr(obj, part)
    return obj if obj is not None else default


def get_typed_config(
    path: str | Sequence[str], expected_type: type[T], default: Optional[T] = None
) -> T:
    """Get a configuration value with type checking."""
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
    """Return the parameter value if provided, otherwise get from config."""
    return param_value if param_value is not None else cfg(config_path)


def parse_env_value(value: str) -> bool | int | float | str:
    """Parse an environment variable string into bool, int, float, or str."""
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

