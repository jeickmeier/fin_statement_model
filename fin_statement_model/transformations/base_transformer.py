"""
Base transformer for the Financial Statement Model.

This module provides the base interface for data transformations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging

# Configure logging
logger = logging.getLogger(__name__)


class DataTransformer(ABC):
    """
    Base class for all data transformers.

    Data transformers are responsible for converting data between different formats
    and applying business rules to prepare data for different use cases.

    This separation of transformations from data processing follows the Single
    Responsibility Principle and makes the code more maintainable and extensible.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the transformer with optional configuration.

        Args:
            config: Optional configuration dictionary for the transformer
        """
        self.config = config or {}
        logger.debug(
            f"Initialized {self.__class__.__name__} with config: {self.config}"
        )

    @abstractmethod
    def transform(self, data: Any) -> Any:
        """
        Transform the input data.

        Args:
            data: The input data to transform

        Returns:
            Transformed data

        Raises:
            ValueError: If the data cannot be transformed
        """
        pass

    def validate_input(self, data: Any) -> bool:
        """
        Validate that the input data is acceptable for this transformer.

        Args:
            data: The input data to validate

        Returns:
            bool: True if the data is valid, False otherwise

        This method should be overridden by subclasses that need
        specific validation logic.
        """
        return True

    def _pre_transform_hook(self, data: Any) -> Any:
        """
        Hook method called before transformation.

        Args:
            data: The input data

        Returns:
            Processed data to be passed to the transform method

        This method can be overridden by subclasses to add pre-processing steps.
        """
        return data

    def _post_transform_hook(self, data: Any) -> Any:
        """
        Hook method called after transformation.

        Args:
            data: The transformed data

        Returns:
            Final processed data

        This method can be overridden by subclasses to add post-processing steps.
        """
        return data

    def execute(self, data: Any) -> Any:
        """
        Execute the complete transformation pipeline.

        Args:
            data: The input data to transform

        Returns:
            Transformed data

        Raises:
            ValueError: If the data is invalid or cannot be transformed
        """
        if not self.validate_input(data):
            raise ValueError(f"Invalid input data for {self.__class__.__name__}")

        try:
            # Apply pre-transform hook
            processed_data = self._pre_transform_hook(data)

            # Perform transformation
            transformed_data = self.transform(processed_data)

            # Apply post-transform hook
            result = self._post_transform_hook(transformed_data)

            logger.debug(
                f"Successfully transformed data with {self.__class__.__name__}"
            )
            return result

        except Exception as e:
            logger.error(f"Error transforming data with {self.__class__.__name__}: {e}")
            raise ValueError(f"Error transforming data: {e}")


class CompositeTransformer(DataTransformer):
    """
    A transformer that composes multiple transformers into a pipeline.

    This allows for creating complex transformation chains while
    maintaining the single responsibility of each individual transformer.
    """

    def __init__(
        self, transformers: List[DataTransformer], config: Optional[Dict] = None
    ):
        """
        Initialize with a list of transformers.

        Args:
            transformers: List of transformers to apply in sequence
            config: Optional configuration dictionary
        """
        super().__init__(config)
        self.transformers = transformers

    def transform(self, data: Any) -> Any:
        """
        Apply each transformer in sequence.

        Args:
            data: The input data to transform

        Returns:
            Data transformed by the pipeline
        """
        result = data
        for transformer in self.transformers:
            result = transformer.execute(result)
        return result

    def add_transformer(self, transformer: DataTransformer) -> None:
        """
        Add a transformer to the pipeline.

        Args:
            transformer: The transformer to add
        """
        self.transformers.append(transformer)

    def remove_transformer(self, index: int) -> Optional[DataTransformer]:
        """
        Remove a transformer from the pipeline.

        Args:
            index: Index of the transformer to remove

        Returns:
            The removed transformer or None if index is invalid
        """
        if 0 <= index < len(self.transformers):
            return self.transformers.pop(index)
        return None
