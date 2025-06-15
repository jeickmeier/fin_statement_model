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

from fin_statement_model.config.helpers import cfg
from fin_statement_model.preprocessing.base_transformer import (
    CompositeTransformer,
    DataTransformer,
)
from fin_statement_model.preprocessing.errors import (
    TransformerConfigurationError,
    TransformerRegistrationError,
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
        """Register a transformer class with the factory.

        Args:
            name: Name to register the transformer under.
            transformer_class: Transformer class to register.

        Raises:
            TransformerRegistrationError: If a transformer with the given name is already registered or if the transformer_class is not a subclass of DataTransformer.
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
    def create_transformer(cls, name: str, **kwargs: Any) -> DataTransformer:
        """Create a transformer instance by its registered name.

        Args:
            name: Name of the registered transformer.
            **kwargs: Keyword arguments to pass to the transformer constructor.

        Returns:
            A DataTransformer instance.

        Raises:
            TransformerConfigurationError: If no transformer is registered under the given name.
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
            List of registered transformer names.
        """
        return list(cls._transformers.keys())

    @classmethod
    def get_transformer_class(cls, name: str) -> type[DataTransformer]:
        """Get a transformer class by its registered name.

        Args:
            name: Name of the registered transformer.

        Returns:
            Transformer class corresponding to the given name.

        Raises:
            TransformerConfigurationError: If no transformer is registered under the given name.
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

        Args:
            package_name: Full package path to scan for transformers.

        Raises:
            ImportError: If the specified package cannot be imported.
        """
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
        """Create a composite transformer from a list of transformer names.

        Args:
            transformer_names: List of transformer names to include in the composite.
            **kwargs: Keyword arguments to pass to each transformer constructor.

        Returns:
            CompositeTransformer instance combining the specified transformers.
        """
        transformers = [
            cls.create_transformer(name, **kwargs) for name in transformer_names
        ]
        return CompositeTransformer(transformers)


class TransformationService:
    """Service for managing and applying data transformations."""

    def __init__(self) -> None:
        """Initialize the transformation service."""
        logger.info("TransformationService initialized")

    def normalize_data(
        self,
        data: Union[pd.DataFrame, dict[str, Any]],
        normalization_type: Optional[str] = None,
        reference: Optional[str] = None,
        scale_factor: Optional[float] = None,
    ) -> Union[pd.DataFrame, dict[str, Any]]:
        """Normalize financial data.

        Args:
            data: DataFrame or dict of financial data to normalize.
            normalization_type: Type of normalization to apply.
            reference: Reference column for 'percent_of' normalization.
            scale_factor: Scale factor for 'scale_by' normalization.

        Returns:
            Normalized data of the same type as input.

        Raises:
            TransformerConfigurationError: If the normalization transformer is not registered.
            NormalizationError: If normalization fails due to invalid parameters or data.
        """
        # Determine normalization type default
        default_norm_type = cfg("preprocessing.default_normalization_type")
        norm_type = (
            normalization_type if normalization_type is not None else default_norm_type
        ) or "percent_of"
        transformer = TransformerFactory.create_transformer(
            "normalization",
            normalization_type=norm_type,
            reference=reference,
            scale_factor=scale_factor,
        )
        return transformer.execute(data)

    def transform_time_series(
        self,
        data: Union[pd.DataFrame, dict[str, Any]],
        transformation_type: Optional[str] = None,
        periods: Optional[int] = None,
        window_size: Optional[int] = None,
    ) -> Union[pd.DataFrame, dict[str, Any]]:
        """Apply time series transformations to financial data.

        Args:
            data: DataFrame or dict of financial data.
            transformation_type: Type of time series transformation to apply.
            periods: Number of periods for lag-based transformations.
            window_size: Window size for moving average calculations.

        Returns:
            Transformed data of the same type as input.

        Raises:
            TransformerConfigurationError: If the time series transformer is not registered.
            TimeSeriesError: If the transformation fails due to invalid parameters or data.
        """
        # Determine defaults from config
        default_transform_type = cfg("preprocessing.default_transformation_type")
        transform_type = (
            transformation_type
            if transformation_type is not None
            else default_transform_type
        )
        default_periods = cfg("preprocessing.default_time_series_periods")
        num_periods = periods if periods is not None else default_periods
        default_window = cfg("preprocessing.default_time_series_window_size")
        win_size = window_size if window_size is not None else default_window
        transformer = TransformerFactory.create_transformer(
            "time_series",
            transformation_type=transform_type,
            periods=num_periods,
            window_size=win_size,
        )
        return transformer.execute(data)

    def convert_periods(
        self,
        data: pd.DataFrame,
        conversion_type: str,
        aggregation: Optional[str] = None,
    ) -> pd.DataFrame:
        """Convert data between different reporting periods.

        Args:
            data: DataFrame with time-based data to convert.
            conversion_type: Conversion type (e.g., 'quarterly_to_annual').
            aggregation: Aggregation method (e.g., 'sum', 'mean', 'last').

        Returns:
            DataFrame with converted periods.

        Raises:
            TransformerConfigurationError: If the period conversion transformer is not registered.
            PeriodConversionError: If period conversion fails due to invalid data or parameters.
        """
        default_agg = cfg("preprocessing.default_conversion_aggregation")
        agg = aggregation if aggregation is not None else default_agg
        transformer = TransformerFactory.create_transformer(
            "period_conversion",
            conversion_type=conversion_type,
            aggregation=agg,
        )
        return transformer.execute(data)

    def format_statement(
        self,
        data: pd.DataFrame,
        statement_type: Optional[str] = None,
        add_subtotals: Optional[bool] = None,
        apply_sign_convention: Optional[bool] = None,
    ) -> pd.DataFrame:
        """Format a financial statement DataFrame.

        Args:
            data: DataFrame representing the statement to format.
            statement_type: Type of statement (e.g., 'income_statement').
            add_subtotals: Whether to include subtotal lines.
            apply_sign_convention: Whether to apply standard sign conventions.

        Returns:
            Formatted DataFrame with applied subtotals and sign conventions.

        Raises:
            TransformerConfigurationError: If the statement formatting transformer is not registered.
            PreprocessingError: If formatting fails due to invalid data or parameters.
        """
        # Determine defaults from preprocessing config
        stmt_cfg = cfg("preprocessing.statement_formatting")
        default_stmt_type = stmt_cfg.statement_type or "income_statement"
        stmt_type = statement_type if statement_type is not None else default_stmt_type
        default_add = (
            stmt_cfg.add_subtotals if hasattr(stmt_cfg, "add_subtotals") else True
        )
        sub = add_subtotals if add_subtotals is not None else default_add
        default_sign = (
            stmt_cfg.apply_sign_convention
            if hasattr(stmt_cfg, "apply_sign_convention")
            else True
        )
        sign = (
            apply_sign_convention if apply_sign_convention is not None else default_sign
        )
        transformer = TransformerFactory.create_transformer(
            "statement_formatting",
            statement_type=stmt_type,
            add_subtotals=sub,
            apply_sign_convention=sign,
        )
        return transformer.execute(data)

    def create_transformation_pipeline(
        self, transformers_config: list[dict[str, Any]]
    ) -> DataTransformer:
        """Create a composite transformer from configurations.

        Args:
            transformers_config: List of transformer configuration dictionaries, each containing a 'name' key and optional parameters.

        Returns:
            CompositeTransformer instance combining the specified transformers.

        Raises:
            ValueError: If any configuration dictionary is missing the 'name' key.
            TransformerConfigurationError: If transformer creation fails for a given name.
        """
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
        self, data: object, transformers_config: list[dict[str, Any]]
    ) -> object:
        """Apply a transformation pipeline to data.

        Args:
            data: Input data to transform.
            transformers_config: List of transformer configuration dictionaries.

        Returns:
            Transformed data after applying the pipeline.

        Raises:
            ValueError: If transformer configuration is invalid.
            TransformerConfigurationError: If transformer creation fails.
        """
        pipeline = self.create_transformation_pipeline(transformers_config)
        return pipeline.execute(data)

    def register_custom_transformer(
        self, name: str, transformer_class: type[DataTransformer]
    ) -> None:
        """Register a custom transformer with the factory.

        Args:
            name: Name under which to register the custom transformer.
            transformer_class: Custom transformer class to register.

        Raises:
            TransformerRegistrationError: If registration fails due to name conflicts or invalid class.
        """
        TransformerFactory.register_transformer(name, transformer_class)
        logger.info(f"Registered custom transformer: {name}")

    def list_available_transformers(self) -> list[str]:
        """List all available transformer types.

        Returns:
            List of transformer names registered in the factory.
        """
        return TransformerFactory.list_transformers()
