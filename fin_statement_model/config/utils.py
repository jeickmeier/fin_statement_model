"""Utility functions for working with configuration.

This module provides helper functions to make accessing configuration
values easier and more concise throughout the codebase.
"""

from __future__ import annotations
from typing import Any, Sequence, Optional, TypeVar, overload
from fin_statement_model.config import get_config, Config
from fin_statement_model.core.errors import FinancialModelError


class ConfigurationAccessError(FinancialModelError):
    """Raised when there's an error accessing configuration values."""


T = TypeVar('T')


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
    
    This is a convenience function that provides easy access to nested
    configuration values without having to navigate the full object hierarchy.
    
    Args:
        path: Either a dotted string path (e.g., "io.default_excel_sheet") or
              a sequence of path components (e.g., ["io", "default_excel_sheet"])
        default: Default value to return if the path doesn't exist or value is None.
                If not provided, will raise ConfigurationAccessError for missing paths.
    
    Returns:
        The configuration value at the specified path, or the default value.
        
    Raises:
        ConfigurationAccessError: If the path doesn't exist and no default is provided.
        
    Examples:
        >>> cfg("io.default_excel_sheet")  # Returns "Sheet1"
        >>> cfg("io.missing_key", "default")  # Returns "default" 
        >>> cfg(["forecasting", "default_periods"])  # Returns 5
        >>> cfg("invalid.path")  # Raises ConfigurationAccessError
    """
    # Convert string path to sequence
    if isinstance(path, str):
        if not path:
            raise ConfigurationAccessError("Configuration path cannot be empty")
        parts = path.split(".")
    else:
        parts = list(path)
    
    if not parts:
        raise ConfigurationAccessError("Configuration path cannot be empty")
    
    # Start from the root config
    try:
        obj = get_config()
    except Exception as e:
        raise ConfigurationAccessError(f"Failed to get configuration: {e}") from e
    
    # Navigate through the path
    full_path = ""
    for i, part in enumerate(parts):
        full_path = ".".join(parts[:i+1])
        
        # Check if the attribute exists
        if not hasattr(obj, part):
            if default is not None:
                return default
            raise ConfigurationAccessError(
                f"Configuration key '{full_path}' does not exist"
            )
        
        try:
            obj = getattr(obj, part)
        except AttributeError:
            if default is not None:
                return default
            raise ConfigurationAccessError(
                f"Cannot access configuration key '{full_path}'"
            )
    
    # Return the value, or default if value is None
    return obj if obj is not None else default


def get_typed_config(path: str | Sequence[str], expected_type: type[T], 
                    default: Optional[T] = None) -> T:
    """Get a configuration value with type checking.
    
    Args:
        path: Configuration path (dotted string or sequence)
        expected_type: The expected type of the configuration value
        default: Default value if path doesn't exist (must match expected_type)
        
    Returns:
        The configuration value cast to the expected type.
        
    Raises:
        ConfigurationAccessError: If path doesn't exist and no default provided
        TypeError: If the value doesn't match the expected type
        
    Examples:
        >>> get_typed_config("forecasting.default_periods", int)  # Returns 5
        >>> get_typed_config("display.scale_factor", float)  # Returns 1.0
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
    """Return the parameter value if provided, otherwise get from config.
    
    This is useful for functions that want to use config defaults but
    allow overrides via parameters.
    
    Args:
        config_path: The configuration path to use if param_value is None
        param_value: The parameter value (if None, will use config)
        
    Returns:
        The parameter value if not None, otherwise the config value
        
    Examples:
        >>> def process_data(delimiter: Optional[str] = None):
        ...     delimiter = cfg_or_param("io.default_csv_delimiter", delimiter)
        ...     # Use delimiter...
    """
    return param_value if param_value is not None else cfg(config_path)


def list_config_paths(prefix: str = "") -> list[str]:
    """List all available configuration paths.
    
    Args:
        prefix: Optional prefix to filter paths (e.g., "io" for all I/O configs)
        
    Returns:
        List of all configuration paths that start with the prefix
        
    Examples:
        >>> list_config_paths("forecasting")
        ['forecasting.default_method', 'forecasting.default_periods', ...]
    """
    config = get_config()
    paths = []
    
    def _extract_paths(obj: Any, current_path: str = "") -> None:
        """Recursively extract configuration paths."""
        # Check if it's a Pydantic model by checking the class
        if hasattr(obj.__class__, 'model_fields'):
            # It's a Pydantic model - access model_fields from the class
            for field_name in obj.__class__.model_fields:
                field_path = f"{current_path}.{field_name}" if current_path else field_name
                field_value = getattr(obj, field_name)
                
                # Check if the field value is also a Pydantic model
                if hasattr(field_value.__class__, 'model_fields'):
                    # Nested model
                    _extract_paths(field_value, field_path)
                else:
                    # Leaf value
                    if not prefix or field_path.startswith(prefix):
                        paths.append(field_path)
    
    _extract_paths(config)
    return sorted(paths)


# Convenience functions for common config values
def default_csv_delimiter() -> str:
    """Get the default CSV delimiter from config."""
    return cfg("io.default_csv_delimiter", ",")


def default_excel_sheet() -> str:
    """Get the default Excel sheet name from config."""
    return cfg("io.default_excel_sheet", "Sheet1")


def default_periods() -> int:
    """Get the default number of forecast periods from config."""
    return get_typed_config("forecasting.default_periods", int)


def default_growth_rate() -> float:
    """Get the default growth rate from config."""
    return get_typed_config("forecasting.default_growth_rate", float, 0.0)


def api_timeout() -> int:
    """Get the API timeout from config."""
    return get_typed_config("api.api_timeout", int, 30)


def api_retry_count() -> int:
    """Get the API retry count from config."""
    return get_typed_config("api.api_retry_count", int, 3) 