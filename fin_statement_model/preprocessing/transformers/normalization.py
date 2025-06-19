"""Provide the NormalizationTransformer for normalizing financial data.

This module defines the transformer to normalize data using percent_of, minmax,
standard, or scale_by methods within the preprocessing layer.
"""

from typing import Optional, Union, ClassVar, Callable
import logging
import warnings

import numpy as np
import pandas as pd

from fin_statement_model.preprocessing.base_transformer import DataTransformer
from fin_statement_model.preprocessing.config import (
    NormalizationConfig,
    NormalizationType,
)
from fin_statement_model.preprocessing.errors import NormalizationError
from fin_statement_model.core.errors import DataValidationError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# NormalizationTransformer
# ---------------------------------------------------------------------------


CustomNormFn = Callable[[pd.DataFrame, "NormalizationTransformer"], pd.DataFrame]


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

    # Runtime registry for user-supplied normalisation functions.
    _CUSTOM_METHODS: ClassVar[dict[str, CustomNormFn]] = {}

    # ------------------------------------------------------------------
    # Public API for custom method registration
    # ------------------------------------------------------------------

    @classmethod
    def register_custom_method(
        cls, name: str, func: CustomNormFn, *, overwrite: bool = False
    ) -> None:
        """Register a custom normalisation *func* under *name*.

        The callable **must** accept two arguments: the DataFrame to be
        normalised and the *transformer instance* (so it can access config
        such as ``reference`` / ``scale_factor``). It must return the
        normalised DataFrame.

        Args:
            name: Identifier to use in ``NormalizationTransformer(..., normalization_type=name)``.
            func: Callable implementing the normalisation.
            overwrite: Allow replacing an existing registration. Defaults to *False*.
        """
        if name in cls._CUSTOM_METHODS and not overwrite:
            raise ValueError(
                f"Custom normalization method '{name}' already registered."
            )
        cls._CUSTOM_METHODS[name] = func
        logger.info("Registered custom normalization method '%s'", name)

    @classmethod
    def list_custom_methods(cls) -> list[str]:
        """Return names of all registered custom normalisation methods."""
        return list(cls._CUSTOM_METHODS.keys())

    def __init__(
        self,
        normalization_type: Union[
            str, NormalizationType
        ] = NormalizationType.PERCENT_OF,
        reference: Optional[str] = None,
        scale_factor: Optional[float] = None,
        *,
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
        # ------------------------------------------------------------------
        # Configuration precedence: *either* supply a Pydantic config object
        # *or* individual keyword-arguments. If both are provided we keep the
        # config (first-class source-of-truth) and issue a gentle warning so
        # that users can clean up their call-sites.
        # ------------------------------------------------------------------

        if config is not None and any(
            param is not None for param in (reference, scale_factor)
        ):
            warnings.warn(
                "Both 'config' and individual kwargs supplied to NormalizationTransformer; the Pydantic config takes precedence.",
                UserWarning,
                stacklevel=2,
            )

        # Extract values from config if present (takes precedence)
        if config is not None:
            normalization_type = config.normalization_type or normalization_type
            reference = config.reference or reference
            scale_factor = (
                config.scale_factor if config.scale_factor is not None else scale_factor
            )

        # Save incoming config dict for logging/debug via base class
        super().__init__(config.model_dump() if config else None)
        # Normalize enum to string
        if isinstance(normalization_type, NormalizationType):
            norm_type = normalization_type.value
        else:
            norm_type = normalization_type
        if (
            norm_type not in self.NORMALIZATION_TYPES
            and norm_type not in self._CUSTOM_METHODS
        ):
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

        if (
            self.normalization_type not in self.NORMALIZATION_TYPES
            and self.normalization_type not in self._CUSTOM_METHODS
        ):
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

        This is the core implementation method that handles both DataFrame
        and Series inputs by converting Series to single-column DataFrames,
        applying the normalization, and converting back if needed.

        Args:
            data: The data to transform. Can be either:
                - pandas.DataFrame: For multi-column normalization
                - pandas.Series: For single-column normalization

        Returns:
            The normalized data in the same format as the input
            (DataFrame → DataFrame, Series → Series).

        Raises:
            DataValidationError: If the data type is not supported
                (neither DataFrame nor Series).
            NormalizationError: If there are issues during normalization,
                such as missing reference columns or invalid values.

        Examples:
            >>> transformer = NormalizationTransformer(
            ...     normalization_type='scale_by',
            ...     scale_factor=0.001
            ... )
            >>> df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
            >>> result = transformer._transform_impl(df)
            >>> series = pd.Series([1, 2, 3], name='values')
            >>> result_series = transformer._transform_impl(series)
        """
        if not isinstance(data, pd.DataFrame | pd.Series):
            raise DataValidationError(
                f"Unsupported data type: {type(data)}. Expected pandas.DataFrame or pandas.Series",
                validation_errors=[f"Got type: {type(data).__name__}"],
            )

        df, was_series = self._coerce_to_dataframe(data)
        result_df = self._normalize_dataframe(df)
        if was_series:
            return result_df.iloc[:, 0]
        return result_df

    def _normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply normalization to a DataFrame.

        This method implements the core normalization logic for each supported
        method type. It handles special cases like:
        - Division by zero in percent_of calculations
        - Constant columns in minmax/standard normalization
        - Custom normalization methods

        Args:
            df: DataFrame to normalize. For each normalization type:
                - percent_of: Must contain the reference column
                - minmax: Any numeric columns
                - standard: Any numeric columns
                - scale_by: Any numeric columns
                - custom: Depends on the custom method

        Returns:
            Normalized DataFrame with the same column names and index.
            The values are transformed according to the normalization type:
            - percent_of: Values as percentages of reference (0-100 scale)
            - minmax: Values scaled to [0,1] range
            - standard: Values with mean=0, std=1
            - scale_by: Values multiplied by scale_factor
            - custom: Depends on the custom method

        Raises:
            NormalizationError: If:
                - Reference column is not found (for percent_of)
                - All reference values are 0 or NaN (for percent_of)
                - Custom method fails

        Examples:
            >>> df = pd.DataFrame({
            ...     'revenue': [1000, 1100, 1200],
            ...     'costs': [600, 650, 700]
            ... })
            >>> transformer = NormalizationTransformer(
            ...     normalization_type='percent_of',
            ...     reference='revenue'
            ... )
            >>> result = transformer._normalize_dataframe(df)
            >>> print(result)
            #    revenue    costs
            # 0   100.0     60.0
            # 1   100.0     59.1
            # 2   100.0     58.3

        Notes:
            - For percent_of: Reference column remains at 100%
            - For minmax: Constant columns map to 0
            - For standard: Constant columns map to 0
            - For scale_by: Simple multiplication
            - Custom methods: Must handle their own edge cases
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
                # else: max_val < min_val (should not happen with .min()/.max())

        elif self.normalization_type == NormalizationType.STANDARD.value:
            for col in df.columns:
                mean = df[col].mean()
                std = df[col].std()

                if std > 0:
                    result[col] = (df[col] - mean) / std
                elif std == 0:  # Handles constant columns
                    result[col] = 0.0  # Or np.nan, depending on desired behavior
                # else: std < 0 (not possible)

        elif self.normalization_type == NormalizationType.SCALE_BY.value:
            for col in df.columns:
                result[col] = df[col] * self.scale_factor

        else:
            # Custom method
            custom_func = self._CUSTOM_METHODS[self.normalization_type]
            return custom_func(df, self)

        return result

    # ------------------------------------------------------------------
    # Data validation
    # ------------------------------------------------------------------

    def validate_input(self, data: object) -> bool:  # noqa: D401 – imperative mood
        """Return *True* when *data* is a DataFrame or Series.

        This method implements the DataTransformer contract by specifying
        exactly which input types are supported by the normalization
        transformer.

        Args:
            data: The input data to validate. Can be any Python object,
                 but only pandas DataFrame and Series are accepted.

        Returns:
            bool: True if data is either:
                - pandas.DataFrame
                - pandas.Series
                False for all other types.

        Examples:
            >>> transformer = NormalizationTransformer()
            >>> transformer.validate_input(pd.DataFrame())
            True
            >>> transformer.validate_input(pd.Series())
            True
            >>> transformer.validate_input([1, 2, 3])
            False
        """
        return isinstance(data, (pd.DataFrame, pd.Series))
