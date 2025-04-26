"""Transformation Service for the Financial Statement Model.

This module provides a high-level service for managing and applying data transformations.
"""

from typing import Optional, Union

import pandas as pd
import logging

from .base_transformer import DataTransformer, CompositeTransformer
from .transformer_factory import TransformerFactory

logger = logging.getLogger(__name__)


class TransformationService:
    """Service for managing and applying data transformations.

    This service separates data transformation logic from data processing,
    making it easier to maintain, test, and extend the codebase.

    It provides methods for common financial data transformations and allows
    for composing multiple transformations into pipelines.
    """

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
        """Normalize financial data.

        Args:
            data: The data to normalize (DataFrame or Dict)
            normalization_type: Type of normalization
            reference: Reference field for percent_of normalization
            scale_factor: Scale factor for scale_by normalization

        Returns:
            Normalized data
        """
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
        """Apply time series transformations to financial data.

        Args:
            data: The time series data to transform
            transformation_type: Type of transformation
            periods: Number of periods for calculations
            window_size: Window size for moving averages

        Returns:
            Transformed data
        """
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
        """Convert data between different period types.

        Args:
            data: DataFrame with time periods
            conversion_type: Type of period conversion
            aggregation: Aggregation method

        Returns:
            Transformed DataFrame with converted periods
        """
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
        """Format a financial statement DataFrame.

        Args:
            data: Financial statement data
            statement_type: Type of statement
            add_subtotals: Whether to add standard subtotals
            apply_sign_convention: Whether to apply sign conventions

        Returns:
            Formatted financial statement
        """
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
        """Create a composite transformer from a list of transformer configurations.

        Args:
            transformers_config: List of dicts with transformer configurations
                Each dict should have:
                - 'name': Name of the transformer
                - Additional configuration parameters for that transformer

        Returns:
            A composite transformer with the configured pipeline

        Example:
            config = [
                {'name': 'period_conversion', 'conversion_type': 'quarterly_to_annual'},
                {'name': 'normalization', 'normalization_type': 'percent_of', 'reference': 'revenue'}
            ]
            pipeline = service.create_transformation_pipeline(config)
            transformed_data = pipeline.execute(data)
        """
        transformers = []

        for config in transformers_config:
            if "name" not in config:
                raise ValueError("Each transformer configuration must have a 'name' field")

            name = config.pop("name")
            transformer = TransformerFactory.create_transformer(name, **config)
            transformers.append(transformer)

        return CompositeTransformer(transformers)

    def apply_transformation_pipeline(
        self, data: object, transformers_config: list[dict[str, object]]
    ) -> object:
        """Apply a transformation pipeline to data.

        Args:
            data: The data to transform
            transformers_config: List of transformer configurations

        Returns:
            Transformed data
        """
        pipeline = self.create_transformation_pipeline(transformers_config)
        return pipeline.execute(data)

    def register_custom_transformer(
        self, name: str, transformer_class: type[DataTransformer]
    ) -> None:
        """Register a custom transformer with the factory.

        Args:
            name: Name for the transformer
            transformer_class: The transformer class to register
        """
        TransformerFactory.register_transformer(name, transformer_class)
        logger.info(f"Registered custom transformer: {name}")

    def list_available_transformers(self) -> list[str]:
        """List all available transformer types.

        Returns:
            List of transformer names
        """
        return TransformerFactory.list_transformers()
