"""Configuration models and enums for preprocessing transformers.

This module provides Pydantic models and enums for configuring data preprocessing
transformations in the fin_statement_model library. The configuration system
follows a declarative approach, allowing users to specify transformations using
either direct instantiation or a fluent DSL interface.

Key Features:
    - Type-safe configuration via Pydantic models
    - Fluent DSL for common transformations
    - Strict validation of configuration parameters
    - Composable transformation pipelines

Examples:
    Basic usage with direct instantiation:

    >>> from fin_statement_model.preprocessing.config import NormalizationConfig
    >>> config = NormalizationConfig(
    ...     normalization_type='percent_of',
    ...     reference='revenue'
    ... )

    Using the fluent DSL interface:

    >>> config = NormalizationConfig.percent_of('revenue')
    >>> time_series = TimeSeriesConfig.moving_avg(window_size=4)
    >>> period_conv = PeriodConversionConfig.quarterly_to_annual()
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, model_validator


class NormalizationType(Enum):
    """Available normalization types for NormalizationTransformer.

    Members:
        PERCENT_OF: Calculate values as percentages of a reference column
        MINMAX: Scale values to [0,1] range using (x - min)/(max - min)
        STANDARD: Standardize using z-score (x - mean)/std
        SCALE_BY: Multiply values by a constant factor

    Examples:
        >>> from fin_statement_model.preprocessing.config import NormalizationType
        >>> NormalizationType.PERCENT_OF.value
        'percent_of'
        >>> NormalizationType.MINMAX.value
        'minmax'
    """

    PERCENT_OF = "percent_of"
    MINMAX = "minmax"
    STANDARD = "standard"
    SCALE_BY = "scale_by"


class TransformationType(Enum):
    """Available transformation types for TimeSeriesTransformer.

    Members:
        GROWTH_RATE: Period-over-period growth rate
        MOVING_AVG: Rolling mean over specified window
        CAGR: Compound Annual Growth Rate
        YOY: Year-over-Year growth rate
        QOQ: Quarter-over-Quarter growth rate

    Examples:
        >>> from fin_statement_model.preprocessing.config import TransformationType
        >>> TransformationType.GROWTH_RATE.value
        'growth_rate'
        >>> TransformationType.YOY.value
        'yoy'
    """

    GROWTH_RATE = "growth_rate"
    MOVING_AVG = "moving_avg"
    CAGR = "cagr"
    YOY = "yoy"
    QOQ = "qoq"


class ConversionType(Enum):
    """Available conversion types for PeriodConversionTransformer.

    Members:
        QUARTERLY_TO_ANNUAL: Convert quarterly data to annual
        MONTHLY_TO_QUARTERLY: Convert monthly data to quarterly
        MONTHLY_TO_ANNUAL: Convert monthly data to annual
        QUARTERLY_TO_TTM: Convert quarterly data to trailing twelve months

    Examples:
        >>> from fin_statement_model.preprocessing.config import ConversionType
        >>> ConversionType.QUARTERLY_TO_ANNUAL.value
        'quarterly_to_annual'
        >>> ConversionType.QUARTERLY_TO_TTM.value
        'quarterly_to_ttm'
    """

    QUARTERLY_TO_ANNUAL = "quarterly_to_annual"
    MONTHLY_TO_QUARTERLY = "monthly_to_quarterly"
    MONTHLY_TO_ANNUAL = "monthly_to_annual"
    QUARTERLY_TO_TTM = "quarterly_to_ttm"


class StatementType(Enum):
    """Available statement types for StatementFormattingTransformer.

    Members:
        INCOME_STATEMENT: Income Statement / P&L
        BALANCE_SHEET: Balance Sheet / Statement of Financial Position
        CASH_FLOW: Cash Flow Statement

    Examples:
        >>> from fin_statement_model.preprocessing.config import StatementType
        >>> StatementType.INCOME_STATEMENT.value
        'income_statement'
        >>> StatementType.BALANCE_SHEET.value
        'balance_sheet'
    """

    INCOME_STATEMENT = "income_statement"
    BALANCE_SHEET = "balance_sheet"
    CASH_FLOW = "cash_flow"


class NormalizationConfig(BaseModel):
    """Configuration for normalization transformations.

    This model configures how numerical data should be normalized or scaled.
    Common use cases include calculating ratios, standardizing scales, and
    applying business-specific scaling factors.

    Attributes:
        normalization_type: Type of normalization to apply:
            - 'percent_of': Express values as percentage of reference column
            - 'minmax': Scale to [0,1] range
            - 'standard': Apply z-score standardization
            - 'scale_by': Multiply by constant factor
        reference: Reference column name for 'percent_of' normalization
        scale_factor: Scaling factor for 'scale_by' normalization

    Examples:
        Calculate percentages of revenue:

        >>> config = NormalizationConfig(
        ...     normalization_type='percent_of',
        ...     reference='revenue'
        ... )

        Using the fluent DSL:

        >>> config = NormalizationConfig.percent_of('revenue')
        >>> config = NormalizationConfig.scale_by(0.001)  # Convert to thousands

    Notes:
        - For 'percent_of', reference column must exist in the data
        - For 'scale_by', scale_factor must be a non-zero number
        - 'minmax' and 'standard' don't require additional parameters
    """

    normalization_type: Optional[str] = None
    reference: Optional[str] = None
    scale_factor: Optional[float] = None

    # Disallow extra attributes via model_config (equivalent to extra="forbid")
    model_config = ConfigDict(extra="forbid")

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def _check_required_fields(self) -> "NormalizationConfig":  # noqa: D401
        """Validate that required fields are present for each normalization type.

        Returns:
            The validated config object

        Raises:
            ValueError: If required fields are missing
        """
        ntype = self.normalization_type or NormalizationType.PERCENT_OF.value
        if ntype == NormalizationType.PERCENT_OF.value and not self.reference:
            raise ValueError(
                "reference must be provided when normalization_type='percent_of'"
            )
        if ntype == NormalizationType.SCALE_BY.value and self.scale_factor is None:
            raise ValueError(
                "scale_factor must be provided when normalization_type='scale_by'"
            )
        return self

    # ------------------------------------------------------------------
    # Fluent constructors / DSL helpers
    # ------------------------------------------------------------------

    @classmethod
    def percent_of(cls, reference: str) -> "NormalizationConfig":
        """Quick helper for ``percent_of`` normalisation.

        Args:
            reference: Name of the reference column (e.g., 'revenue')

        Returns:
            Config for calculating percentages relative to reference

        Examples:
            >>> config = NormalizationConfig.percent_of('revenue')
            >>> config.normalization_type
            'percent_of'
            >>> config.reference
            'revenue'
        """
        return cls(
            normalization_type=NormalizationType.PERCENT_OF.value, reference=reference
        )

    @classmethod
    def minmax(cls) -> "NormalizationConfig":
        """Return config for min-max scaling.

        This scales values to the [0,1] range using (x - min)/(max - min).

        Returns:
            Config for min-max normalization

        Examples:
            >>> config = NormalizationConfig.minmax()
            >>> config.normalization_type
            'minmax'
        """
        return cls(normalization_type=NormalizationType.MINMAX.value)

    @classmethod
    def standard(cls) -> "NormalizationConfig":
        """Return config for z-score standardisation.

        This standardizes values using (x - mean)/std to achieve zero mean
        and unit variance.

        Returns:
            Config for z-score standardization

        Examples:
            >>> config = NormalizationConfig.standard()
            >>> config.normalization_type
            'standard'
        """
        return cls(normalization_type=NormalizationType.STANDARD.value)

    @classmethod
    def scale_by(cls, scale_factor: float) -> "NormalizationConfig":
        """Return config for simple scaling by *scale_factor*.

        Args:
            scale_factor: Factor to multiply values by (e.g., 0.001 for thousands)

        Returns:
            Config for scaling by constant factor

        Examples:
            >>> config = NormalizationConfig.scale_by(0.001)
            >>> config.normalization_type
            'scale_by'
            >>> config.scale_factor
            0.001
        """
        return cls(
            normalization_type=NormalizationType.SCALE_BY.value,
            scale_factor=scale_factor,
        )


class TimeSeriesConfig(BaseModel):
    """Configuration for time series transformations.

    This model configures time-based transformations like growth rates,
    moving averages, and period-over-period comparisons.

    Attributes:
        transformation_type: Type of time series transformation:
            - 'growth_rate': Period-over-period growth
            - 'moving_avg': Rolling mean over window
            - 'cagr': Compound Annual Growth Rate
            - 'yoy': Year-over-Year comparison
            - 'qoq': Quarter-over-Quarter comparison
        periods: Number of periods for lag-based calculations
        window_size: Window size for moving average calculations

    Examples:
        Calculate Year-over-Year growth:

        >>> config = TimeSeriesConfig(
        ...     transformation_type='yoy',
        ...     periods=4  # Four quarters
        ... )

        Using the fluent DSL:

        >>> config = TimeSeriesConfig.yoy()  # Default 4 periods
        >>> config = TimeSeriesConfig.moving_avg(window_size=3)

    Notes:
        - For moving averages, window_size must be specified
        - YOY defaults to 4 periods (quarters)
        - QOQ defaults to 1 period
    """

    transformation_type: Optional[str] = None
    periods: Optional[int] = None
    window_size: Optional[int] = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _check_params(self) -> "TimeSeriesConfig":
        """Validate parameters for each transformation type.

        Returns:
            The validated config object

        Raises:
            ValueError: If required parameters are missing
        """
        ttype = self.transformation_type or TransformationType.GROWTH_RATE.value
        if ttype == TransformationType.MOVING_AVG.value and not self.window_size:
            raise ValueError(
                "window_size must be provided for moving_avg transformation"
            )
        return self

    # ------------------------------------------------------------------
    # DSL helpers
    # ------------------------------------------------------------------

    @classmethod
    def growth_rate(cls, periods: int = 1) -> "TimeSeriesConfig":
        """Configure period-over-period growth rate calculation.

        Args:
            periods: Number of periods to look back (default: 1)

        Returns:
            Growth rate calculation config

        Examples:
            >>> config = TimeSeriesConfig.growth_rate(periods=2)
            >>> config.transformation_type
            'growth_rate'
            >>> config.periods
            2
        """
        return cls(
            transformation_type=TransformationType.GROWTH_RATE.value, periods=periods
        )

    @classmethod
    def moving_avg(cls, window_size: int) -> "TimeSeriesConfig":
        """Configure moving average calculation.

        Args:
            window_size: Size of the rolling window

        Returns:
            Moving average calculation config

        Examples:
            >>> config = TimeSeriesConfig.moving_avg(window_size=3)
            >>> config.transformation_type
            'moving_avg'
            >>> config.window_size
            3
        """
        return cls(
            transformation_type=TransformationType.MOVING_AVG.value,
            window_size=window_size,
        )

    @classmethod
    def cagr(cls) -> "TimeSeriesConfig":
        """Configure Compound Annual Growth Rate calculation.

        Returns:
            CAGR calculation config

        Examples:
            >>> config = TimeSeriesConfig.cagr()
            >>> config.transformation_type
            'cagr'
        """
        return cls(transformation_type=TransformationType.CAGR.value)

    @classmethod
    def yoy(cls, periods: int | None = None) -> "TimeSeriesConfig":
        """Configure Year-over-Year growth calculation.

        Args:
            periods: Number of periods for YOY (default: 4 quarters)

        Returns:
            YOY calculation config

        Examples:
            >>> config = TimeSeriesConfig.yoy()  # Default 4 periods
            >>> config.transformation_type
            'yoy'
            >>> config.periods
            4
        """
        return cls(
            transformation_type=TransformationType.YOY.value, periods=periods or 4
        )

    @classmethod
    def qoq(cls, periods: int | None = None) -> "TimeSeriesConfig":
        """Configure Quarter-over-Quarter growth calculation.

        Args:
            periods: Number of periods for QOQ (default: 1 quarter)

        Returns:
            QOQ calculation config

        Examples:
            >>> config = TimeSeriesConfig.qoq()  # Default 1 period
            >>> config.transformation_type
            'qoq'
            >>> config.periods
            1
        """
        return cls(
            transformation_type=TransformationType.QOQ.value, periods=periods or 1
        )


class PeriodConversionConfig(BaseModel):
    """Configuration for period conversion transformations.

    This model configures how to convert between different time periods
    (e.g., quarterly to annual) and how to aggregate the data during conversion.

    Attributes:
        conversion_type: Type of period conversion:
            - 'quarterly_to_annual': Convert quarterly to annual
            - 'monthly_to_quarterly': Convert monthly to quarterly
            - 'monthly_to_annual': Convert monthly to annual
            - 'quarterly_to_ttm': Convert to trailing twelve months
        aggregation: Aggregation method for conversion:
            - 'sum': Sum values (default for flow measures)
            - 'mean': Average values
            - 'last': Use last period's value (for stocks)
            - 'first': Use first period's value
            - 'max': Use maximum value
            - 'min': Use minimum value

    Examples:
        Convert quarterly data to annual sums:

        >>> config = PeriodConversionConfig(
        ...     conversion_type='quarterly_to_annual',
        ...     aggregation='sum'
        ... )

        Using the fluent DSL:

        >>> config = PeriodConversionConfig.quarterly_to_annual('sum')
        >>> config = PeriodConversionConfig.quarterly_to_ttm()

    Notes:
        - TTM (Trailing Twelve Months) always uses 'sum' aggregation
        - Choose aggregation based on the metric type:
            - Flow measures (revenue, expenses): Use 'sum'
            - Stock measures (balance sheet): Use 'last'
            - Ratios/percentages: Consider 'mean' or 'last'
    """

    conversion_type: Optional[str] = None
    aggregation: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    # ------------------------------------------------------------------
    # DSL helpers
    # ------------------------------------------------------------------

    @classmethod
    def quarterly_to_annual(cls, aggregation: str = "sum") -> "PeriodConversionConfig":
        """Configure quarterly to annual conversion.

        Args:
            aggregation: How to aggregate quarters (default: 'sum')

        Returns:
            Quarterly to annual conversion config

        Examples:
            >>> config = PeriodConversionConfig.quarterly_to_annual('sum')
            >>> config.conversion_type
            'quarterly_to_annual'
            >>> config.aggregation
            'sum'
        """
        return cls(
            conversion_type=ConversionType.QUARTERLY_TO_ANNUAL.value,
            aggregation=aggregation,
        )

    @classmethod
    def monthly_to_quarterly(cls, aggregation: str = "sum") -> "PeriodConversionConfig":
        """Configure monthly to quarterly conversion.

        Args:
            aggregation: How to aggregate months (default: 'sum')

        Returns:
            Monthly to quarterly conversion config

        Examples:
            >>> config = PeriodConversionConfig.monthly_to_quarterly('mean')
            >>> config.conversion_type
            'monthly_to_quarterly'
            >>> config.aggregation
            'mean'
        """
        return cls(
            conversion_type=ConversionType.MONTHLY_TO_QUARTERLY.value,
            aggregation=aggregation,
        )

    @classmethod
    def monthly_to_annual(cls, aggregation: str = "sum") -> "PeriodConversionConfig":
        """Configure monthly to annual conversion.

        Args:
            aggregation: How to aggregate months (default: 'sum')

        Returns:
            Monthly to annual conversion config

        Examples:
            >>> config = PeriodConversionConfig.monthly_to_annual('last')
            >>> config.conversion_type
            'monthly_to_annual'
            >>> config.aggregation
            'last'
        """
        return cls(
            conversion_type=ConversionType.MONTHLY_TO_ANNUAL.value,
            aggregation=aggregation,
        )

    @classmethod
    def quarterly_to_ttm(cls) -> "PeriodConversionConfig":
        """Configure quarterly to trailing twelve months conversion.

        Returns:
            TTM conversion config (always uses 'sum' aggregation)

        Examples:
            >>> config = PeriodConversionConfig.quarterly_to_ttm()
            >>> config.conversion_type
            'quarterly_to_ttm'
            >>> config.aggregation
            'sum'
        """
        return cls(
            conversion_type=ConversionType.QUARTERLY_TO_TTM.value, aggregation="sum"
        )


class StatementFormattingConfig(BaseModel):
    """Configuration for formatting statement output.

    This model configures how financial statements should be formatted
    for display or analysis, including subtotal calculation and sign conventions.

    Attributes:
        statement_type: Type of financial statement:
            - 'income_statement': Income Statement / P&L
            - 'balance_sheet': Balance Sheet
            - 'cash_flow': Cash Flow Statement
        add_subtotals: Whether to include subtotal lines (e.g., Gross Profit)
        apply_sign_convention: Whether to apply standard sign conventions:
            - Assets: Positive
            - Liabilities: Negative
            - Revenue: Positive
            - Expenses: Negative
            - Cash Inflows: Positive
            - Cash Outflows: Negative

    Examples:
        Format a balance sheet with standard conventions:

        >>> config = StatementFormattingConfig(
        ...     statement_type='balance_sheet',
        ...     add_subtotals=True,
        ...     apply_sign_convention=True
        ... )

    Notes:
        - Subtotals are calculated based on standard groupings
        - Sign conventions follow standard accounting practices
        - When sign_convention=False, values are displayed as-is
    """

    statement_type: Optional[str] = None
    add_subtotals: Optional[bool] = None
    apply_sign_convention: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")


__all__ = [
    "ConversionType",
    "NormalizationConfig",
    "NormalizationType",
    "PeriodConversionConfig",
    "StatementFormattingConfig",
    "StatementType",
    "TimeSeriesConfig",
    "TransformationType",
]
