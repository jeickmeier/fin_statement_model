"""Common period granularity definitions & helpers for the preprocessing layer.

This module centralises period-related constants / utility functions so that
other packages (forecasting, preprocessing transformers, etc.) can share a
single source of truth and avoid ad-hoc month/quarter/year conversion tables.
"""

from __future__ import annotations

from enum import Enum
from typing import Final, Mapping, Union

import pandas as pd

__all__ = [
    "Period",
    "MONTHS_IN_YEAR",
    "MONTHS_IN_QUARTER",
    "quarter_to_months",
    "month_to_quarter",
    "resample_to_period",
]


class Period(str, Enum):
    """Supported period granularities within the library."""

    MONTH = "M"  # Pandas offset alias for month-end ("M")
    QUARTER = "Q"  # Quarter-end (calendar) – pandas default is year-end quarter.
    YEAR = "A"  # Year-end ("A"/"Y") – choose "A" to be explicit.

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    @property
    def to_years(self) -> float:
        """Return the number of *years* represented by one unit of *self*."""

        mapping: dict[Period, float] = {
            Period.MONTH: 1 / 12,
            Period.QUARTER: 1 / 4,
            Period.YEAR: 1.0,
        }
        return mapping[self]

    @property
    def to_months(self) -> int:
        """Return the number of *months* represented by one unit of *self*."""

        mapping: dict[Period, int] = {
            Period.MONTH: 1,
            Period.QUARTER: 3,
            Period.YEAR: 12,
        }
        return mapping[self]

    @staticmethod
    def infer_from_offset(alias: str) -> "Period":
        """Infer Period from a pandas offset alias ("M", "Q", "A", etc.)."""

        alias = alias.upper()
        if alias.startswith("M"):
            return Period.MONTH
        if alias.startswith("Q"):
            return Period.QUARTER
        if alias.startswith(("A", "Y")):
            return Period.YEAR
        raise ValueError(f"Cannot infer period type from offset alias '{alias}'")


# ---------------------------------------------------------------------------
# Conversion tables – kept as *constants* for fast lookup.
# ---------------------------------------------------------------------------

MONTHS_IN_YEAR: Final[int] = 12
MONTHS_IN_QUARTER: Final[int] = 3

# Map e.g. (2023, 1) → (2023-01-31, 2023-02-28, 2023-03-31)
# Implemented as *callable* rather than constant due to variable month lengths.


def quarter_to_months(year: int, quarter: int) -> list[pd.Timestamp]:
    """Return month-end Timestamps belonging to *quarter* of *year*.

    Args:
        year: Calendar year.
        quarter: Quarter number, 1-based (1-4).

    Returns:
        List with three *pandas.Timestamp* objects representing the month-end
        dates of the quarter.
    """
    if quarter not in {1, 2, 3, 4}:
        raise ValueError("quarter must be in 1..4")

    start_month = 3 * (quarter - 1) + 1
    months = [start_month + i for i in range(3)]
    return [
        pd.Timestamp(year=year, month=m, day=1) + pd.offsets.MonthEnd() for m in months
    ]


def month_to_quarter(ts: pd.Timestamp) -> tuple[int, int]:
    """Return *(year, quarter)* tuple for a given Timestamp."""

    quarter = (ts.month - 1) // 3 + 1
    return ts.year, quarter


# ---------------------------------------------------------------------------
# Resampling helper (simpler interface than pandas.Grouper strings everywhere).
# ---------------------------------------------------------------------------


DfOrSeries = Union[pd.DataFrame, pd.Series]


def resample_to_period(
    df: DfOrSeries, target: Period, *, aggregation: str = "sum"
) -> DfOrSeries:
    """Resample *df*/*Series* to *target* granularity using *aggregation* method.

    This is a thin wrapper around *pandas.DataFrame.resample* that selects the
    correct offset string given a :class:`Period` enum member.
    """
    rule_map: Mapping[Period, str] = {
        Period.MONTH: "M",
        Period.QUARTER: "Q",
        Period.YEAR: "A",
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
