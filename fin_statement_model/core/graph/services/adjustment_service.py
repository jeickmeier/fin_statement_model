"""AdjustmentService – thin wrapper around :class:`~fin_statement_model.core.adjustments.manager.AdjustmentManager`.

The service exposes a **Graph-compatible** API for storing, filtering and
applying discretionary adjustments to calculated node values.  All heavy-
lifting is delegated to the underlying :class:`AdjustmentManager` so the
graph layer can remain agnostic of implementation details.

Basic usage (via the public `Graph` façade):

>>> from fin_statement_model.core.graph import Graph
>>> g = Graph(periods=["2023"])
>>> g.add_financial_statement_item("Revenue", {"2023": 100})
>>> g.add_adjustment(
...     node_name="Revenue",
...     period="2023",
...     value=-10,
...     reason="Correction after audit",
... )
>>> g.get_adjusted_value("Revenue", "2023")
90.0
"""

from __future__ import annotations

from typing import Optional, Set, List
from uuid import UUID, uuid4

from fin_statement_model.core.adjustments.manager import AdjustmentManager
from fin_statement_model.core.adjustments.models import (
    Adjustment,
    AdjustmentType,
    AdjustmentTag,
    AdjustmentFilterInput,
    DEFAULT_SCENARIO,
)

__all__: list[str] = ["AdjustmentService"]


class AdjustmentService:  # pylint: disable=too-few-public-methods
    """Encapsulate adjustment storage and application logic.

    During step 1.2 this is a thin wrapper exposing the same API surface used
    by ``Graph`` so that later migrations are trivial.
    """

    def __init__(self, manager: Optional[AdjustmentManager] = None) -> None:
        self._manager: AdjustmentManager = manager or AdjustmentManager()

    # ------------------------------------------------------------------
    # Delegate helpers (minimal implementations) -----------------------
    # ------------------------------------------------------------------
    # Public API mirrors Graph methods exactly – signatures copied.

    def add_adjustment(
        self,
        node_name: str,
        period: str,
        value: float,
        reason: str,
        adj_type: AdjustmentType = AdjustmentType.ADDITIVE,
        scale: float = 1.0,
        priority: int = 0,
        tags: Optional[Set[AdjustmentTag]] = None,
        scenario: Optional[str] = None,
        user: Optional[str] = None,
        *,
        adj_id: Optional[UUID] = None,
    ) -> UUID:
        """Create an :class:`~fin_statement_model.core.adjustments.models.Adjustment` instance and store it.

        The helper mirrors :pymeth:`Graph.add_adjustment` so external callers
        can interact with either API transparently.
        """
        scenario = scenario or DEFAULT_SCENARIO
        adj = Adjustment(
            id=adj_id or uuid4(),
            node_name=node_name,
            period=period,
            value=value,
            reason=reason,
            type=adj_type,
            scale=scale,
            priority=priority,
            tags=tags or set(),
            scenario=scenario,
            user=user,
        )
        self._manager.add_adjustment(adj)
        return adj.id

    # Basic delegations -------------------------------------------------
    def remove_adjustment(self, adj_id: UUID) -> bool:  # noqa: D401
        return self._manager.remove_adjustment(adj_id)

    def get_adjustments(
        self, node_name: str, period: str, *, scenario: Optional[str] = None
    ) -> List[Adjustment]:
        return self._manager.get_adjustments(
            node_name, period, scenario=scenario or DEFAULT_SCENARIO
        )

    def get_filtered_adjustments(
        self, node_name: str, period: str, filter_input: AdjustmentFilterInput = None
    ) -> List[Adjustment]:
        return self._manager.get_filtered_adjustments(node_name, period, filter_input)

    def apply_adjustments(
        self, base_value: float, adjustments: List[Adjustment]
    ) -> tuple[float, bool]:
        return self._manager.apply_adjustments(base_value, adjustments)

    def list_all_adjustments(self) -> List[Adjustment]:  # noqa: D401
        return self._manager.get_all_adjustments()

    def clear_all(self) -> None:  # noqa: D401
        self._manager.clear_all()

    def was_adjusted(
        self, node_name: str, period: str, filter_input: AdjustmentFilterInput = None
    ) -> bool:
        """Return True if any adjustments match the criteria (cheap helper)."""
        return bool(
            self._manager.get_filtered_adjustments(node_name, period, filter_input)
        )
