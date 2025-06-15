"""Provide the NormalizationTransformer for normalizing financial data.

This module defines the transformer to normalize data using percent_of, minmax,
standard, or scale_by methods within the preprocessing layer.
"""

import logging
from typing import ClassVar, Optional, Union

import numpy as np
import pandas as pd

from fin_statement_model.core.errors import DataValidationError
from fin_statement_model.preprocessing.base_transformer import DataTransformer
from fin_statement_model.preprocessing.config import (
    NormalizationConfig,
    NormalizationType,
)
from fin_statement_model.preprocessing.errors import NormalizationError

logger = logging.getLogger(__name__)


class NormalizationTransformer(DataTransformer):
    """Normalize financial data using various methods.

    This transformer provides multiple normalization strategies commonly used in
    financial analysis to make data comparable across different scales or to
    express values as percentages of a reference metric.

    Supported normalization types:
        - **percent_of**: Express values as percentages of a reference column
          (e.g., all items as % of revenue)
        - **minmax**: Scale values to [0, 1] range based on min/max values
        - **standard**: Standardize using (x - mean) / std deviation
        - **scale_by**: Multiply all values by a fixed scale factor

    Examples:
        Express all income statement items as percentage of revenue:

        >>> import pandas as pd
        >>> from fin_statement_model.preprocessing.transformers import NormalizationTransformer
        >>>
        >>> # Sample income statement data
        >>> data = pd.DataFrame({
        ...     'revenue': [1000, 1100, 1200],
        ...     'cogs': [600, 650, 700],
        ...     'operating_expenses': [200, 220, 250]
        ... }, index=['2021', '2022', '2023'])
        >>>
        >>> # Create transformer to express as % of revenue
        >>> normalizer = NormalizationTransformer(
        ...     normalization_type='percent_of',
        ...     reference='revenue'
        ... )
        >>>
        >>> # Transform the data
        >>> normalized = normalizer.transform(data)
        >>> print(normalized)
        #       revenue  cogs  operating_expenses
        # 2021    100.0  60.0               20.0
        # 2022    100.0  59.1               20.0
        # 2023    100.0  58.3               20.8

        Scale financial data to millions:

        >>> # Scale values to millions (divide by 1,000,000)
        >>> scaler = NormalizationTransformer(
        ...     normalization_type='scale_by',
        ...     scale_factor=0.000001
        ... )
        >>> scaled = scaler.transform(data)

    Note:
        For 'percent_of' normalization, if a reference value is 0 or NaN,
        the corresponding output for that row will be NaN to avoid division
        by zero errors.
    """

    NORMALIZATION_TYPES: ClassVar[list[str]] = [t.value for t in NormalizationType]

    def __init__(
        self,
        normalization_type: Union[
            str, NormalizationType
        ] = NormalizationType.PERCENT_OF,
        reference: Optional[str] = None,
        scale_factor: Optional[float] = None,
        config: Optional[NormalizationConfig] = None,
    ):
        """Initialize the normalizer with specified parameters.

        Args:
            normalization_type: Type of normalization to apply. Can be either
                a string or NormalizationType enum value:
                - 'percent_of': Express values as percentage of reference column
                - 'minmax': Scale to [0,1] range
                - 'standard': Apply z-score normalization
                - 'scale_by': Multiply by scale_factor
            reference: Name of the reference column for 'percent_of' normalization.
                Required when normalization_type is 'percent_of'.
            scale_factor: Multiplication factor for 'scale_by' normalization.
                Required when normalization_type is 'scale_by'.
                Common values: 0.001 (to thousands), 0.000001 (to millions)
            config: Optional NormalizationConfig object containing configuration.
                If provided, overrides other parameters.

        Raises:
            NormalizationError: If normalization_type is invalid, or if required
                parameters are missing for the selected normalization type.
        """
        super().__init__(config.model_dump() if config else None)
        # Normalize enum to string
        if isinstance(normalization_type, NormalizationType):
            norm_type = normalization_type.value
        else:
            norm_type = normalization_type
        if norm_type not in self.NORMALIZATION_TYPES:
            raise NormalizationError(
                f"Invalid normalization type: {norm_type}. "
                f"Must be one of {self.NORMALIZATION_TYPES}",
                method=norm_type,
            )
        self.normalization_type = norm_type

        self.reference = reference
        self.scale_factor = scale_factor

        # Validation
        if (
            self.normalization_type == NormalizationType.PERCENT_OF.value
            and not reference
        ):
            raise NormalizationError(
                "Reference field must be provided for percent_of normalization",
                method=self.normalization_type,
            )

        if (
            self.normalization_type == NormalizationType.SCALE_BY.value
            and scale_factor is None
        ):
            raise NormalizationError(
                "Scale factor must be provided for scale_by normalization",
                method=self.normalization_type,
            )

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Normalize the data based on the configured normalization type.

        Args:
            data: DataFrame containing financial data to normalize.
                All columns will be normalized except the reference column
                in 'percent_of' normalization.

        Returns:
            DataFrame with normalized values. Original column names are preserved
            for all normalization types.

        Raises:
            DataValidationError: If data is not a pandas DataFrame.
            NormalizationError: If reference column is not found in DataFrame
                (for 'percent_of' normalization).
        """
        if not isinstance(data, pd.DataFrame):
            raise DataValidationError(
                f"Unsupported data type: {type(data)}. Expected pandas.DataFrame",
                validation_errors=[f"Got type: {type(data).__name__}"],
            )
        return super().transform(data)

    def validate_config(self) -> None:
        """Validate the transformer configuration.

        Raises:
            NormalizationError: If the configuration is invalid.
        """
        super().validate_config()

        if self.normalization_type not in self.NORMALIZATION_TYPES:
            raise NormalizationError(
                f"Unknown normalization method: {self.normalization_type}. "
                f"Supported methods are: {self.NORMALIZATION_TYPES}",
                method=self.normalization_type,
            )

        if (
            self.normalization_type == NormalizationType.PERCENT_OF.value
            and not self.reference
        ):
            raise NormalizationError(
                "Reference field must be provided for percent_of normalization",
                method=self.normalization_type,
            )

        if (
            self.normalization_type == NormalizationType.SCALE_BY.value
            and self.scale_factor is None
        ):
            raise NormalizationError(
                "Scale factor must be provided for scale_by normalization",
                method=self.normalization_type,
            )

    def _transform_impl(
        self, data: Union[pd.DataFrame, pd.Series]
    ) -> Union[pd.DataFrame, pd.Series]:
        """Apply the normalization transformation.

        Args:
            data: The data to transform.

        Returns:
            The normalized data.

        Raises:
            DataValidationError: If the data type is not supported.
            NormalizationError: If there are issues during normalization.
        """
        if not isinstance(data, pd.DataFrame | pd.Series):
            raise DataValidationError(
                f"Unsupported data type: {type(data)}. Expected pandas.DataFrame or pandas.Series",
                validation_errors=[f"Got type: {type(data).__name__}"],
            )

        # Handle Series by converting to DataFrame temporarily
        if isinstance(data, pd.Series):
            temp_df = data.to_frame()
            result_df = self._normalize_dataframe(temp_df)
            return result_df.iloc[:, 0]  # Return as Series
        else:
            return self._normalize_dataframe(data)

    def _normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply normalization to a DataFrame.

        Args:
            df: DataFrame to normalize.

        Returns:
            Normalized DataFrame.

        Raises:
            NormalizationError: If reference column is not found or other normalization issues.
        """
        result = df.copy()

        if self.normalization_type == NormalizationType.PERCENT_OF.value:
            if self.reference not in df.columns:
                raise NormalizationError(
                    f"Reference column '{self.reference}' not found in DataFrame",
                    method=self.normalization_type,
                    reference_field=self.reference,
                )

            for col in df.columns:
                if col != self.reference:
                    # Replace 0 with NaN in the denominator to ensure division by zero results in NaN
                    reference_series = df[self.reference].replace(0, np.nan)
                    if (
                        reference_series.isnull().all()
                    ):  # If all reference values are NaN (or were 0)
                        result[col] = np.nan
                        logger.warning(
                            f"All reference values for '{self.reference}' are zero or NaN. '{col}' will be NaN."
                        )
                    else:
                        result[col] = (df[col] / reference_series) * 100

        elif (
            self.normalization_type == NormalizationType.MINMAX.value
        ):  # pragma: no cover
            for col in df.columns:
                min_val = df[col].min()
                max_val = df[col].max()

                if max_val > min_val:
                    result[col] = (df[col] - min_val) / (
                        max_val - min_val
                    )  # pragma: no cover
                elif max_val == min_val:  # Handles constant columns
                    result[col] = (
                        0.0  # Or np.nan, depending on desired behavior for constant series
                    )
                # else: max_val < min_val (should not happen with .min()/.max())  # noqa: ERA001

        elif self.normalization_type == NormalizationType.STANDARD.value:
            for col in df.columns:
                mean = df[col].mean()
                std = df[col].std()

                if std > 0:
                    result[col] = (df[col] - mean) / std
                elif std == 0:  # Handles constant columns
                    result[col] = 0.0  # Or np.nan, depending on desired behavior
                # else: std < 0 (not possible)  # noqa: ERA001

        elif self.normalization_type == NormalizationType.SCALE_BY.value:
            for col in df.columns:
                result[col] = df[col] * self.scale_factor

        return result
