"""Preprocessing module entrypoint.

This module provides the core interfaces, services, and exceptions for data preprocessing in the fin_statement_model library.

Features:
    - DataTransformer: Abstract base class for defining data transformations
    - CompositeTransformer: Compose multiple transformers into sequential pipelines
    - TransformerFactory: Discover, register, and instantiate transformers by name
    - TransformationService: High-level API for common preprocessing tasks:
        - normalize_data
        - transform_time_series
        - convert_periods
        - format_statement
        - create/apply transformation pipelines
    - Exception hierarchy for robust error handling
    - Built-in transformers are auto-discovered on import

Examples:
    Basic normalization:

    >>> import pandas as pd
    >>> from fin_statement_model.preprocessing import TransformationService
    >>> df = pd.DataFrame({'revenue': [1000, 1100], 'cogs': [600, 650]}, index=['2022', '2023'])
    >>> service = TransformationService()
    >>> normalized = service.normalize_data(df, normalization_type='percent_of', reference='revenue')
    >>> print(normalized)

    List available transformers:

    >>> from fin_statement_model.preprocessing import TransformerFactory
    >>> TransformerFactory.list_transformers()
    ['NormalizationTransformer', 'normalization', 'TimeSeriesTransformer', ...]

    Register a custom transformer:

    >>> from fin_statement_model.preprocessing import TransformerFactory, DataTransformer
    >>> class MyCustomTransformer(DataTransformer):
    ...     def _transform_impl(self, data):
    ...         return data + 1
    ...     def validate_input(self, data):
    ...         return True
    >>> TransformerFactory.register_transformer('my_custom', MyCustomTransformer)
    >>> t = TransformerFactory.create_transformer('my_custom')
    >>> t.execute(1)
    2

See Also:
    - fin_statement_model.preprocessing.base_transformer
    - fin_statement_model.preprocessing.transformer_service
    - fin_statement_model.preprocessing.errors
    - fin_statement_model.preprocessing.config
    - fin_statement_model.preprocessing.transformers
"""

from .base_transformer import DataTransformer, CompositeTransformer
from .transformer_service import TransformerFactory, TransformationService
from .errors import (
    PreprocessingError,
    TransformerRegistrationError,
    TransformerConfigurationError,
    PeriodConversionError,
    NormalizationError,
    TimeSeriesError,
)

## Trigger transformer discovery on package import
TransformerFactory.discover_transformers(
    "fin_statement_model.preprocessing.transformers"
)

__all__ = [
    "CompositeTransformer",
    "DataTransformer",
    "NormalizationError",
    "PeriodConversionError",
    "PreprocessingError",
    "TimeSeriesError",
    "TransformationService",
    "TransformerConfigurationError",
    "TransformerFactory",
    "TransformerRegistrationError",
]
