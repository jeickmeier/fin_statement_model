"""Define custom exception classes for the preprocessing package.

This module provides specific error types for data preprocessing,
transformation, and validation operations in the preprocessing layer.

Exception Hierarchy:
    - PreprocessingError (base for all preprocessing errors)
        - TransformerRegistrationError
        - TransformerConfigurationError
        - PeriodConversionError
        - NormalizationError
        - TimeSeriesError

All exceptions inherit from FinancialModelError or TransformationError in core.errors.

Examples:
    Raise a normalization error:

    >>> from fin_statement_model.preprocessing.errors import NormalizationError
    >>> raise NormalizationError("Reference column missing", method="percent_of", reference_field="revenue")
    Traceback (most recent call last):
        ...
    NormalizationError: Reference column missing

    Catch a period conversion error:

    >>> from fin_statement_model.preprocessing.errors import PeriodConversionError
    >>> try:
    ...     raise PeriodConversionError("Invalid period", source_period="Q", target_period="A")
    ... except PeriodConversionError as e:
    ...     print(e)
    Invalid period
"""

from typing import Any

from fin_statement_model.core.errors import (
    FinancialModelError,
    TransformationError,
)

__all__ = [
    "NormalizationError",
    "PeriodConversionError",
    "PreprocessingError",
    "TimeSeriesError",
    "TransformerConfigurationError",
    "TransformerRegistrationError",
]


class PreprocessingError(FinancialModelError):
    """Base exception for all preprocessing-related errors.

    All errors in the preprocessing layer should inherit from this class.

    Examples:
        >>> from fin_statement_model.preprocessing.errors import PreprocessingError
        >>> raise PreprocessingError("General preprocessing error")
        Traceback (most recent call last):
            ...
        PreprocessingError: General preprocessing error
    """


class TransformerRegistrationError(PreprocessingError):
    """Exception raised for transformer registration issues.

    This includes attempts to register duplicate transformers or
    register invalid transformer classes.

    Args:
        message: The primary error message.
        transformer_name: Optional name of the transformer.
        existing_class: Optional existing class that's already registered.

    Examples:
        >>> from fin_statement_model.preprocessing.errors import TransformerRegistrationError
        >>> raise TransformerRegistrationError("Duplicate", transformer_name="MyTransformer")
        Traceback (most recent call last):
            ...
        TransformerRegistrationError: Duplicate for transformer 'MyTransformer'
    """

    def __init__(
        self,
        message: str,
        transformer_name: str | None = None,
        existing_class: type | None = None,
    ):
        """Initialize the TransformerRegistrationError."""
        self.transformer_name = transformer_name
        self.existing_class = existing_class

        full_message = message
        if transformer_name:
            full_message = f"{message} for transformer '{transformer_name}'"
        if existing_class:
            full_message = f"{full_message} (already registered as {existing_class.__name__})"

        super().__init__(full_message)


class TransformerConfigurationError(PreprocessingError):
    """Exception raised for invalid transformer configuration.

    This includes missing required parameters, invalid parameter values,
    or incompatible configuration options.

    Args:
        message: The primary error message.
        transformer_name: Optional name of the transformer.
        config: Optional configuration dictionary that caused the error.
        missing_params: Optional list of missing required parameters.

    Examples:
        >>> from fin_statement_model.preprocessing.errors import TransformerConfigurationError
        >>> raise TransformerConfigurationError(
        ...     "Missing config", transformer_name="Normalizer", missing_params=["reference"]
        ... )
        Traceback (most recent call last):
            ...
        TransformerConfigurationError: Missing config (Transformer: Normalizer; Missing params: reference)
    """

    def __init__(
        self,
        message: str,
        transformer_name: str | None = None,
        config: dict[str, Any] | None = None,
        missing_params: list[str] | None = None,
    ):
        """Initialize the TransformerConfigurationError."""
        self.transformer_name = transformer_name
        self.config = config
        self.missing_params = missing_params or []

        details = []
        if transformer_name:
            details.append(f"Transformer: {transformer_name}")
        if missing_params:
            details.append(f"Missing params: {', '.join(missing_params)}")

        full_message = message
        if details:
            full_message = f"{message} ({'; '.join(details)})"

        super().__init__(full_message)


class PeriodConversionError(TransformationError):
    """Exception raised for period conversion failures.

    This includes invalid period formats, unsupported conversion types,
    or missing date/period columns.

    Args:
        message: The primary error message.
        source_period: Optional source period type.
        target_period: Optional target period type.
        date_column: Optional name of the date column.

    Examples:
        >>> from fin_statement_model.preprocessing.errors import PeriodConversionError
        >>> raise PeriodConversionError("Invalid period", source_period="Q", target_period="A")
        Traceback (most recent call last):
            ...
        PeriodConversionError: Invalid period
    """

    def __init__(
        self,
        message: str,
        source_period: str | None = None,
        target_period: str | None = None,
        date_column: str | None = None,
    ):
        """Initialize the PeriodConversionError."""
        self.source_period = source_period
        self.target_period = target_period
        self.date_column = date_column

        details: dict[str, Any] = {}
        if source_period and target_period:
            details["conversion"] = f"{source_period} -> {target_period}"
        if date_column:
            details["date_column"] = date_column

        super().__init__(
            message,
            transformer_type="PeriodConversionTransformer",
            parameters=details,
        )


class NormalizationError(TransformationError):
    """Exception raised for normalization failures.

    This includes missing reference columns, invalid normalization methods,
    or data type incompatibilities.

    Args:
        message: The primary error message.
        method: Optional normalization method.
        reference_field: Optional reference field for percent_of method.
        scale_factor: Optional scale factor for scale_by method.

    Examples:
        >>> from fin_statement_model.preprocessing.errors import NormalizationError
        >>> raise NormalizationError("Reference missing", method="percent_of", reference_field="revenue")
        Traceback (most recent call last):
            ...
        NormalizationError: Reference missing
    """

    def __init__(
        self,
        message: str,
        method: str | None = None,
        reference_field: str | None = None,
        scale_factor: float | None = None,
    ):
        """Initialize the NormalizationError."""
        self.method = method
        self.reference_field = reference_field
        self.scale_factor = scale_factor

        params: dict[str, Any] = {}
        if method:
            params["method"] = method
        if reference_field:
            params["reference"] = reference_field
        if scale_factor is not None:
            params["scale_factor"] = scale_factor

        super().__init__(
            message,
            transformer_type="NormalizationTransformer",
            parameters=params,
        )


class TimeSeriesError(TransformationError):
    """Exception raised for time series transformation failures.

    This includes invalid window sizes, missing columns, or
    incompatible aggregation methods.

    Args:
        message: The primary error message.
        operation: Optional operation type (e.g., 'rolling_mean', 'lag').
        window_size: Optional window size parameter.
        column: Optional column being processed.

    Examples:
        >>> from fin_statement_model.preprocessing.errors import TimeSeriesError
        >>> raise TimeSeriesError("Invalid window", operation="moving_avg", window_size=3)
        Traceback (most recent call last):
            ...
        TimeSeriesError: Invalid window
    """

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        window_size: int | None = None,
        column: str | None = None,
    ):
        """Initialize the TimeSeriesError."""
        self.operation = operation
        self.window_size = window_size
        self.column = column

        params: dict[str, Any] = {}
        if operation:
            params["operation"] = operation
        if window_size is not None:
            params["window_size"] = window_size
        if column:
            params["column"] = column

        super().__init__(
            message,
            transformer_type="TimeSeriesTransformer",
            parameters=params,
        )
