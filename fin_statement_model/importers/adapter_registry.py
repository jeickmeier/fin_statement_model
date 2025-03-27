"""
Registry for data source adapter instances.

This module provides a registry for storing and retrieving adapter instances,
allowing for efficient reuse of adapters across the application.
"""

from typing import Dict,  Optional
import logging

from .adapter_base import DataSourceAdapter
from .adapter_factory import AdapterFactory

# Configure logging
logger = logging.getLogger(__name__)


class AdapterRegistry:
    """
    Registry for storing and retrieving adapter instances.

    This class provides a centralized registry for adapter instances, allowing
    for efficient reuse of adapters across the application. It acts as a cache
    for adapter instances, storing them by type and configuration.
    """

    # Registry of adapter instances
    _instances: Dict[str, Dict[str, DataSourceAdapter]] = {}

    @classmethod
    def register(
        cls, adapter_type: str, config_key: str, adapter: DataSourceAdapter
    ) -> None:
        """
        Register an adapter instance with the registry.

        Args:
            adapter_type: Type of the adapter (e.g., 'fmp', 'excel')
            config_key: Unique key identifying the adapter configuration
            adapter: Adapter instance to register
        """
        if adapter_type not in cls._instances:
            cls._instances[adapter_type] = {}

        cls._instances[adapter_type][config_key] = adapter
        logger.debug(
            f"Registered adapter instance of type '{adapter_type}' with config key '{config_key}'"
        )

    @classmethod
    def get(cls, adapter_type: str, config_key: str) -> Optional[DataSourceAdapter]:
        """
        Retrieve an adapter instance from the registry.

        Args:
            adapter_type: Type of the adapter (e.g., 'fmp', 'excel')
            config_key: Unique key identifying the adapter configuration

        Returns:
            Optional[DataSourceAdapter]: The adapter instance, or None if not found
        """
        if (
            adapter_type not in cls._instances
            or config_key not in cls._instances[adapter_type]
        ):
            return None

        logger.debug(
            f"Retrieved adapter instance of type '{adapter_type}' with config key '{config_key}'"
        )
        return cls._instances[adapter_type][config_key]

    @classmethod
    def get_or_create(
        cls, adapter_type: str, config_key: str, **config
    ) -> DataSourceAdapter:
        """
        Retrieve an adapter instance from the registry, or create it if it doesn't exist.

        Args:
            adapter_type: Type of the adapter (e.g., 'fmp', 'excel')
            config_key: Unique key identifying the adapter configuration
            **config: Configuration parameters for creating a new adapter instance

        Returns:
            DataSourceAdapter: The adapter instance

        Raises:
            ValueError: If the adapter type is not registered
        """
        adapter = cls.get(adapter_type, config_key)
        if adapter is not None:
            return adapter

        logger.debug(
            f"Creating new adapter instance of type '{adapter_type}' with config key '{config_key}'"
        )
        adapter = AdapterFactory.create_adapter(adapter_type, **config)
        cls.register(adapter_type, config_key, adapter)
        return adapter

    @classmethod
    def remove(cls, adapter_type: str, config_key: str) -> bool:
        """
        Remove an adapter instance from the registry.

        Args:
            adapter_type: Type of the adapter (e.g., 'fmp', 'excel')
            config_key: Unique key identifying the adapter configuration

        Returns:
            bool: True if the adapter was removed, False if it wasn't found
        """
        if (
            adapter_type not in cls._instances
            or config_key not in cls._instances[adapter_type]
        ):
            return False

        del cls._instances[adapter_type][config_key]
        logger.debug(
            f"Removed adapter instance of type '{adapter_type}' with config key '{config_key}'"
        )

        # Clean up empty adapter type dictionaries
        if not cls._instances[adapter_type]:
            del cls._instances[adapter_type]

        return True

    @classmethod
    def clear(cls) -> None:
        """
        Clear all adapter instances from the registry.
        """
        cls._instances.clear()
        logger.debug("Cleared all adapter instances from registry")

    @classmethod
    def list_instances(cls) -> Dict[str, Dict[str, DataSourceAdapter]]:
        """
        List all adapter instances in the registry.

        Returns:
            Dict[str, Dict[str, DataSourceAdapter]]: Mapping of adapter types to configurations to instances
        """
        return dict(cls._instances)
