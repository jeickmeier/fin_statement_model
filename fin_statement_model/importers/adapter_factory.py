"""
Factory for creating data source adapters.

This module provides a factory class that creates and manages data source adapters,
allowing the system to use different data sources without knowing the specific implementation details.
"""
from typing import Dict, Type
import importlib
import logging

from .adapter_base import DataSourceAdapter, FileDataSourceAdapter, APIDataSourceAdapter

# Configure logging
logger = logging.getLogger(__name__)


class AdapterFactory:
    """
    Factory class for creating data source adapters.
    
    This class handles the creation of adapter instances based on the adapter type,
    providing a centralized way to instantiate and manage adapters.
    """
    
    # Registry of available adapters
    _adapters: Dict[str, Type[DataSourceAdapter]] = {}
    
    @classmethod
    def register_adapter(cls, adapter_type: str, adapter_class: Type[DataSourceAdapter]) -> None:
        """
        Register a new adapter class with the factory.
        
        Args:
            adapter_type: Unique identifier for the adapter type
            adapter_class: Adapter class to register
            
        Raises:
            ValueError: If an adapter with the same type is already registered
        """
        if adapter_type in cls._adapters:
            logger.warning(f"Adapter type '{adapter_type}' is already registered. Overwriting.")
        cls._adapters[adapter_type] = adapter_class
        logger.info(f"Registered adapter '{adapter_type}'")
    
    @classmethod
    def create_adapter(cls, adapter_type: str, **kwargs) -> DataSourceAdapter:
        """
        Create an instance of the specified adapter type.
        
        Args:
            adapter_type: Type of adapter to create (e.g., 'fmp', 'excel')
            **kwargs: Configuration parameters for the adapter
            
        Returns:
            DataSourceAdapter: Instantiated adapter of the requested type
            
        Raises:
            ValueError: If the adapter type is not registered
        """
        if adapter_type not in cls._adapters:
            raise ValueError(f"Adapter type '{adapter_type}' is not registered. Available types: {list(cls._adapters.keys())}")
        
        adapter_class = cls._adapters[adapter_type]
        logger.debug(f"Creating adapter of type '{adapter_type}'")
        return adapter_class(**kwargs)
    
    @classmethod
    def get_adapter_class(cls, adapter_type: str) -> Type[DataSourceAdapter]:
        """
        Get the adapter class for the specified type.
        
        Args:
            adapter_type: Type of adapter to get
            
        Returns:
            Type[DataSourceAdapter]: Adapter class for the specified type
            
        Raises:
            ValueError: If the adapter type is not registered
        """
        if adapter_type not in cls._adapters:
            raise ValueError(f"Adapter type '{adapter_type}' is not registered. Available types: {list(cls._adapters.keys())}")
        return cls._adapters[adapter_type]
    
    @classmethod
    def list_adapters(cls) -> Dict[str, Type[DataSourceAdapter]]:
        """
        List all registered adapters.
        
        Returns:
            Dict[str, Type[DataSourceAdapter]]: Mapping of adapter types to adapter classes
        """
        return dict(cls._adapters)
    
    @classmethod
    def discover_adapters(cls, package_path: str = 'fin_statement_model.importers') -> None:
        """
        Discover and register adapters from a package.
        
        This method automatically discovers adapter classes by importing all modules
        in the specified package and looking for classes that inherit from DataSourceAdapter.
        
        Args:
            package_path: Dot-separated path to the package containing adapters
        """
        try:
            package = importlib.import_module(package_path)
            package_dir = package.__path__
            
            import pkgutil
            
            for _, module_name, is_pkg in pkgutil.iter_modules(package_dir):
                try:
                    module = importlib.import_module(f"{package_path}.{module_name}")
                    
                    # Find all classes that inherit from DataSourceAdapter
                    for name, obj in module.__dict__.items():
                        if (isinstance(obj, type) and 
                            issubclass(obj, DataSourceAdapter) and 
                            obj not in [DataSourceAdapter, FileDataSourceAdapter, APIDataSourceAdapter]):
                            
                            # Convert class name to adapter type (e.g., FMPAdapter -> fmp)
                            adapter_type = name.replace('Adapter', '').lower()
                            cls.register_adapter(adapter_type, obj)
                            
                except Exception as e:
                    logger.error(f"Error discovering adapters in module {module_name}: {e}")
        
        except Exception as e:
            logger.error(f"Error discovering adapters in package {package_path}: {e}")


# Automatically discover and register adapters when the module is imported
AdapterFactory.discover_adapters() 