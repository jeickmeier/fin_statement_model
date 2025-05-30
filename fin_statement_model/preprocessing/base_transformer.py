"""Define base DataTransformer interface for preprocessing layer.

This module provides the DataTransformer abstract base class and CompositeTransformer.
"""

from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional, Union
import logging

from fin_statement_model.core.errors import TransformationError

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
    def transform(self, data: Union[pd.DataFrame, pd.Series]) -> Union[pd.DataFrame, pd.Series]:
        """Transform the input data.

        Args:
            data: The data to transform.

        Returns:
            The transformed data.

        Raises:
            TransformationError: If transformation fails.
        """
        try:
            self.logger.debug(f"Transforming data with {self.__class__.__name__}")
            return self._transform_impl(data)
        except Exception as e:
            self.logger.exception(f"Error transforming data with {self.__class__.__name__}")
            raise TransformationError(
                "Error transforming data",
                transformer_type=self.__class__.__name__,
            ) from e

    def validate_input(self, data: object) -> bool:
        """Validate that the input data is a pandas DataFrame by default.

        This performs a basic DataFrame type check and can be overridden by subclasses with more specific validation logic.

        Args:
            data (object): The input data to validate.

        Returns:
            bool: True if data is a pandas.DataFrame, False otherwise.
        """
        return isinstance(data, pd.DataFrame)

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

    def validate_config(self) -> None:
        """Validate the transformer configuration.

        This method can be overridden by subclasses to add specific validation logic.

        Raises:
            TransformationError: If the configuration is invalid.
        """
        if self.config is None:
            raise TransformationError(
                f"Invalid input data for {self.__class__.__name__}",
                transformer_type=self.__class__.__name__,
            )


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
        """Validate input for the composite transformer.

        If the pipeline is empty, accepts any data; otherwise, delegates validation to the first transformer.

        Args:
            data (object): Input data to validate.

        Returns:
            bool: True if input is valid for the pipeline.
        """
        if not hasattr(self, "transformers") or not self.transformers:
            return True
        return self.transformers[0].validate_input(data)
