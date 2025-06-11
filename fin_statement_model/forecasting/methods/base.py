"""Define base protocol and abstract class for forecast methods.

This module defines the interface that all forecast methods must implement
and provides an abstract base class with common functionality.
"""

from typing import Protocol, Any, Optional, runtime_checkable
from abc import ABC, abstractmethod

from fin_statement_model.core.nodes import Node


@runtime_checkable
class ForecastMethod(Protocol):
    """Protocol for forecast methods to implement.

    All forecast methods must provide a name property and implement
    validate_config and normalize_params, optionally prepare_historical_data.
    """

    @property
    def name(self) -> str:
        """Return the method name."""
        ...

    def validate_config(self, config: Any) -> None:
        """Validate the configuration for this method.

        Args:
            config: The method-specific configuration to validate.

        Raises:
            ValueError: If configuration is invalid.
        """
        ...

    def normalize_params(
        self, config: Any, forecast_periods: list[str]
    ) -> dict[str, Any]:
        """Normalize parameters for the NodeFactory.

        Args:
            config: The method-specific configuration.
            forecast_periods: List of periods to forecast.

        Returns:
            Dict with 'forecast_type' and 'growth_params' keys.
        """
        ...

    def prepare_historical_data(
        self, node: Node, historical_periods: list[str]
    ) -> Optional[list[float]]:
        """Prepare historical data for methods that need it.

        Args:
            node: The node to extract historical data from.
            historical_periods: List of historical periods.

        Returns:
            List of historical values or None if not needed.
        """
        ...


class BaseForecastMethod(ABC):
    """Provide an abstract base class for forecast methods.

    Enforces the forecast method interface and provides common functionality,
    including the get_forecast_params convenience method.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the method name."""

    @property
    @abstractmethod
    def internal_type(self) -> str:
        """Return the internal forecast type for NodeFactory."""

    @abstractmethod
    def validate_config(self, config: Any) -> None:
        """Validate the configuration for this method."""

    @abstractmethod
    def normalize_params(
        self, config: Any, forecast_periods: list[str]
    ) -> dict[str, Any]:
        """Normalize parameters for the NodeFactory."""

    def prepare_historical_data(
        self, node: Node, historical_periods: list[str]
    ) -> Optional[list[float]]:
        """Prepare historical data for methods that need it.

        Default implementation returns None (not needed).
        Override in methods that require historical data.
        """
        return None

    def get_forecast_params(
        self, config: Any, forecast_periods: list[str]
    ) -> dict[str, Any]:
        """Get complete forecast parameters.

        This is a convenience method that validates and normalizes in one call.

        Args:
            config: The method-specific configuration.
            forecast_periods: List of periods to forecast.

        Returns:
            Dict with 'forecast_type' and 'growth_params' keys.

        Raises:
            ValueError: If configuration is invalid.
        """
        self.validate_config(config)
        return self.normalize_params(config, forecast_periods)
