"""Forecast method registry and selection strategies.

This module manages the ForecastMethodRegistry for registering and retrieving
forecast methods, and exposes convenience functions for global access. It enables
dynamic extensibility for custom forecasting methods and provides helpers for
querying and listing available methods.

Features:
    - Register, unregister, and retrieve forecast methods by name
    - List available methods and query method metadata
    - Global registry instance for convenience
    - Extensible: add custom methods at runtime

Example:
    >>> from fin_statement_model.forecasting.strategies import (
    ...     forecast_registry,
    ...     get_forecast_method,
    ...     register_forecast_method,
    ... )
    >>> from fin_statement_model.forecasting.methods.simple import SimpleForecastMethod
    >>> method = get_forecast_method("simple")
    >>> method.name
    'simple'
    >>> class MyMethod(SimpleForecastMethod):
    ...     @property
    ...     def name(self):
    ...         return "my_custom"
    >>> register_forecast_method(MyMethod())
    >>> forecast_registry.has_method("my_custom")
    True
"""

import logging
from typing import Any

from .methods import (
    AverageForecastMethod,
    CurveForecastMethod,
    ForecastMethod,
    HistoricalGrowthForecastMethod,
    SimpleForecastMethod,
    StatisticalForecastMethod,
)

logger = logging.getLogger(__name__)


class ForecastMethodRegistry:
    """Manage forecast methods in a registry.

    Provides methods to register, unregister, retrieve, and list available
    forecast methods. Supports querying method metadata.

    Example:
        >>> registry = ForecastMethodRegistry()
        >>> method = registry.get_method("simple")
        >>> print(registry.list_methods())
        ['simple', 'curve', 'statistical', 'average', 'historical_growth']
    """

    def __init__(self) -> None:
        """Initialize the registry with built-in methods."""
        self._methods: dict[str, ForecastMethod] = {}
        self._register_builtin_methods()

    def _register_builtin_methods(self) -> None:
        """Register all built-in forecast methods."""
        builtin_methods = [
            SimpleForecastMethod(),
            CurveForecastMethod(),
            StatisticalForecastMethod(),
            AverageForecastMethod(),
            HistoricalGrowthForecastMethod(),
        ]

        for method in builtin_methods:
            self.register(method)
            logger.debug("Registered built-in forecast method: %s", method.name)

    def register(self, method: ForecastMethod) -> None:
        """Register a new forecast method.

        Args:
            method: The forecast method to register.

        Raises:
            ValueError: If a method with the same name is already registered.

        Example:
            >>> from fin_statement_model.forecasting.methods.simple import SimpleForecastMethod
            >>> registry = ForecastMethodRegistry()
            >>> registry.register(SimpleForecastMethod())
        """
        if method.name in self._methods:
            raise ValueError(f"Forecast method '{method.name}' is already registered")

        self._methods[method.name] = method
        logger.info("Registered forecast method: %s", method.name)

    def unregister(self, name: str) -> None:
        """Unregister a forecast method.

        Args:
            name: The name of the method to unregister.

        Raises:
            KeyError: If the method is not registered.

        Example:
            >>> registry = ForecastMethodRegistry()
            >>> registry.unregister("simple")
        """
        if name not in self._methods:
            raise KeyError(f"Forecast method '{name}' is not registered")

        del self._methods[name]
        logger.info("Unregistered forecast method: %s", name)

    def get_method(self, name: str) -> ForecastMethod:
        """Get a forecast method by name.

        Args:
            name: The name of the method to retrieve.

        Returns:
            The requested forecast method.

        Raises:
            ValueError: If the method is not registered.

        Example:
            >>> registry = ForecastMethodRegistry()
            >>> method = registry.get_method("simple")
            >>> method.name
            'simple'
        """
        if name not in self._methods:
            available = ", ".join(sorted(self._methods.keys()))
            raise ValueError(f"Unknown forecast method: '{name}'. Available methods: {available}")

        return self._methods[name]

    def list_methods(self) -> list[str]:
        """List all available forecast methods.

        Returns:
            Sorted list of registered method names.

        Example:
            >>> registry = ForecastMethodRegistry()
            >>> registry.list_methods()
            ['average', 'curve', 'historical_growth', 'simple', 'statistical']
        """
        return sorted(self._methods.keys())

    def has_method(self, name: str) -> bool:
        """Check if a method is registered.

        Args:
            name: The name of the method to check.

        Returns:
            True if the method is registered, False otherwise.

        Example:
            >>> registry = ForecastMethodRegistry()
            >>> registry.has_method("simple")
            True
        """
        return name in self._methods

    def get_method_info(self, name: str) -> dict[str, Any]:
        """Get information about a forecast method.

        Args:
            name: The name of the method.

        Returns:
            Dictionary with method information including docstring.

        Raises:
            ValueError: If the method is not registered.

        Example:
            >>> registry = ForecastMethodRegistry()
            >>> info = registry.get_method_info("simple")
            >>> "name" in info and "description" in info
            True
        """
        method = self.get_method(name)
        return {
            "name": method.name,
            "class": method.__class__.__name__,
            "description": method.__class__.__doc__ or "No description available",
            "module": method.__class__.__module__,
        }


# Global registry instance
forecast_registry = ForecastMethodRegistry()


def get_forecast_method(name: str) -> ForecastMethod:
    """Retrieve a forecast method from the global registry.

    Args:
        name: The name of the method to retrieve.

    Returns:
        The requested forecast method.

    Raises:
        ValueError: If the method is not registered.

    Example:
        >>> from fin_statement_model.forecasting.strategies import get_forecast_method
        >>> method = get_forecast_method("simple")
        >>> method.name
        'simple'
    """
    return forecast_registry.get_method(name)


def register_forecast_method(method: ForecastMethod) -> None:
    """Register a custom forecast method in the global registry.

    Args:
        method: The forecast method to register.

    Raises:
        ValueError: If a method with the same name is already registered.

    Example:
        >>> from fin_statement_model.forecasting.methods.simple import SimpleForecastMethod
        >>> from fin_statement_model.forecasting.strategies import register_forecast_method
        >>> register_forecast_method(SimpleForecastMethod())
    """
    forecast_registry.register(method)
