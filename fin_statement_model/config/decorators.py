"""Decorators for configuration migration.

This module provides decorators to help migrate from hard-coded defaults
to configuration-based defaults while maintaining backward compatibility.
"""

from __future__ import annotations
import functools
import warnings
from typing import Any, Callable, TypeVar, ParamSpec
from fin_statement_model.config import cfg

P = ParamSpec('P')
T = TypeVar('T')


def uses_config_default(param_name: str, config_path: str, 
                       deprecated: bool = False) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator that replaces None parameter values with config defaults.
    
    This decorator allows functions to use configuration defaults for parameters
    while maintaining backward compatibility with explicit values.
    
    Args:
        param_name: Name of the parameter to check
        config_path: Configuration path to use for default value
        deprecated: If True, warns when None is passed (encouraging explicit values)
        
    Returns:
        Decorated function that uses config defaults
        
    Example:
        >>> @uses_config_default("delimiter", "io.default_csv_delimiter")
        ... def read_csv(file_path: str, delimiter: Optional[str] = None):
        ...     # delimiter will be set from config if None
        ...     return pd.read_csv(file_path, delimiter=delimiter)
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Check if the parameter was provided
            if param_name in kwargs:
                param_value = kwargs[param_name]
                if param_value is None:
                    # Get value from config
                    config_value = cfg(config_path)
                    kwargs[param_name] = config_value
                    
                    if deprecated:
                        warnings.warn(
                            f"Passing None for '{param_name}' is deprecated. "
                            f"The value will be taken from config key '{config_path}'. "
                            f"Consider omitting the parameter or passing an explicit value.",
                            DeprecationWarning,
                            stacklevel=2
                        )
            else:
                # Parameter not provided at all - check function signature
                import inspect
                sig = inspect.signature(func)
                
                if param_name in sig.parameters:
                    # Parameter exists but wasn't provided
                    param = sig.parameters[param_name]
                    
                    # Only set from config if default is None
                    if param.default is None or param.default is inspect.Parameter.empty:
                        kwargs[param_name] = cfg(config_path)
            
            return func(*args, **kwargs)
        
        # Add documentation about config usage
        if wrapper.__doc__:
            wrapper.__doc__ += (
                f"\n\n    Note: Parameter '{param_name}' uses config default from "
                f"'{config_path}' when not provided."
            )
        
        return wrapper
    return decorator


def migrate_to_config(*param_configs: tuple[str, str], 
                     grace_period: bool = True) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator for migrating multiple parameters to use config defaults.
    
    This is a convenience decorator for functions with multiple parameters
    that should use config defaults.
    
    Args:
        *param_configs: Tuples of (param_name, config_path)
        grace_period: If True, allows hard-coded defaults during migration
        
    Returns:
        Decorated function that uses config for specified parameters
        
    Example:
        >>> @migrate_to_config(
        ...     ("periods", "forecasting.default_periods"),
        ...     ("growth_rate", "forecasting.default_growth_rate")
        ... )
        ... def forecast(data, periods=None, growth_rate=None):
        ...     # Both parameters will use config if None
        ...     pass
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        # Apply uses_config_default for each parameter
        decorated = func
        for param_name, config_path in param_configs:
            decorated = uses_config_default(
                param_name, config_path, deprecated=not grace_period
            )(decorated)
        return decorated
    return decorator


def config_aware_init(class_: type[T]) -> type[T]:
    """Class decorator that makes __init__ parameters use config defaults.
    
    This decorator examines the class __init__ method and automatically
    applies config defaults based on parameter names that match config keys.
    
    Args:
        class_: The class to decorate
        
    Returns:
        Decorated class with config-aware initialization
        
    Example:
        >>> @config_aware_init
        ... class DataProcessor:
        ...     def __init__(self, delimiter=None, validate_on_read=None):
        ...         # Parameters will be set from matching config keys
        ...         self.delimiter = delimiter
        ...         self.validate = validate_on_read
    """
    # Common parameter to config mappings
    param_mappings = {
        "delimiter": "io.default_csv_delimiter",
        "sheet_name": "io.default_excel_sheet",
        "periods": "forecasting.default_periods",
        "growth_rate": "forecasting.default_growth_rate",
        "method": "forecasting.default_method",
        "scale_factor": "display.scale_factor",
        "scale": "display.scale_factor",
        "retry_count": "api.api_retry_count",
        "max_retries": "api.api_retry_count",
        "timeout": "api.api_timeout",
        "validate_on_read": "io.validate_on_read",
        "auto_clean": "preprocessing.auto_clean_data",
    }
    
    original_init = class_.__init__
    
    @functools.wraps(original_init)
    def new_init(self, *args, **kwargs):
        import inspect
        sig = inspect.signature(original_init)
        
        # Check each parameter
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
                
            # Check if we have a mapping for this parameter
            if param_name in param_mappings and param_name not in kwargs:
                # Only apply if the default is None
                if param.default is None or param.default is inspect.Parameter.empty:
                    config_path = param_mappings[param_name]
                    try:
                        kwargs[param_name] = cfg(config_path)
                    except Exception:
                        # Silently skip if config key doesn't exist
                        pass
        
        original_init(self, *args, **kwargs)
    
    class_.__init__ = new_init
    return class_


def warn_hardcoded_default(param_name: str, config_path: str, 
                          hardcoded_value: Any) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator that warns about hard-coded defaults that should use config.
    
    This is useful during migration to identify functions still using
    hard-coded defaults.
    
    Args:
        param_name: Parameter name with hard-coded default
        config_path: Config path that should be used instead
        hardcoded_value: The hard-coded value to warn about
        
    Returns:
        Decorated function that warns about hard-coded usage
        
    Example:
        >>> @warn_hardcoded_default("periods", "forecasting.default_periods", 5)
        ... def forecast(data, periods=5):  # Will warn when periods=5 is used
        ...     pass
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            import inspect
            sig = inspect.signature(func)
            
            # Check if parameter exists and get its default
            if param_name in sig.parameters:
                param = sig.parameters[param_name]
                param_default = param.default if param.default != inspect.Parameter.empty else None
                
                # Get the actual value being used
                if param_name in kwargs:
                    # Explicitly provided
                    param_value = kwargs[param_name]
                else:
                    # Using default - bind arguments to get actual value
                    bound = sig.bind(*args, **kwargs)
                    bound.apply_defaults()
                    param_value = bound.arguments.get(param_name)
                
                # Warn if using the hard-coded value
                if param_value == hardcoded_value and param_default == hardcoded_value:
                    warnings.warn(
                        f"Function '{func.__name__}' is using hard-coded default "
                        f"{param_name}={hardcoded_value}. Consider using "
                        f"config value from '{config_path}' instead.",
                        FutureWarning,
                        stacklevel=2
                    )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator 