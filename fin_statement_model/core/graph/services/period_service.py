"""Simple PeriodService stub – manages the list of unique, sorted periods.

PeriodService is responsible for managing the list of unique, sorted period identifiers used in the graph.
It provides methods for adding, validating, and clearing periods, ensuring that all period operations are
consistent and deduplicated.

Key responsibilities:
    - Maintain a sorted, unique list of period identifiers
    - Add new periods and ensure uniqueness
    - Validate and clear periods

Examples:
    >>> from fin_statement_model.core.graph.services.period_service import PeriodService
    >>> ps = PeriodService()
    >>> ps.add_periods(["2023", "2022"])
    >>> ps.periods
    ['2022', '2023']
    >>> ps.clear()
    >>> ps.periods
    []
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

    def __init__(self) -> None:
        # Internal, sorted list of unique period identifiers.
        self._periods: list[str] = []

    # ------------------------------------------------------------------
    # Public API --------------------------------------------------------
    # ------------------------------------------------------------------
    @property
    def periods(self) -> List[str]:
        """Return an immutable **sorted** list of period identifiers."""
        # Return a shallow copy to prevent accidental mutation
        return list(self._periods)

    def add_periods(self, periods: list[str]) -> None:
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
    def contains(self, period: str) -> bool:
        """Return ``True`` if *period* is already registered."""
        return period in self._periods

    def clear(self) -> None:
        """Remove all registered periods."""
        self._periods.clear()
