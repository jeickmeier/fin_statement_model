from __future__ import annotations

import re
from dataclasses import dataclass
from functools import total_ordering
from typing import Optional

from fin_statement_model.core.errors import PeriodError

__all__: list[str] = ["Period"]


@total_ordering
@dataclass(frozen=True, slots=True)
class Period:  # pylint: disable=too-many-instance-attributes
    """Value object representing a financial reporting *period*.

    A *Period* can currently be expressed in one of three formats:

    1. Annual: ``YYYY`` (e.g. ``"2023"``)
    2. Quarterly: ``YYYYQ[1-4]`` (e.g. ``"2023Q4"``)
    3. Monthly (ISO): ``YYYY-MM`` (e.g. ``"2023-03"``)

    The object is *immutable* and *hashable* so that it can safely be used as a
    key in dictionaries or stored in sets.  Chronological ordering works across
    representations – i.e. ``Period("2023Q1") < Period("2023-03") <
    Period("2023Q4") < Period("2023")``.
    """

    year: int
    quarter: Optional[int] = None  # 1-4
    month: Optional[int] = None  # 1-12

    # ------------------------------------------------------------------
    # Regex patterns ----------------------------------------------------
    # ------------------------------------------------------------------
    _PAT_Q = re.compile(r"^(?P<y>\d{4})Q(?P<q>[1-4])$")
    _PAT_Y = re.compile(r"^(?P<y>\d{4})$")
    _PAT_M = re.compile(r"^(?P<y>\d{4})-(?P<m>0[1-9]|1[0-2])$")

    # ------------------------------------------------------------------
    # Construction helpers ---------------------------------------------
    # ------------------------------------------------------------------
    @classmethod
    def parse(cls, s: str) -> "Period":
        """Parse *s* into a :class:`Period` or raise :class:`PeriodError`."""
        if not isinstance(s, str):
            raise PeriodError("Period string must be of type str", period=str(s))

        if (match := cls._PAT_Q.match(s)) is not None:
            year = int(match.group("y"))
            quarter = int(match.group("q"))
            return cls(year=year, quarter=quarter)

        if (match := cls._PAT_M.match(s)) is not None:
            year = int(match.group("y"))
            month = int(match.group("m"))
            return cls(year=year, month=month)

        if (match := cls._PAT_Y.match(s)) is not None:
            year = int(match.group("y"))
            return cls(year=year)

        raise PeriodError("Invalid period format", period=s)

    # Friendly helper that does *not* raise -----------------------------
    @classmethod
    def try_parse(cls, s: str) -> Optional["Period"]:
        """Return :class:`Period` if *s* is valid else *None* (no exception)."""
        try:
            return cls.parse(s)
        except PeriodError:  # pragma: no cover – helper should swallow errors
            return None

    # ------------------------------------------------------------------
    # Dunder overrides --------------------------------------------------
    # ------------------------------------------------------------------
    def __str__(self) -> str:
        if self.quarter is not None:
            return f"{self.year}Q{self.quarter}"
        if self.month is not None:
            return f"{self.year}-{self.month:02d}"
        return f"{self.year}"

    def __repr__(self) -> str:  # pragma: no cover – debugger aid
        return f"Period('{str(self)}')"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Period):
            return NotImplemented
        return (
            self.year == other.year
            and self.quarter == other.quarter
            and self.month == other.month
        )

    def __lt__(self, other: "Period") -> bool:
        if not isinstance(other, Period):  # pragma: no cover – safety
            return NotImplemented
        return self._order_key < other._order_key

    def __hash__(self) -> int:
        return hash((self.year, self.quarter, self.month))

    # ------------------------------------------------------------------
    # Convenience properties -------------------------------------------
    # ------------------------------------------------------------------
    @property
    def is_annual(self) -> bool:
        """Return *True* if the period represents a full year."""
        return self.quarter is None and self.month is None

    @property
    def is_quarterly(self) -> bool:
        """Return *True* if the period is a fiscal quarter (Q1–Q4)."""
        return self.quarter is not None

    @property
    def is_monthly(self) -> bool:
        """Return *True* if the period is a calendar month (ISO *YYYY-MM*)."""
        return self.month is not None

    # ------------------------------------------------------------------
    # Internal helpers --------------------------------------------------
    # ------------------------------------------------------------------
    @property
    def _order_key(self) -> tuple[int, int]:
        """Return a numeric key allowing chronological ordering across types."""
        # Map to *month number* inside the year for cross-type comparisons:
        #   Year  -> 13   (comes *after* Q4 / Dec to preserve intuitive ordering)
        #   Q1    -> 3
        #   Q2    -> 6
        #   Q3    -> 9
        #   Q4    -> 12
        #   Month -> month number (1–12)
        if self.month is not None:
            month_idx = self.month
        elif self.quarter is not None:
            month_idx = self.quarter * 3
        else:
            month_idx = 13  # year-level – place after Q4/Dec of the same year
        return (self.year, month_idx)
