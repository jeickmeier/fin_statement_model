"""Define the base DataTransformer interface for the preprocessing layer.

This module provides the DataTransformer abstract base class and CompositeTransformer
for building and composing data transformation pipelines. The design follows the
Strategy pattern, allowing different transformation algorithms to be encapsulated
in separate classes while sharing a common interface.

Examples:
    Create a simple transformer:

    >>> class UppercaseTransformer(DataTransformer):
    ...     def _transform_impl(self, data):
    ...         return data.str.upper()
    ...
    ...     def validate_input(self, data):
    ...         return isinstance(data, (pd.Series, pd.DataFrame))

    Create a composite pipeline:

    >>> uppercase = UppercaseTransformer()
    >>> pipeline = CompositeTransformer([uppercase])
    >>> result = pipeline.execute(pd.Series(["a", "b", "c"]))
    >>> print(result)
    0    A
    1    B
    2    C
    dtype: object
"""

# ---------------------------------------------------------------------------
# Future imports - must appear immediately after the module docstring.
# ---------------------------------------------------------------------------

from __future__ import annotations

# The *annotations* future postpones evaluation of type hints to runtime. This
# prevents ``TypeError: 'Series' is not subscriptable`` errors on older pandas
# versions that don't support subscripted generics while still letting static
# type checkers see the full `pd.Series[Any]` information.
# ---------------------------------------------------------------------------
# Standard library & third-party imports
# ---------------------------------------------------------------------------
from abc import ABC, abstractmethod
import logging
from typing import TYPE_CHECKING, Any, cast

from fin_statement_model.core.errors import TransformationError

# Delegate Series/DataFrame coercion to shared utility
from fin_statement_model.preprocessing.utils import ensure_dataframe

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)

# PEP 563/PEP 649: Postpone evaluation of type annotations to **runtime** (they
# remain as strings until explicitly evaluated). This prevents errors when
# subscripted generics like ``pd.Series[Any]`` are used with pandas versions
# that do not yet support them as proper generic aliases.


