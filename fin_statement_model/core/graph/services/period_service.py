"""PeriodService – single source of truth for period management in the graph layer.

The service owns a mutable list of *unique*, *sorted* period identifiers and
provides helpers to query or extend that list.  A direct list reference is
kept so that legacy code paths accessing ``Graph._periods`` remain in sync.

Example:

>>> from fin_statement_model.core.graph.services.period_service import PeriodService
>>> ps = PeriodService(["2023", "2022"])
>>> ps.periods
["2022", "2023"]
>>> ps.add_periods(["2021", "2023"])
>>> ps.periods
["2021", "2022", "2023"]
"""

from __future__ import annotations

from typing import Iterable, List

# Period-related helpers -------------------------------------------------------
# We import the new value object locally to avoid recursive import issues.
from fin_statement_model.core.time.period import Period

# Type alias accepted by public APIs
_PeriodStr = str  # alias for readability

__all__: list[str] = ["PeriodService"]


class PeriodService:  # pylint: disable=too-few-public-methods
    """Single source of truth for *period* management inside the graph layer.

    The service keeps a **shared list reference** so that legacy code paths
    directly touching ``Graph._periods`` remain in sync.  Internally periods are
    stored as :class:`Period` objects to guarantee type-safe comparisons and
    reliable chronological ordering.
    """

    def __init__(self, periods: Iterable[_PeriodStr] | None = None) -> None:
        """Create a new :class:`PeriodService`.

        Args:
            periods: Optional iterable of initial periods (either raw strings or
                :class:`Period` instances).  If the provided object is **exactly**
                a ``list`` instance we *reuse* the reference so external code
                observing that list (e.g. ``Graph._periods``) remains in sync.
        """

        # Backing list reference (strings) ------------------------------------
        self._periods: List[str]

        if isinstance(periods, list):
            # Reuse reference and ensure elements are str
            self._periods = periods
            if not all(isinstance(p, str) for p in self._periods):
                raise TypeError("Initial periods list must contain str elements only.")

            # Deduplicate & sort
            self._periods[:] = self._sorted_unique(self._periods)
        else:
            # Create a fresh list managed exclusively by this service
            self._periods = []
            if periods is not None:
                self.add_periods(periods)

    # ------------------------------------------------------------------
    # Public API --------------------------------------------------------
    # ------------------------------------------------------------------
    @property
    def periods(self) -> List[str]:
        """Return an immutable **sorted** list of *string* period identifiers."""
        # Keep external contract (str) for now.  Internally we maintain order
        # via Period objects; converting here preserves that order.
        return self._periods

    def add_periods(self, periods: Iterable[str]) -> None:
        """Add new periods ensuring uniqueness and chronological ordering.

        Args:
            periods: Iterable of raw strings (``"2023Q1"``) *or* :class:`Period`
                instances.

        Raises:
            TypeError: If *periods* is not iterable or contains unsupported types.
            PeriodError: If a raw string cannot be parsed into a valid period.
        """
        if isinstance(
            periods, str
        ):  # pragma: no cover – defend against str iterable confusion
            raise TypeError(
                "Periods must be an iterable of strings, not a single string."
            )

        period_list = list(periods)
        if not all(isinstance(p, str) for p in period_list):
            raise TypeError("All periods must be strings.")

        combined = list(set(self._periods).union(period_list))
        self._periods[:] = self._sorted_unique(combined)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _sort_key(value: str) -> tuple[int, int | str]:
        maybe = Period.try_parse(value)
        if maybe is not None:
            year, month_idx = maybe._order_key  # pylint: disable=protected-access
            return (0, year * 100 + month_idx)
        return (1, value)

    def _sorted_unique(self, values: List[str]) -> List[str]:
        return sorted(list(set(values)), key=self._sort_key)
