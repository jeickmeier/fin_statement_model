"""Immutable *Period* value object and lightweight *PeriodIndex* container.

The implementation purposefully avoids any third-party libraries so that the
**domain layer stays pure and dependency-free**.  A subset of the richer
functionality available in ``fin_statement_model.core.time.period`` is
re-implemented here to remove the dependency on the broader *core/time* API.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import total_ordering
from typing import Any, Iterable, Iterator, Optional, Sequence, Tuple, overload

__all__: list[str] = ["Period", "PeriodIndex"]

# ---------------------------------------------------------------------------
# Period
# ---------------------------------------------------------------------------


@total_ordering
@dataclass(frozen=True, slots=True)
class Period:  # pylint: disable=too-many-instance-attributes
    """Canonical representation of a financial reporting period.

    Supported textual formats (case-sensitive):

    • Annual:  ``YYYY``          → ``Period(2023)``
    • Quarter: ``YYYYQ[1-4]``    → ``Period(2023, quarter=4)``
    • Month:   ``YYYY-MM``       → ``Period(2023, month=3)``

    The object is **hashable** and **totally ordered** so it can be used as a
    dictionary key or stored in sets and sorted containers.
    """

    year: int
    quarter: Optional[int] = None  # 1–4 (mutually exclusive with *month*)
    month: Optional[int] = None  # 1–12

    # Regex patterns ----------------------------------------------------
    _PAT_Q = re.compile(r"^(?P<y>\d{4})Q(?P<q>[1-4])$")
    _PAT_Y = re.compile(r"^(?P<y>\d{4})$")
    _PAT_M = re.compile(r"^(?P<y>\d{4})-(?P<m>0[1-9]|1[0-2])$")

    # Construction helpers ---------------------------------------------
    @classmethod
    def parse(cls, s: str) -> "Period":
        """Return a :class:`Period` from *s* or raise :class:`ValueError`."""
        if not isinstance(s, str):
            raise ValueError("Period string must be of type str")

        if (match := cls._PAT_Q.match(s)) is not None:
            return cls(year=int(match.group("y")), quarter=int(match.group("q")))

        if (match := cls._PAT_M.match(s)) is not None:
            return cls(year=int(match.group("y")), month=int(match.group("m")))

        if (match := cls._PAT_Y.match(s)) is not None:
            return cls(year=int(match.group("y")))

        raise ValueError(f"Invalid period format: {s!r}")

    # More forgiving variant – returns *None* on failure ----------------
    @classmethod
    def try_parse(cls, s: str) -> Optional["Period"]:
        """Return :class:`Period` if *s* is valid, else *None*."""
        try:
            return cls.parse(s)
        except ValueError:  # pragma: no cover – helper intended to swallow
            return None

    # Dunder overrides --------------------------------------------------
    def __str__(self) -> str:
        if self.quarter is not None:
            return f"{self.year}Q{self.quarter}"
        if self.month is not None:
            return f"{self.year}-{self.month:02d}"
        return f"{self.year}"

    def __repr__(self) -> str:
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
        if not isinstance(other, Period):  # pragma: no cover
            return NotImplemented
        return self._order_key < other._order_key

    # Convenience predicates -------------------------------------------
    @property
    def is_annual(self) -> bool:
        """Return *True* if the period represents a full calendar/fiscal year."""
        return self.quarter is None and self.month is None

    @property
    def is_quarterly(self) -> bool:
        return self.quarter is not None

    @property
    def is_monthly(self) -> bool:
        return self.month is not None

    # Internal helper – numeric key for ordering -----------------------
    @property
    def _order_key(self) -> Tuple[int, int]:
        # Map to *month number* within the year for cross-type comparisons:
        #   Year  -> 13   (comes after Dec/Q4 of same year)
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
            month_idx = 13
        return (self.year, month_idx)

    # Hash is automatically provided by *dataclass(frozen=True)*


# ---------------------------------------------------------------------------
# PeriodIndex (mutable during build – frozen snapshot after .freeze())
# ---------------------------------------------------------------------------


class PeriodIndex(Sequence[Period]):
    """An *ordered*, *unique* collection of :class:`Period` objects.

    The container is **mutable** until :pyfunc:`freeze` is called, after which
    any further mutation attempts raise :class:`RuntimeError`.  The design is a
    very light-weight substitute for pandas' ``PeriodIndex`` without the heavy
    dependency.
    """

    __slots__ = ("_items", "_frozen")

    def __init__(self, items: Iterable[Period] | None = None) -> None:
        self._items: list[Period] = []
        self._frozen: bool = False
        if items is not None:
            self.extend(items)

    # ------------------------------------------------------------------
    # Mutation helpers (guarded by *frozen* flag)
    # ------------------------------------------------------------------
    def add(self, period: Period) -> None:
        """Add *period* preserving chronological order and uniqueness."""
        self._ensure_not_frozen()
        if period not in self._items:
            self._items.append(period)
            self._items.sort()

    def extend(self, periods: Iterable[Period]) -> None:
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

    def __iter__(self) -> Iterator[Period]:
        return iter(self._items)

    # Overloads for type safety ------------------------------------------------
    @overload
    def __getitem__(self, idx: int) -> Period: ...

    @overload
    def __getitem__(self, idx: slice) -> Sequence[Period]: ...

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