class DataTransformer(ABC):
    """Define base class for data transformers.

    The DataTransformer class provides a common interface for all data transformation
    operations in the preprocessing layer. It follows the Template Method pattern,
    defining the skeleton of the transformation algorithm in the execute() method
    while letting subclasses override specific steps.

    Key Features:
        - Configuration management via __init__
        - Pre/post transformation hooks
        - Input validation
        - Error handling and logging
        - Support for both DataFrame and Series inputs

    The transformation workflow is:
        1. validate_input() - Check if input data is valid
        2. _pre_transform_hook() - Optional preprocessing
        3. transform() - Core transformation logic
        4. _post_transform_hook() - Optional postprocessing

    Examples:
        Create a simple transformer that adds a constant:

        >>> class AddConstantTransformer(DataTransformer):
        ...     def __init__(self, constant=1):
        ...         super().__init__({"constant": constant})
        ...         self.constant = constant
        ...
        ...     def _transform_impl(self, data):
        ...         return data + self.constant
        ...
        ...     def validate_input(self, data):
        ...         return isinstance(data, (pd.Series, pd.DataFrame))
        >>> transformer = AddConstantTransformer(constant=5)
        >>> result = transformer.execute(pd.Series([1, 2, 3]))
        >>> print(result)
        0    6
        1    7
        2    8
        dtype: int64

    Notes:
        - Subclasses must implement _transform_impl() and validate_input()
        - The execute() method orchestrates the complete transformation pipeline
        - Use pre/post hooks for setup/cleanup rather than overriding execute()
    """

    def __init__(self, config: dict[str, object] | None = None):
        """Initialize the transformer with optional configuration.

        The config dictionary can contain any parameters needed by the transformer.
        These parameters are stored and can be validated via validate_config().

        Args:
            config: Optional configuration dictionary for the transformer.
                   Common keys might include:
                   - 'input_columns': List of columns to transform
                   - 'output_format': Desired output format
                   - 'parameters': Algorithm-specific parameters

        Examples:
            >>> transformer = DataTransformer({"scale": 2.0, "offset": 1.0})
            >>> transformer.config
            {'scale': 2.0, 'offset': 1.0}
        """
        self.config = config or {}
        logger.debug(
            "Initialized %s with config: %s",
            self.__class__.__name__,
            self.config,
        )

    def transform(self, data: pd.DataFrame | pd.Series[Any]) -> pd.DataFrame | pd.Series[Any]:
        """Transform the input data.

        This is the main public interface for transformation. It wraps the internal
        _transform_impl() method with error handling and logging.

        Args:
            data: The data to transform. Can be either:
                - pandas.DataFrame: For multi-column transformations
                - pandas.Series: For single-column transformations

        Returns:
            The transformed data, maintaining the same type as the input
            (DataFrame → DataFrame, Series → Series).

        Raises:
            TransformationError: If any step of the transformation fails.
                The error will include:
                - The transformer type that failed
                - The original exception as context
                - Any relevant parameters

        Examples:
            >>> df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
            >>> transformer = MyTransformer()
            >>> try:
            ...     result = transformer.transform(df)
            ... except TransformationError as e:
            ...     print(f"Transform failed: {e}")
        """
        try:
            logger.debug("Transforming data with %s", self.__class__.__name__)
            return self._transform_impl(data)
        except Exception as e:
            logger.exception("Error transforming data with %s", self.__class__.__name__)
            raise TransformationError(
                "Error transforming data",
                transformer_type=self.__class__.__name__,
            ) from e

    @abstractmethod
    def _transform_impl(self, data: pd.DataFrame | pd.Series[Any]) -> pd.DataFrame | pd.Series[Any]:
        """Apply the transformation logic.

        This is the core method that subclasses must implement to define their
        specific transformation algorithm.

        Args:
            data: The data to transform. Will be either:
                - pandas.DataFrame: For multi-column transformations
                - pandas.Series: For single-column transformations

        Returns:
            The transformed data, maintaining the same type as the input.

        Raises:
            TransformationError: If the transformation fails.

        Examples:
            Implementation for a scaling transformer:

            >>> def _transform_impl(self, data):
            ...     scale = self.config.get("scale", 1.0)
            ...     return data * scale
        """

    @abstractmethod
    def validate_input(self, data: object) -> bool:
        """Return *True* if *data* is valid for this transformer.

        This method defines the contract for what kind of data the transformer
        can handle. Subclasses must implement this to specify their input
        requirements.

        Args:
            data: The data to validate, typically one of:
                - pandas.DataFrame
                - pandas.Series
                - numpy.ndarray
                - Other domain-specific types

        Returns:
            bool: True if the data is valid for this transformer.

        Examples:
            Validate only numeric DataFrames:

            >>> def validate_input(self, data):
            ...     if not isinstance(data, pd.DataFrame):
            ...         return False
            ...     return data.select_dtypes(include=["number"]).shape[1] > 0

            Accept both Series and DataFrame:

            >>> def validate_input(self, data):
            ...     return isinstance(data, (pd.Series, pd.DataFrame))
        """

    def _pre_transform_hook(self, data: object) -> object:
        """Hook method called before transformation.

        This hook allows subclasses to perform setup or preprocessing without
        overriding the main execute() method. Common uses include:
        - Data type conversion
        - Missing value handling
        - Input validation
        - Resource allocation

        Args:
            data: The input data to preprocess

        Returns:
            Processed data to be passed to the transform method

        Examples:
            Handle missing values:

            >>> def _pre_transform_hook(self, data):
            ...     if isinstance(data, pd.DataFrame):
            ...         return data.fillna(0)
            ...     return data
        """
        return data

    def _post_transform_hook(self, data: object) -> object:
        """Hook method called after transformation.

        This hook allows subclasses to perform cleanup or post-processing without
        overriding the main execute() method. Common uses include:
        - Result validation
        - Format conversion
        - Resource cleanup
        - Logging/metrics collection

        Args:
            data: The transformed data to post-process

        Returns:
            Final processed data

        Examples:
            Round numeric results:

            >>> def _post_transform_hook(self, data):
            ...     if isinstance(data, pd.DataFrame):
            ...         return data.round(decimals=2)
            ...     return data
        """
        return data

    def execute(self, data: object) -> object:
        """Execute the complete transformation pipeline.

        This method orchestrates the entire transformation process:
        1. Validates the input data
        2. Applies pre-transformation hook
        3. Performs the core transformation
        4. Applies post-transformation hook
        5. Handles any errors

        Args:
            data: The input data to transform. The type must be compatible
                 with what validate_input() accepts.

        Returns:
            The fully transformed and processed data.

        Raises:
            ValueError: If the data is invalid or any step fails.

        Examples:
            >>> transformer = MyTransformer({"scale": 2.0})
            >>> try:
            ...     result = transformer.execute(pd.DataFrame({"A": [1, 2, 3]}))
            ... except ValueError as e:
            ...     print(f"Transformation failed: {e}")
        """
        if not self.validate_input(data):
            raise ValueError(f"Invalid input data for {self.__class__.__name__}")

        try:
            # Apply pre-transform hook
            processed_data = self._pre_transform_hook(data)

            # Perform transformation with explicit type cast for static type checker
            result = self.transform(cast("pd.DataFrame | pd.Series[Any]", processed_data))
            result = cast("pd.DataFrame | pd.Series[Any]", self._post_transform_hook(result))
            logger.debug("Successfully transformed data with %s", self.__class__.__name__)
        except Exception as e:
            # Don't log here - transform() already logs exceptions
            raise ValueError("Error transforming data") from e
        else:
            return result

    def validate_config(self) -> None:
        """Validate the transformer configuration.

        This method verifies that the configuration provided to __init__
        is valid for this transformer. Subclasses should override this to
        add specific validation rules.

        Raises:
            TransformationError: If the configuration is invalid.

        Examples:
            Validate required config parameters:

            >>> def validate_config(self):
            ...     super().validate_config()  # Always call parent
            ...     if "scale_factor" not in self.config:
            ...         raise TransformationError(
            ...             "Missing required config 'scale_factor'", transformer_type=self.__class__.__name__
            ...         )
        """
        if self.config is None:
            raise TransformationError(
                f"Invalid input data for {self.__class__.__name__}",
                transformer_type=self.__class__.__name__,
            )

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _coerce_to_dataframe(
        data: pd.DataFrame | pd.Series[Any],
    ) -> tuple[pd.DataFrame, bool]:
        """Return ``(df, was_series)`` ensuring *data* is a DataFrame.

        This method is **deprecated** and will be removed in a future release.
        It now simply delegates to :func:`fin_statement_model.preprocessing.utils.ensure_dataframe`.
        """
        # Delegation keeps backward-compatibility without duplicating logic.
        return ensure_dataframe(data)


