"""Simple PeriodService stub – manages the list of unique, sorted periods.

This service will eventually hold all period-deduplication, validation and
sorting logic previously embedded in ``Graph``.  For now it offers the same
public surface in a minimal form so that ``Graph`` can delegate during the
incremental refactor.
"""

from __future__ import annotations

from typing import List

__all__: list[str] = ["PeriodService"]


class PeriodService:  # pylint: disable=too-few-public-methods
    """Encapsulate period management helpers.

    The service now owns its internal list of period identifiers.  Call-sites
    should interact exclusively via the public API – direct mutation of the
    underlying list is no longer supported (removed legacy shim).
    """

    def __init__(self) -> None:  # noqa: D401
        # Internal, sorted list of unique period identifiers.
        self._periods: list[str] = []

    # ------------------------------------------------------------------
    # Public API --------------------------------------------------------
    # ------------------------------------------------------------------
    @property
    def periods(self) -> List[str]:  # noqa: D401
        """Return an immutable **sorted** list of period identifiers."""
        # Return a shallow copy to prevent accidental mutation
        return list(self._periods)

    def add_periods(self, periods: list[str]) -> None:  # noqa: D401
        """Add *periods* ensuring uniqueness & sorted order."""
        if not isinstance(periods, list):  # defensive – mirroring existing Graph.guards
            raise TypeError("Periods must be provided as a list of strings.")
        combined = set(self._periods).union(periods)
        sorted_periods = sorted(combined)
        # Mutate in place to keep external references alive
        self._periods.clear()
        self._periods.extend(sorted_periods)

    # ------------------------------------------------------------------
    # Convenience helpers ------------------------------------------------
    # ------------------------------------------------------------------
    def contains(self, period: str) -> bool:  # noqa: D401
        """Return ``True`` if *period* is already registered."""
        return period in self._periods

    def clear(self) -> None:  # noqa: D401
        """Remove all registered periods."""
        self._periods.clear()
