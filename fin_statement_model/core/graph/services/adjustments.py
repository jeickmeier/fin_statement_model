"""AdjustmentService – store & query discretionary adjustments (v2).

# mypy: ignore-errors

Purely in-memory storage; persistence and complex filtering are handled by
higher-level layers.  This service is intentionally *thin* so that it can be
replaced by a DB-backed implementation without touching the engine.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Iterable, Set

from fin_statement_model.core.graph.domain.adjustment import (
    Adjustment,
    AdjustmentTag,
)

# Predicate type alias
FilterPredicate = Callable[[Adjustment], bool]

__all__: list[str] = ["AdjustmentService"]


class AdjustmentService:
    """Store :class:`Adjustment` objects and provide simple lookups."""

    def __init__(self) -> None:
        # Nested mapping node_code -> period_str -> list[Adjustment]
        self._store: dict[str, dict[str, list[Adjustment]]] = defaultdict(
            lambda: defaultdict(list)
        )

    # ------------------------------------------------------------------
    # Mutating API
    # ------------------------------------------------------------------
    def add(self, adj: Adjustment) -> None:
        """Add *adj* to the store (no uniqueness enforced)."""
        self._store[adj.node][adj.period].append(adj)

    def add_many(self, adjustments: Iterable[Adjustment]) -> None:
        for adj in adjustments:
            self.add(adj)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    def list_all(self) -> list[Adjustment]:
        """Return *all* adjustments currently stored (unordered)."""
        return [
            adj
            for node_map in self._store.values()
            for per_list in node_map.values()
            for adj in per_list
        ]

    def get_for(self, node: str, period: str) -> list[Adjustment]:
        return list(self._store.get(node, {}).get(period, []))

    def clear(self) -> None:
        self._store.clear()

    # ------------------------------------------------------------------
    # Filtering & application helpers ----------------------------------
    # ------------------------------------------------------------------
    # Basic filtering API replicates subset of v1 AdjustmentFilter ----------------
    def get_filtered(
        self,
        node: str,
        period: str,
        filter_input: Any = None,
    ) -> list[Adjustment]:
        """Return adjustments for *node* & *period* that satisfy *filter_input*."""

        adjs = self.get_for(node, period)
        if not filter_input:
            return adjs

        # Convert filter_input into predicate --------------------------------
        pred: FilterPredicate

        from fin_statement_model.core.adjustments.models import (
            AdjustmentFilter,
        )  # lazy import

        if isinstance(filter_input, AdjustmentFilter):
            pred = filter_input.matches
        elif callable(filter_input):
            pred = filter_input
        else:  # assume tag set
            tags: Set[AdjustmentTag] = set(filter_input)  # type: ignore[arg-type]

            def _tag_pred(adj: Adjustment) -> bool:
                return bool(adj.tags & tags)

            pred = _tag_pred

        return [a for a in adjs if pred(a)]

    # ------------------------------------------------------------------
    def apply_adjustments(self, base_value: float, adjustments: list[Adjustment]):
        """Return adjusted value + bool flag if changed."""
        if not adjustments:
            return base_value, False

        # Sort by priority ascending ------------------------------------
        sorted_adj = sorted(adjustments, key=lambda a: a.priority)
        value = base_value
        for adj in sorted_adj:
            value = self._apply_one(value, adj)
        return value, value != base_value

    @staticmethod
    def _apply_one(base: float, adj: Adjustment) -> float:
        return adj.type.apply(base, adj.value, adj.scale)