class CompositeTransformer(DataTransformer):
    """Compose multiple transformers into a pipeline.

    The CompositeTransformer implements the Composite pattern, allowing
    multiple transformers to be treated as a single transformer. This enables
    building complex transformation pipelines from simple components.

    Key Features:
        - Sequential application of transformers
        - Dynamic pipeline modification (add/remove)
        - Unified configuration
        - Automatic input validation propagation

    Examples:
        Create a pipeline that scales then normalizes:

        >>> scale = ScaleTransformer(scale_factor=0.001)  # Scale to thousands
        >>> normalize = NormalizationTransformer(method="percent_of", ref="revenue")
        >>> pipeline = CompositeTransformer([scale, normalize])
        >>> result = pipeline.execute(df)

        Dynamically modify the pipeline:

        >>> moving_avg = MovingAverageTransformer(window=3)
        >>> pipeline.add_transformer(moving_avg)
        >>> pipeline.remove_transformer(0)  # Remove scaling
    """

    def __init__(
        self,
        transformers: list[DataTransformer],
        config: dict[str, object] | None = None,
    ):
        """Initialize with a list of transformers.

        Args:
            transformers: List of transformers to apply in sequence. Each
                        transformer must be an instance of DataTransformer.
            config: Optional configuration dictionary that applies to the
                   entire pipeline.

        Examples:
            >>> t1 = ScaleTransformer(scale_factor=0.001)
            >>> t2 = NormalizationTransformer(method="percent_of", ref="revenue")
            >>> pipeline = CompositeTransformer(transformers=[t1, t2], config={"name": "scale_and_normalize"})
        """
        super().__init__(config)
        self.transformers = transformers

    def _transform_impl(self, data: pd.DataFrame | pd.Series[Any]) -> pd.DataFrame | pd.Series[Any]:
        """Apply each transformer in sequence.

        This implementation follows the Composite pattern, delegating to
        each transformer in the pipeline while maintaining error handling
        and type consistency.

        Args:
            data: The input data to transform

        Returns:
            Data transformed by the complete pipeline

        Examples:
            >>> pipeline = CompositeTransformer([
            ...     ScaleTransformer(scale_factor=0.001),
            ...     NormalizationTransformer(method="percent_of", ref="revenue"),
            ... ])
            >>> result = pipeline._transform_impl(df)
        """
        result: pd.DataFrame | pd.Series[Any] = data
        for transformer in self.transformers:
            result = cast("pd.DataFrame | pd.Series[Any]", transformer.execute(result))
        return result

    def add_transformer(self, transformer: DataTransformer) -> None:
        """Add a transformer to the pipeline.

        This method allows dynamic extension of the transformation pipeline.
        New transformers are added to the end of the sequence.

        Args:
            transformer: The transformer to add. Must be an instance of
                       DataTransformer.

        Examples:
            >>> pipeline = CompositeTransformer([])
            >>> pipeline.add_transformer(ScaleTransformer(scale_factor=0.001))
            >>> pipeline.add_transformer(NormalizationTransformer(method="percent_of", ref="revenue"))
        """
        self.transformers.append(transformer)

    def remove_transformer(self, index: int) -> DataTransformer | None:
        """Remove a transformer from the pipeline.

        This method allows dynamic modification of the transformation pipeline
        by removing transformers at specific positions.

        Args:
            index: Index of the transformer to remove (0-based)

        Returns:
            The removed transformer or None if index is invalid

        Examples:
            >>> pipeline = CompositeTransformer([
            ...     ScaleTransformer(scale_factor=0.001),
            ...     NormalizationTransformer(method="percent_of", ref="revenue"),
            ... ])
            >>> removed = pipeline.remove_transformer(0)  # Remove scaling
            >>> isinstance(removed, ScaleTransformer)
            True
        """
        if 0 <= index < len(self.transformers):
            return self.transformers.pop(index)
        return None

    def validate_input(self, data: object) -> bool:
        """Validate input for the composite transformer.

        For a composite transformer, input validation is delegated to the
        first transformer in the pipeline (if any exist). This ensures that
        the initial data format matches what the pipeline expects.

        Args:
            data: Input data to validate.

        Returns:
            bool: True if the pipeline is empty or if the first transformer
                 accepts the input.

        Examples:
            >>> pipeline = CompositeTransformer([
            ...     ScaleTransformer(scale_factor=0.001)  # Accepts DataFrame only
            ... ])
            >>> pipeline.validate_input(pd.DataFrame({"A": [1, 2, 3]}))
            True
            >>> pipeline.validate_input(pd.Series([1, 2, 3]))
            False
        """
        if not hasattr(self, "transformers") or not self.transformers:
            return True
        return self.transformers[0].validate_input(data)
