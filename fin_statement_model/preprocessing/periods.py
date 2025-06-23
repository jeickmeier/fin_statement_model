"""Common period granularity definitions & helpers for the preprocessing layer.

This module centralises period-related constants and utility functions so that
other packages (forecasting, preprocessing transformers, etc.) can share a
single source of truth and avoid ad-hoc month/quarter/year conversion tables.

Features:
    - Period enum for standard period granularities (month, quarter, year)
    - Helpers for converting between months and quarters
    - Resampling utility for DataFrames/Series

Examples:
    Infer period from pandas offset alias:

    >>> Period.infer_from_offset("Q")
    <Period.QUARTER: 'Q'>

    Get months in a quarter:

    >>> quarter_to_months(2023, 2)
    [Timestamp('2023-04-30 00:00:00'), Timestamp('2023-05-31 00:00:00'), Timestamp('2023-06-30 00:00:00')]

    Resample monthly data to annual:

    >>> import pandas as pd
    >>> df = pd.DataFrame({"value": [1, 2, 3, 4, 5, 6]}, index=pd.date_range("2023-01-31", periods=6, freq="M"))
    >>> resample_to_period(df, Period.YEAR, aggregation="sum")
       value
    2023     21
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, Final

import pandas as pd

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = [
    "MONTHS_IN_QUARTER",
    "MONTHS_IN_YEAR",
    "Period",
    "month_to_quarter",
    "quarter_to_months",
    "resample_to_period",
]


class Period(str, Enum):
    """Supported period granularities within the library.

    Members:
        MONTH: Month-end ('ME')
        QUARTER: Quarter-end ('QE')
        YEAR: Year-end ('YE')

    Examples:
        >>> Period.MONTH.value
        'ME'
        >>> Period.QUARTER.value
        'QE'
        >>> Period.YEAR.value
        'YE'
    """

    MONTH = "ME"  # Pandas offset alias for month-end ("ME")
    QUARTER = "QE"  # Quarter-end (calendar)
    YEAR = "YE"  # Year-end ("YE")

    @property
    def to_years(self) -> float:
        """Return the number of *years* represented by one unit of *self*.

        Examples:
            >>> Period.MONTH.to_years
            0.08333333333333333
            >>> Period.QUARTER.to_years
            0.25
            >>> Period.YEAR.to_years
            1.0
        """
        mapping: dict[Period, float] = {
            Period.MONTH: 1 / 12,
            Period.QUARTER: 1 / 4,
            Period.YEAR: 1.0,
        }
        return mapping[self]

    @property
    def to_months(self) -> int:
        """Return the number of *months* represented by one unit of *self*.

        Examples:
            >>> Period.MONTH.to_months
            1
            >>> Period.QUARTER.to_months
            3
            >>> Period.YEAR.to_months
            12
        """
        mapping: dict[Period, int] = {
            Period.MONTH: 1,
            Period.QUARTER: 3,
            Period.YEAR: 12,
        }
        return mapping[self]

    @staticmethod
    def infer_from_offset(alias: str) -> Period:
        """Infer Period from a pandas offset alias ("ME", "QE", "YE", etc.).

        Args:
            alias: Pandas offset alias string (e.g., 'ME', 'QE', 'YE')

        Returns:
            Period enum value corresponding to the alias

        Raises:
            ValueError: If alias cannot be mapped to a Period

        Examples:
            >>> Period.infer_from_offset("ME")
            <Period.MONTH: 'ME'>
            >>> Period.infer_from_offset("QE")
            <Period.QUARTER: 'QE'>
            >>> Period.infer_from_offset("YE")
            <Period.YEAR: 'YE'>
        """
        alias = alias.upper()
        if alias.startswith("M"):
            return Period.MONTH
        if alias.startswith("Q"):
            return Period.QUARTER
        if alias.startswith(("A", "Y")):
            return Period.YEAR
        raise ValueError(f"Cannot infer period type from offset alias '{alias}'")


# ---------------------------------------------------------------------------
# Conversion tables - kept as *constants* for fast lookup.
# ---------------------------------------------------------------------------

MONTHS_IN_YEAR: Final[int] = 12
MONTHS_IN_QUARTER: Final[int] = 3


def quarter_to_months(year: int, quarter: int) -> list[pd.Timestamp]:
    """Return month-end Timestamps belonging to *quarter* of *year*.

    Args:
        year: Calendar year.
        quarter: Quarter number, 1-based (1-4).

    Returns:
        List with three *pandas.Timestamp* objects representing the month-end
        dates of the quarter.

    Examples:
        >>> quarter_to_months(2023, 1)
        [Timestamp('2023-01-31 00:00:00'), Timestamp('2023-02-28 00:00:00'), Timestamp('2023-03-31 00:00:00')]
    """
    if quarter not in {1, 2, 3, 4}:
        raise ValueError("quarter must be in 1..4")

    start_month = 3 * (quarter - 1) + 1
    months = [start_month + i for i in range(3)]
    return [pd.Timestamp(year=year, month=m, day=1) + pd.offsets.MonthEnd() for m in months]


def month_to_quarter(ts: pd.Timestamp) -> tuple[int, int]:
    """Return *(year, quarter)* tuple for a given Timestamp.

    Args:
        ts: pandas.Timestamp to convert

    Returns:
        Tuple of (year, quarter)

    Examples:
        >>> import pandas as pd
        >>> month_to_quarter(pd.Timestamp("2023-05-31"))
        (2023, 2)
    """
    quarter = (ts.month - 1) // 3 + 1
    return ts.year, quarter


# ---------------------------------------------------------------------------
# Resampling helper (simpler interface than pandas.Grouper strings everywhere).
# ---------------------------------------------------------------------------

# NOTE:
# We cannot subscript ``pd.Series`` at *runtime* on pandas < 2.0 because the
# class is not a PEP 585 generic alias in older pandas versions.  Attempting
# to evaluate ``pd.Series[Any]`` therefore raises ``TypeError: 'Series' is not
# subscriptable`` when this module is imported - which breaks the entire
# test-suite.  To keep static type checkers (mypy, Pyright, etc.) happy *and*
# avoid the runtime error, we define the alias conditionally:
#   * During **type checking** we use the fully-parametrised generic form so
#     that tools understand the expected element type.
#   * At **runtime** we fall back to the *unparametrised* ``pd.Series`` class
#     which works across all supported pandas versions.

if TYPE_CHECKING:  # pragma: no cover - evaluated only by static analysers
    from pandas import Series as _Series

    DfOrSeries = pd.DataFrame | _Series[Any]
else:
    # Runtime-safe alias: still correctly represents the union of the two
    # containers but avoids subscripted ``Series``.
    DfOrSeries = pd.DataFrame | pd.Series


def resample_to_period(df: DfOrSeries, target: Period, *, aggregation: str = "sum") -> DfOrSeries:
    """Resample *df*/*Series* to *target* granularity using *aggregation* method.

    This is a thin wrapper around *pandas.DataFrame.resample* that selects the
    correct offset string given a :class:`Period` enum member.

    Args:
        df: DataFrame or Series to resample
        target: Target period granularity (Period.MONTH, QUARTER, YEAR)
        aggregation: Aggregation method ('sum', 'mean', 'last', etc.)

    Returns:
        Resampled DataFrame or Series

    Raises:
        ValueError: If aggregation method is not supported

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"value": [1, 2, 3, 4]}, index=pd.date_range("2023-01-31", periods=4, freq="ME"))
        >>> resample_to_period(df, Period.QUARTER, aggregation="sum")
               value
        2023Q1      6
    """
    rule_map: Mapping[Period, str] = {
        Period.MONTH: "ME",
        Period.QUARTER: "QE",
        Period.YEAR: "YE",
    }

    rule = rule_map[target]
    if aggregation == "sum":
        return df.resample(rule).sum()
    if aggregation == "mean":
        return df.resample(rule).mean()
    if aggregation == "last":
        return df.resample(rule).last()
    if aggregation == "first":
        return df.resample(rule).first()
    if aggregation == "max":
        return df.resample(rule).max()
    if aggregation == "min":
        return df.resample(rule).min()

    raise ValueError(f"Unsupported aggregation method '{aggregation}'")
