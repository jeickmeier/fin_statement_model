"""
Transformer Factory for the Financial Statement Model.

This module provides a factory for creating and managing data transformers.
"""

import logging
import importlib
import inspect
import pkgutil
from typing import Dict, Type, List

from .base_transformer import DataTransformer

# Configure logging
logger = logging.getLogger(__name__)


class TransformerFactory:
    """
    Factory class for creating and managing data transformers.

    This class centralizes the creation and registration of transformers,
    providing a clean interface for accessing transformation functionality.
    """

    # Registry of transformer types
    _transformers: Dict[str, Type[DataTransformer]] = {}

    @classmethod
    def register_transformer(
        cls, name: str, transformer_class: Type[DataTransformer]
    ) -> None:
        """
        Register a transformer class with the factory.

        Args:
            name: Name to register the transformer under
            transformer_class: The transformer class to register

        Raises:
            ValueError: If the name is already registered
            TypeError: If transformer_class is not a subclass of DataTransformer
        """
        if name in cls._transformers:
            raise ValueError(f"Transformer name '{name}' is already registered")

        if not issubclass(transformer_class, DataTransformer):
            raise TypeError("Transformer class must be a subclass of DataTransformer")

        cls._transformers[name] = transformer_class
        logger.info(f"Registered transformer '{name}'")

    @classmethod
    def create_transformer(cls, name: str, **kwargs) -> DataTransformer:
        """
        Create a transformer instance by name.

        Args:
            name: Name of the registered transformer
            **kwargs: Arguments to pass to the transformer constructor

        Returns:
            DataTransformer: An instance of the requested transformer

        Raises:
            ValueError: If no transformer is registered with the given name
        """
        if name not in cls._transformers:
            raise ValueError(f"No transformer registered with name '{name}'")

        transformer_class = cls._transformers[name]
        transformer = transformer_class(**kwargs)
        logger.debug(f"Created transformer '{name}'")
        return transformer

    @classmethod
    def list_transformers(cls) -> List[str]:
        """
        List all registered transformer names.

        Returns:
            List[str]: List of registered transformer names
        """
        return list(cls._transformers.keys())

    @classmethod
    def get_transformer_class(cls, name: str) -> Type[DataTransformer]:
        """
        Get a transformer class by name.

        Args:
            name: Name of the registered transformer

        Returns:
            Type[DataTransformer]: The requested transformer class

        Raises:
            ValueError: If no transformer is registered with the given name
        """
        if name not in cls._transformers:
            raise ValueError(f"No transformer registered with name '{name}'")

        return cls._transformers[name]

    @classmethod
    def discover_transformers(cls, package_name: str) -> None:
        """
        Discover and register all transformers in a package.

        This method imports all modules in the specified package and
        registers any DataTransformer subclasses found.

        Args:
            package_name: Name of the package to search
        """
        try:
            package = importlib.import_module(package_name)
            package_path = package.__path__

            # Import all modules in the package
            for _, module_name, _ in pkgutil.iter_modules(package_path):
                full_module_name = f"{package_name}.{module_name}"
                module = importlib.import_module(full_module_name)

                # Find all DataTransformer subclasses in the module
                for name, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj)
                        and issubclass(obj, DataTransformer)
                        and obj != DataTransformer
                    ):
                        # Register the transformer with its class name
                        cls.register_transformer(name, obj)

            logger.info(f"Discovered transformers from package '{package_name}'")

        except ImportError as e:
            logger.error(
                f"Error discovering transformers from package '{package_name}': {e}"
            )

    @classmethod
    def create_composite_transformer(
        cls, transformer_names: List[str], **kwargs
    ) -> DataTransformer:
        """
        Create a composite transformer from a list of transformer names.

        Args:
            transformer_names: List of registered transformer names to include in the pipeline
            **kwargs: Additional arguments to pass to individual transformers

        Returns:
            DataTransformer: A composite transformer containing the specified transformers

        Raises:
            ValueError: If any transformer name is not registered
        """
        from .base_transformer import CompositeTransformer

        transformers = []
        for name in transformer_names:
            transformers.append(cls.create_transformer(name, **kwargs))

        return CompositeTransformer(transformers)
