"""PeriodService – canonicalise and manage graph periods (v2).

# mypy: ignore-errors

Acts as a lightweight wrapper around :class:`PeriodIndex`.
"""

from __future__ import annotations

from typing import Iterable, List

from fin_statement_model.core.time.period import Period, PeriodIndex

__all__: list[str] = ["PeriodService"]


class PeriodService:
    """Maintain a sorted, duplicate-free collection of periods."""

    def __init__(self, initial: Iterable[str | Period] | None = None) -> None:
        self._index = PeriodIndex()
        if initial is not None:
            self.add_many(initial)

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------
    def add(self, period: str | Period) -> None:
        self._index.add(
            period if isinstance(period, Period) else Period.parse(str(period))
        )

    def add_many(self, periods: Iterable[str | Period]) -> None:
        for p in periods:
            self.add(p)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------
    @property
    def periods(self) -> List[str]:
        """Return periods **as strings** in chronological order."""
        return [str(p) for p in self._index]

    def __contains__(self, period: str | Period) -> bool:
        target = str(period) if isinstance(period, Period) else period
        return any(str(p) == target for p in self._index)

    def __len__(self) -> int:
        return len(self._index)

    def __iter__(self):
        return iter(self.periods)
