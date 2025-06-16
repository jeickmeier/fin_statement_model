from __future__ import annotations

import re
from dataclasses import dataclass
from functools import total_ordering
from typing import Any, Iterable, Iterator, Optional, Sequence, overload

from fin_statement_model.core.errors import PeriodError

__all__: list[str] = ["Period", "PeriodIndex"]


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


# ---------------------------------------------------------------------------
# PeriodIndex (mutable during build – frozen snapshot after .freeze())
# ---------------------------------------------------------------------------


class PeriodIndex(Sequence["Period"]):
    """An *ordered*, *unique* collection of :class:`Period` objects.

    The container is **mutable** until :pyfunc:`freeze` is called, after which
    any further mutation attempts raise :class:`RuntimeError`.  The design is a
    very light-weight substitute for pandas' ``PeriodIndex`` without the heavy
    dependency.
    """

    __slots__ = ("_items", "_frozen")

    def __init__(self, items: Iterable["Period"] | None = None) -> None:
        self._items: list[Period] = []
        self._frozen: bool = False
        if items is not None:
            self.extend(items)

    # ------------------------------------------------------------------
    # Mutation helpers (guarded by *frozen* flag)
    # ------------------------------------------------------------------
    def add(self, period: "Period") -> None:
        """Add *period* preserving chronological order and uniqueness."""
        self._ensure_not_frozen()
        if period not in self._items:
            self._items.append(period)
            self._items.sort()

    def extend(self, periods: Iterable["Period"]) -> None:
        """Add multiple periods in one go (duplicates ignored)."""
        for p in periods:
            self.add(p)

    def clone(self) -> "PeriodIndex":
        """Return a *mutable copy* of this index (preserves frozen flag)."""
        copy = PeriodIndex(self._items)
        copy._frozen = self._frozen
        return copy

    # Finalise ----------------------------------------------------------
    def freeze(self) -> "PeriodIndex":
        """Return an *immutable* snapshot of the current index."""
        frozen_copy = PeriodIndex(self._items)
        frozen_copy._frozen = True
        return frozen_copy

    # ------------------------------------------------------------------
    # Sequence Protocol – delegate to underlying list (read-only)
    # ------------------------------------------------------------------
    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator["Period"]:
        return iter(self._items)

    # Overloads for type safety ------------------------------------------------
    @overload
    def __getitem__(self, idx: int) -> "Period": ...

    @overload
    def __getitem__(self, idx: slice) -> Sequence["Period"]: ...

    def __getitem__(self, idx: Any) -> Any:
        """Return a single :class:`Period` or a slice of them."""

        return self._items[idx]

    def __contains__(self, item: object) -> bool:
        return item in self._items

    def __repr__(self) -> str:
        return (
            f"PeriodIndex({[str(p) for p in self._items]}){'*' if self._frozen else ''}"
        )

    # ------------------------------------------------------------------
    # Internal helpers --------------------------------------------------
    # ------------------------------------------------------------------
    def _ensure_not_frozen(self) -> None:
        if self._frozen:
            raise RuntimeError(
                "Cannot mutate frozen PeriodIndex – create a clone() first."
            )
