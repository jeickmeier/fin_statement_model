"""Forecast method protocol and abstract base class.

This module defines the interface (protocol) that all forecast methods must implement
and provides an abstract base class with common functionality for built-in and custom
forecast methods.

All forecast methods must implement the ForecastMethod protocol or inherit from
BaseForecastMethod. This ensures compatibility with the forecasting engine and node factory.

Example:
    >>> from fin_statement_model.forecasting.methods.base import BaseForecastMethod
    >>> class MyMethod(BaseForecastMethod):
    ...     @property
    ...     def name(self):
    ...         return "my_method"
    ...
    ...     @property
    ...     def internal_type(self):
    ...         return "my_type"
    ...
    ...     def validate_config(self, config):
    ...         pass
    ...
    ...     def normalize_params(self, config, forecast_periods):
    ...         return {"forecast_type": self.internal_type, "growth_params": config}
    >>> m = MyMethod()
    >>> m.get_forecast_params(0.1, ["2024"])  # doctest: +ELLIPSIS
    {'forecast_type': 'my_type', 'growth_params': 0.1}
"""

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

from fin_statement_model.core.nodes import Node


@runtime_checkable
class ForecastMethod(Protocol):
    """Protocol for forecast methods to implement.

    All forecast methods must provide a name property and implement
    validate_config and normalize_params, optionally prepare_historical_data.

    Example:
        >>> class Dummy:
        ...     @property
        ...     def name(self):
        ...         return "dummy"
        ...
        ...     def validate_config(self, config):
        ...         pass
        ...
        ...     def normalize_params(self, config, forecast_periods):
        ...         return {"forecast_type": "dummy", "growth_params": config}
        ...
        ...     def prepare_historical_data(self, node, historical_periods):
        ...         return None
        >>> isinstance(Dummy(), ForecastMethod)
        True
    """

    @property
    def name(self) -> str:
        """Return the method name.

        Returns:
            The unique name of the forecast method (e.g., 'simple', 'curve').
        """
        ...

    def validate_config(self, config: Any) -> None:
        """Validate the configuration for this method.

        Args:
            config: The method-specific configuration to validate.

        Raises:
            ValueError: If configuration is invalid.
        """
        ...

    def normalize_params(self, config: Any, forecast_periods: list[str]) -> dict[str, Any]:
        """Normalize parameters for the NodeFactory.

        Args:
            config: The method-specific configuration.
            forecast_periods: List of periods to forecast.

        Returns:
            Dict with 'forecast_type' and 'growth_params' keys.
        """
        ...

    def prepare_historical_data(self, node: Node, historical_periods: list[str]) -> list[float] | None:
        """Prepare historical data for methods that need it.

        Default implementation returns ``None`` (not needed). Override this
        method in subclasses that require historical data.

        Args:
            node: The node to extract historical data from.
            historical_periods: List of historical periods.

        Returns:
            List of historical values or ``None`` if no historical data is
            required.
        """
        _ = (node, historical_periods)  # Parameters intentionally unused in the base implementation
        return None


class BaseForecastMethod(ABC):
    """Abstract base class for forecast methods.

    Enforces the forecast method interface and provides common functionality,
    including the get_forecast_params convenience method.

    Example:
        >>> class Dummy(BaseForecastMethod):
        ...     @property
        ...     def name(self):
        ...         return "dummy"
        ...
        ...     @property
        ...     def internal_type(self):
        ...         return "dummy_type"
        ...
        ...     def validate_config(self, config):
        ...         pass
        ...
        ...     def normalize_params(self, config, forecast_periods):
        ...         return {"forecast_type": self.internal_type, "growth_params": config}
        >>> d = Dummy()
        >>> d.get_forecast_params(0.1, ["2024"])
        {'forecast_type': 'dummy_type', 'growth_params': 0.1}
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the method name.

        Returns:
            The unique name of the forecast method (e.g., 'simple', 'curve').
        """

    @property
    @abstractmethod
    def internal_type(self) -> str:
        """Return the internal forecast type for NodeFactory.

        Returns:
            The internal type string used by the node factory.
        """

    @abstractmethod
    def validate_config(self, config: Any) -> None:
        """Validate the configuration for this method.

        Args:
            config: The method-specific configuration to validate.

        Raises:
            ValueError: If configuration is invalid.
        """

    @abstractmethod
    def normalize_params(self, config: Any, forecast_periods: list[str]) -> dict[str, Any]:
        """Normalize parameters for the NodeFactory.

        Args:
            config: The method-specific configuration.
            forecast_periods: List of periods to forecast.

        Returns:
            Dict with 'forecast_type' and 'growth_params' keys.
        """

    def prepare_historical_data(self, node: Node, historical_periods: list[str]) -> list[float] | None:
        """Prepare historical data for methods that need it.

        Default implementation returns ``None`` (not needed). Override this
        method in subclasses that require historical data.

        Args:
            node: The node to extract historical data from.
            historical_periods: List of historical periods.

        Returns:
            List of historical values or ``None`` if no historical data is
            required.
        """
        _ = (node, historical_periods)  # Parameters intentionally unused in the base implementation
        return None

    def get_forecast_params(self, config: Any, forecast_periods: list[str]) -> dict[str, Any]:
        """Get complete forecast parameters.

        This is a convenience method that validates and normalizes in one call.

        Args:
            config: The method-specific configuration.
            forecast_periods: List of periods to forecast.

        Returns:
            Dict with 'forecast_type' and 'growth_params' keys.

        Raises:
            ValueError: If configuration is invalid.

        Example:
            >>> class Dummy(BaseForecastMethod):
            ...     @property
            ...     def name(self):
            ...         return "dummy"
            ...
            ...     @property
            ...     def internal_type(self):
            ...         return "dummy_type"
            ...
            ...     def validate_config(self, config):
            ...         pass
            ...
            ...     def normalize_params(self, config, forecast_periods):
            ...         return {"forecast_type": self.internal_type, "growth_params": config}
            >>> d = Dummy()
            >>> d.get_forecast_params(0.1, ["2024"])
            {'forecast_type': 'dummy_type', 'growth_params': 0.1}
        """
        self.validate_config(config)
        return self.normalize_params(config, forecast_periods)
