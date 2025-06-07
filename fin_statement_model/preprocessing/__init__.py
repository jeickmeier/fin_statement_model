"""Export DataTransformer, CompositeTransformer, and TransformerFactory for preprocessing.

This module exposes core transformer interfaces and factory for the preprocessing layer.
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
