"""Preprocessing module entrypoint.

Provides the core interfaces, services, and exceptions for data preprocessing:

- DataTransformer: Abstract base class for defining data transformations.
- CompositeTransformer: Compose multiple transformers into sequential pipelines.
- TransformerFactory: Discover, register, and instantiate transformers by name.
- TransformationService: High-level API for common tasks:
  - normalize_data
  - transform_time_series
  - convert_periods
  - format_statement
  - create/apply transformation pipelines
- Exceptions: PreprocessingError, TransformerRegistrationError, TransformerConfigurationError,
  PeriodConversionError, NormalizationError, TimeSeriesError.

Built-in transformers in `fin_statement_model.preprocessing.transformers`
are automatically discovered and registered on import.

Usage Example:
    >>> import pandas as pd
    >>> from fin_statement_model.preprocessing import TransformationService
    >>> df = pd.DataFrame({'revenue': [1000, 1100], 'cogs': [600, 650]}, index=['2022', '2023'])
    >>> service = TransformationService()
    >>> normalized = service.normalize_data(df, normalization_type='percent_of', reference='revenue')
    >>> print(normalized)
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
