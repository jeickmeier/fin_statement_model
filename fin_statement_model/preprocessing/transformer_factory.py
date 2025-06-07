"""Provide TransformerFactory to create and manage data transformers.

This module implements a factory for registering and instantiating transformers.
"""

import importlib
import re
import inspect
import pkgutil
import logging
from typing import ClassVar, Any

from fin_statement_model.preprocessing.base_transformer import DataTransformer
from fin_statement_model.preprocessing.errors import (
    TransformerRegistrationError,
    TransformerConfigurationError,
)

logger = logging.getLogger(__name__)


class TransformerFactory:
    """Create and manage transformer instances.

    Centralizes transformer registration, discovery, and instantiation.
    """

    # Registry of transformer types
    _transformers: ClassVar[dict[str, type[DataTransformer]]] = {}

    @classmethod
    def register_transformer(cls, name: str, transformer_class: type[DataTransformer]) -> None:
        """Register a transformer class with the factory.

        Args:
            name: Name to register the transformer under
            transformer_class: The transformer class to register

        Raises:
            TransformerRegistrationError: If the name is already registered or if the
                transformer_class is not a subclass of DataTransformer.
        """
        if name in cls._transformers:
            raise TransformerRegistrationError(
                f"Transformer name '{name}' is already registered",
                transformer_name=name,
                existing_class=cls._transformers[name],
            )

        if not issubclass(transformer_class, DataTransformer):
            raise TransformerRegistrationError(
                "Transformer class must be a subclass of DataTransformer",
                transformer_name=name,
            )

        cls._transformers[name] = transformer_class
        logger.info(f"Registered transformer '{name}'")

    @classmethod
    def create_transformer(cls, name: str, **kwargs: dict[str, Any]) -> DataTransformer:
        """Create a transformer instance by name.

        Args:
            name: Name of the registered transformer
            **kwargs: Arguments to pass to the transformer constructor

        Returns:
            DataTransformer: An instance of the requested transformer

        Raises:
            TransformerConfigurationError: If the transformer is not registered
        """
        if name not in cls._transformers:
            raise TransformerConfigurationError(
                f"No transformer registered with name '{name}'",
                transformer_name=name,
            )

        transformer_class = cls._transformers[name]
        transformer = transformer_class(**kwargs)
        logger.debug(f"Created transformer '{name}'")
        return transformer

    @classmethod
    def list_transformers(cls) -> list[str]:
        """List all registered transformer names.

        Returns:
            List[str]: List of registered transformer names
        """
        return list(cls._transformers.keys())

    @classmethod
    def get_transformer_class(cls, name: str) -> type[DataTransformer]:
        """Get a transformer class by name.

        Args:
            name: Name of the registered transformer

        Returns:
            Type[DataTransformer]: The requested transformer class

        Raises:
            TransformerConfigurationError: If the transformer is not registered
        """
        if name not in cls._transformers:
            raise TransformerConfigurationError(
                f"No transformer registered with name '{name}'",
                transformer_name=name,
            )

        return cls._transformers[name]

    @classmethod
    def discover_transformers(cls, package_name: str) -> None:
        """Discover and register all transformers in a package.

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
                        # Register snake_case alias without '_transformer'
                        snake = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
                        snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", snake).lower()
                        alias = snake.replace("_transformer", "")
                        if alias not in cls._transformers:
                            cls.register_transformer(alias, obj)

            logger.info(f"Discovered transformers from package '{package_name}'")

        except ImportError:
            logger.exception(f"Error discovering transformers from package '{package_name}'")

    @classmethod
    def create_composite_transformer(
        cls, transformer_names: list[str], **kwargs: dict[str, Any]
    ) -> DataTransformer:
        """Create a composite transformer from a list of transformer names.

        Args:
            transformer_names: List of registered transformer names to include in the pipeline
            **kwargs: Additional arguments to pass to individual transformers

        Returns:
            DataTransformer: A composite transformer containing the specified transformers

        Raises:
            ValueError: If any transformer name is not registered
        """
        from .base_transformer import CompositeTransformer

        # Use list comprehension for PERF401
        transformers = [cls.create_transformer(name, **kwargs) for name in transformer_names]

        return CompositeTransformer(transformers)
