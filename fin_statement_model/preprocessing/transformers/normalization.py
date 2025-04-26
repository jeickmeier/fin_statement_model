"""Provide a NormalizationTransformer to normalize financial data.

Transforms data by percent_of, minmax, standard, or scale_by methods.

This module implements the NormalizationTransformer for the preprocessing layer.
"""

from typing import Optional, Union, ClassVar

import pandas as pd

from fin_statement_model.preprocessing.base_transformer import DataTransformer
from fin_statement_model.preprocessing.enums import NormalizationType
from fin_statement_model.preprocessing.types import NormalizationConfig


class NormalizationTransformer(DataTransformer):
    """Transformer that normalizes financial data.

    This transformer can normalize values by:
    - Dividing by a reference value (e.g. convert to percentages of revenue)
    - Scaling to a specific range (e.g. 0-1)
    - Applying standard normalization ((x - mean) / std)

    It can operate on DataFrames or dictionary data structures.
    """

    NORMALIZATION_TYPES: ClassVar[list[str]] = [t.value for t in NormalizationType]

    def __init__(
        self,
        normalization_type: Union[str, NormalizationType] = NormalizationType.PERCENT_OF,
        reference: Optional[str] = None,
        scale_factor: Optional[float] = None,
        config: Optional[NormalizationConfig] = None,
    ):
        """Initialize the normalizer.

        Args:
            normalization_type: Type of normalization to apply
                - 'percent_of': Divides by a reference value
                - 'minmax': Scales to range [0,1]
                - 'standard': Applies (x - mean) / std
                - 'scale_by': Multiplies by a scale factor
            reference: Reference field for percent_of normalization
            scale_factor: Factor to scale by for scale_by normalization
            config: Additional configuration options
        """
        super().__init__(config)
        # Normalize enum to string
        if isinstance(normalization_type, NormalizationType):
            norm_type = normalization_type.value
        else:
            norm_type = normalization_type
        if norm_type not in self.NORMALIZATION_TYPES:
            raise ValueError(
                f"Invalid normalization type: {norm_type}. "
                f"Must be one of {self.NORMALIZATION_TYPES}"
            )
        self.normalization_type = norm_type

        self.reference = reference
        self.scale_factor = scale_factor

        # Validation
        if self.normalization_type == NormalizationType.PERCENT_OF.value and not reference:
            raise ValueError("Reference field must be provided for percent_of normalization")

        if self.normalization_type == NormalizationType.SCALE_BY.value and scale_factor is None:
            raise ValueError("Scale factor must be provided for scale_by normalization")

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Normalize the data based on the configured normalization type.

        Args:
            data: pd.DataFrame containing financial data

        Returns:
            pd.DataFrame: Normalized DataFrame
        """
        if not isinstance(data, pd.DataFrame):
            raise TypeError(f"Unsupported data type: {type(data)}. Expected pandas.DataFrame")
        return self._transform_dataframe(data)

    def _transform_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform a DataFrame."""
        result = df.copy()

        if self.normalization_type == NormalizationType.PERCENT_OF.value:
            if self.reference not in df.columns:
                raise ValueError(f"Reference column '{self.reference}' not found in DataFrame")

            for col in df.columns:
                if col != self.reference:
                    result[col] = df[col] / df[self.reference] * 100

        elif self.normalization_type == NormalizationType.MINMAX.value:  # pragma: no cover
            for col in df.columns:
                min_val = df[col].min()
                max_val = df[col].max()

                if max_val > min_val:
                    result[col] = (df[col] - min_val) / (max_val - min_val)  # pragma: no cover

        elif self.normalization_type == NormalizationType.STANDARD.value:
            for col in df.columns:
                mean = df[col].mean()
                std = df[col].std()

                if std > 0:
                    result[col] = (df[col] - mean) / std

        elif self.normalization_type == NormalizationType.SCALE_BY.value:
            for col in df.columns:
                result[col] = df[col] * self.scale_factor

        return result
