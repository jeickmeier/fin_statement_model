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
    """Encapsulate period management helpers."""

    def __init__(self, periods: list[str] | None = None) -> None:  # noqa: D401
        # If an existing list is provided we keep a direct reference so that
        # legacy code paths (still touching ``Graph._periods``) stay in sync.
        self._periods: list[str] = periods if periods is not None else []

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
