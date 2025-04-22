"""Define base DataTransformer interface for preprocessing layer.

This module provides the DataTransformer abstract base class and CompositeTransformer.
"""

from abc import ABC, abstractmethod
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DataTransformer(ABC):
    """Define base class for data transformers.

    Data transformers convert data between formats and apply business rules.

    This separation follows the Single Responsibility Principle for maintainability.
    """

    def __init__(self, config: Optional[dict[str, object]] = None):
        """Initialize the transformer with optional configuration.

        Args:
            config: Optional configuration dictionary for the transformer
        """
        self.config = config or {}
        logger.debug(f"Initialized {self.__class__.__name__} with config: {self.config}")

    @abstractmethod
    def transform(self, data: object) -> object:
        """Transform the input data.

        Args:
            data: The input data to transform

        Returns:
            Transformed data

        Raises:
            ValueError: If the data cannot be transformed
        """

    def validate_input(self, data: object) -> bool:
        """Validate that the input data is acceptable for this transformer.

        This method must be overridden by subclasses with custom validation logic.

        Raises:
            NotImplementedError: if not implemented in subclass
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement validate_input()")

    def _pre_transform_hook(self, data: object) -> object:
        """Hook method called before transformation.

        Args:
            data: The input data

        Returns:
            Processed data to be passed to the transform method

        This method can be overridden by subclasses to add pre-processing steps.
        """
        return data

    def _post_transform_hook(self, data: object) -> object:
        """Hook method called after transformation.

        Args:
            data: The transformed data

        Returns:
            Final processed data

        This method can be overridden by subclasses to add post-processing steps.
        """
        return data

    def execute(self, data: object) -> object:
        """Execute the complete transformation pipeline.

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
            result = self.transform(processed_data)
            result = self._post_transform_hook(result)
            logger.debug(f"Successfully transformed data with {self.__class__.__name__}")
        except Exception as e:
            logger.exception(f"Error transforming data with {self.__class__.__name__}")
            raise ValueError("Error transforming data") from e
        else:
            return result


class CompositeTransformer(DataTransformer):
    """Compose multiple transformers into a pipeline.

    This allows building complex transformation chains from simple steps.
    """

    def __init__(self, transformers: list[DataTransformer], config: Optional[dict] = None):
        """Initialize with a list of transformers.

        Args:
            transformers: List of transformers to apply in sequence
            config: Optional configuration dictionary
        """
        super().__init__(config)
        self.transformers = transformers

    def transform(self, data: object) -> object:
        """Apply each transformer in sequence.

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
        """Add a transformer to the pipeline.

        Args:
            transformer: The transformer to add
        """
        self.transformers.append(transformer)

    def remove_transformer(self, index: int) -> Optional[DataTransformer]:
        """Remove a transformer from the pipeline.

        Args:
            index: Index of the transformer to remove

        Returns:
            The removed transformer or None if index is invalid
        """
        if 0 <= index < len(self.transformers):
            return self.transformers.pop(index)
        return None

    def validate_input(self, data: object) -> bool:
        """CompositeTransformer always accepts data; individual transformers validate."""
        return True
