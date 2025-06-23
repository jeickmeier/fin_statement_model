"""Package for preprocessing transformers.

This package exports built-in data transformer classes for the preprocessing layer.

Available transformers:
    - NormalizationTransformer
    - TimeSeriesTransformer
    - PeriodConversionTransformer

Examples:
    Import and use a built-in transformer:

    >>> from fin_statement_model.preprocessing.transformers import NormalizationTransformer
    >>> import pandas as pd
    >>> df = pd.DataFrame({"revenue": [100, 200], "cogs": [60, 120]})
    >>> normalizer = NormalizationTransformer(normalization_type="percent_of", reference="revenue")
    >>> result = normalizer.transform(df)
    >>> print(result)
"""

from .normalization import NormalizationTransformer
from .period_conversion import PeriodConversionTransformer
from .time_series import TimeSeriesTransformer

__all__ = [
    "NormalizationTransformer",
    "PeriodConversionTransformer",
    "TimeSeriesTransformer",
]
