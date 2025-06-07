"""Custom Exception classes for the preprocessing package.

These exceptions provide specific error information related to data
preprocessing, transformation, and validation operations.
"""

from typing import Optional, Any
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
    """Base exception for all preprocessing-related errors."""


class TransformerRegistrationError(PreprocessingError):
    """Exception raised for transformer registration issues.

    This includes attempts to register duplicate transformers or
    register invalid transformer classes.
    """

    def __init__(
        self,
        message: str,
        transformer_name: Optional[str] = None,
        existing_class: Optional[type] = None,
    ):
        """Initialize a TransformerRegistrationError.

        Args:
            message: The primary error message.
            transformer_name: Optional name of the transformer.
            existing_class: Optional existing class that's already registered.
        """
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
    """

    def __init__(
        self,
        message: str,
        transformer_name: Optional[str] = None,
        config: Optional[dict[str, Any]] = None,
        missing_params: Optional[list[str]] = None,
    ):
        """Initialize a TransformerConfigurationError.

        Args:
            message: The primary error message.
            transformer_name: Optional name of the transformer.
            config: Optional configuration dictionary that caused the error.
            missing_params: Optional list of missing required parameters.
        """
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
    """

    def __init__(
        self,
        message: str,
        source_period: Optional[str] = None,
        target_period: Optional[str] = None,
        date_column: Optional[str] = None,
    ):
        """Initialize a PeriodConversionError.

        Args:
            message: The primary error message.
            source_period: Optional source period type.
            target_period: Optional target period type.
            date_column: Optional name of the date column.
        """
        self.source_period = source_period
        self.target_period = target_period
        self.date_column = date_column

        details = {}
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
    """

    def __init__(
        self,
        message: str,
        method: Optional[str] = None,
        reference_field: Optional[str] = None,
        scale_factor: Optional[float] = None,
    ):
        """Initialize a NormalizationError.

        Args:
            message: The primary error message.
            method: Optional normalization method.
            reference_field: Optional reference field for percent_of method.
            scale_factor: Optional scale factor for scale_by method.
        """
        self.method = method
        self.reference_field = reference_field
        self.scale_factor = scale_factor

        params = {}
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
    """

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        window_size: Optional[int] = None,
        column: Optional[str] = None,
    ):
        """Initialize a TimeSeriesError.

        Args:
            message: The primary error message.
            operation: Optional operation type (e.g., 'rolling_mean', 'lag').
            window_size: Optional window size parameter.
            column: Optional column being processed.
        """
        self.operation = operation
        self.window_size = window_size
        self.column = column

        params = {}
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
