"""Provide TransformerFactory and TransformationService for preprocessing.

This module merges the transformer factory and transformation service into a single module for simplicity.
"""

import importlib
import inspect
import logging
import pkgutil
import re
from typing import Any, ClassVar, Optional, Union

import pandas as pd

from fin_statement_model.preprocessing.base_transformer import (
    DataTransformer,
    CompositeTransformer,
)
from fin_statement_model.preprocessing.errors import (
    TransformerRegistrationError,
    TransformerConfigurationError,
)

logger = logging.getLogger(__name__)


class TransformerFactory:
    """Create and manage transformer instances.

    Centralizes transformer registration, discovery, and instantiation.
    """

    _transformers: ClassVar[dict[str, type[DataTransformer]]] = {}

    @classmethod
    def register_transformer(
        cls, name: str, transformer_class: type[DataTransformer]
    ) -> None:
        """Register a transformer class with the factory."""
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
    def create_transformer(cls, name: str, **kwargs: Any) -> DataTransformer:
        """Create a transformer instance by name."""
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
        """List all registered transformer names."""
        return list(cls._transformers.keys())

    @classmethod
    def get_transformer_class(cls, name: str) -> type[DataTransformer]:
        """Get a transformer class by name."""
        if name not in cls._transformers:
            raise TransformerConfigurationError(
                f"No transformer registered with name '{name}'",
                transformer_name=name,
            )
        return cls._transformers[name]

    @classmethod
    def discover_transformers(cls, package_name: str) -> None:
        """Discover and register all transformers in a package."""
        try:
            package = importlib.import_module(package_name)
            package_path = package.__path__
            for _, module_name, _ in pkgutil.iter_modules(package_path):
                full_module_name = f"{package_name}.{module_name}"
                module = importlib.import_module(full_module_name)
                for obj_name, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj)
                        and issubclass(obj, DataTransformer)
                        and obj is not DataTransformer
                    ):
                        cls.register_transformer(obj_name, obj)
                        snake = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", obj_name)
                        snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", snake).lower()
                        alias = snake.replace("_transformer", "")
                        if alias not in cls._transformers:
                            cls.register_transformer(alias, obj)
            logger.info(f"Discovered transformers from package '{package_name}'")
        except ImportError:
            logger.exception(
                f"Error discovering transformers from package '{package_name}'"
            )

    @classmethod
    def create_composite_transformer(
        cls, transformer_names: list[str], **kwargs: Any
    ) -> DataTransformer:
        """Create a composite transformer from a list of transformer names."""
        transformers = [
            cls.create_transformer(name, **kwargs) for name in transformer_names
        ]
        return CompositeTransformer(transformers)


class TransformationService:
    """Service for managing and applying data transformations."""

    def __init__(self):
        """Initialize the transformation service."""
        logger.info("TransformationService initialized")

    def normalize_data(
        self,
        data: Union[pd.DataFrame, dict],
        normalization_type: str = "percent_of",
        reference: Optional[str] = None,
        scale_factor: Optional[float] = None,
    ) -> Union[pd.DataFrame, dict]:
        """Normalize financial data."""
        transformer = TransformerFactory.create_transformer(
            "normalization",
            normalization_type=normalization_type,
            reference=reference,
            scale_factor=scale_factor,
        )
        return transformer.execute(data)

    def transform_time_series(
        self,
        data: Union[pd.DataFrame, dict],
        transformation_type: str = "growth_rate",
        periods: int = 1,
        window_size: int = 3,
    ) -> Union[pd.DataFrame, dict]:
        """Apply time series transformations to financial data."""
        transformer = TransformerFactory.create_transformer(
            "time_series",
            transformation_type=transformation_type,
            periods=periods,
            window_size=window_size,
        )
        return transformer.execute(data)

    def convert_periods(
        self, data: pd.DataFrame, conversion_type: str, aggregation: str = "sum"
    ) -> pd.DataFrame:
        """Convert data between different period types."""
        transformer = TransformerFactory.create_transformer(
            "period_conversion",
            conversion_type=conversion_type,
            aggregation=aggregation,
        )
        return transformer.execute(data)

    def format_statement(
        self,
        data: pd.DataFrame,
        statement_type: str = "income_statement",
        add_subtotals: bool = True,
        apply_sign_convention: bool = True,
    ) -> pd.DataFrame:
        """Format a financial statement DataFrame."""
        transformer = TransformerFactory.create_transformer(
            "statement_formatting",
            statement_type=statement_type,
            add_subtotals=add_subtotals,
            apply_sign_convention=apply_sign_convention,
        )
        return transformer.execute(data)

    def create_transformation_pipeline(
        self, transformers_config: list[dict[str, object]]
    ) -> DataTransformer:
        """Create a composite transformer from configurations."""
        transformers = []
        for config in transformers_config:
            if "name" not in config:
                raise ValueError(
                    "Each transformer configuration must have a 'name' field"
                )
            name = config.pop("name")
            transformer = TransformerFactory.create_transformer(name, **config)
            transformers.append(transformer)
        return CompositeTransformer(transformers)

    def apply_transformation_pipeline(
        self, data: object, transformers_config: list[dict[str, object]]
    ) -> object:
        """Apply a transformation pipeline to data."""
        pipeline = self.create_transformation_pipeline(transformers_config)
        return pipeline.execute(data)

    def register_custom_transformer(
        self, name: str, transformer_class: type[DataTransformer]
    ) -> None:
        """Register a custom transformer with the factory."""
        TransformerFactory.register_transformer(name, transformer_class)
        logger.info(f"Registered custom transformer: {name}")

    def list_available_transformers(self) -> list[str]:
        """List all available transformer types."""
        return TransformerFactory.list_transformers()
