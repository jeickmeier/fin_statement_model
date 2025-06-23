"""AdjustmentService stub - wraps ``AdjustmentManager`` for Graph refactor.

AdjustmentService encapsulates adjustment storage and application logic for the graph. It provides methods
for adding, removing, and listing adjustments, as well as applying adjustments to node values for scenario
analysis and what-if modeling. All adjustment logic is delegated here from the Graph and its mix-ins.

Key responsibilities:
    - Add, remove, and list adjustments for nodes and periods
    - Apply adjustments to node values
    - Retrieve and filter adjustments by scenario or tags
    - Clear all adjustments
    - Check if a value was adjusted

Examples:
    >>> from fin_statement_model.core.graph.services.adjustment_service import AdjustmentService
    >>> service = AdjustmentService()
    >>> adj_id = service.add_adjustment("Revenue", "2023", 10.0, reason="Scenario boost")
    >>> service.list_all_adjustments()  # doctest: +SKIP
"""

from __future__ import annotations

from uuid import UUID, uuid4

from fin_statement_model.core.adjustments.manager import AdjustmentManager
from fin_statement_model.core.adjustments.models import (
    DEFAULT_SCENARIO,
    Adjustment,
    AdjustmentFilterInput,
    AdjustmentTag,
    AdjustmentType,
)

__all__: list[str] = ["AdjustmentService"]


class AdjustmentService:  # pylint: disable=too-few-public-methods
    """Encapsulate adjustment storage and application logic.

    During step 1.2 this is a thin wrapper exposing the same API surface used
    by ``Graph`` so that later migrations are trivial.
    """

    def __init__(self, manager: AdjustmentManager | None = None) -> None:
        """Create a new AdjustmentService.

        Args:
            manager: Optional pre-configured :class:`AdjustmentManager` to use.
                When *None*, a fresh instance is created.
        """
        self._manager: AdjustmentManager = manager or AdjustmentManager()

    # ------------------------------------------------------------------
    # Delegate helpers (minimal implementations) -----------------------
    # ------------------------------------------------------------------
    # Public API mirrors Graph methods exactly - signatures copied.

    def add_adjustment(
        self,
        node_name: str,
        period: str,
        value: float,
        reason: str,
        adj_type: AdjustmentType = AdjustmentType.ADDITIVE,
        scale: float = 1.0,
        priority: int = 0,
        tags: set[AdjustmentTag] | None = None,
        scenario: str | None = None,
        user: str | None = None,
        *,
        adj_id: UUID | None = None,
    ) -> UUID:
        """Create ``Adjustment`` and add to manager (stub)."""
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
    def remove_adjustment(self, adj_id: UUID) -> bool:
        """Remove an adjustment from the manager.

        Args:
            adj_id: Unique identifier of the adjustment to remove.

        Returns:
            True if an adjustment with *adj_id* was found and removed, False otherwise.
        """
        return self._manager.remove_adjustment(adj_id)

    def get_adjustments(self, node_name: str, period: str, *, scenario: str | None = None) -> list[Adjustment]:
        """Return all adjustments for *node_name*/*period*.

        Args:
            node_name: Canonical node identifier (e.g. "revenue").
            period: Period label (e.g. "2024").
            scenario: Scenario name - defaults to ``"default"`` when *None*.

        Returns:
            A list of matching :class:`fin_statement_model.core.adjustments.models.Adjustment` instances.
        """
        return self._manager.get_adjustments(node_name, period, scenario=scenario or DEFAULT_SCENARIO)

    def get_filtered_adjustments(
        self, node_name: str, period: str, filter_input: AdjustmentFilterInput = None
    ) -> list[Adjustment]:
        """Return adjustments matching an *AdjustmentFilterInput*.

        Args:
            node_name: Target node name.
            period: Period identifier.
            filter_input: Additional filter specifying scenarios/tags.

        Returns:
            List of adjustments that satisfy all filter criteria.
        """
        return self._manager.get_filtered_adjustments(node_name, period, filter_input)

    def apply_adjustments(self, base_value: float, adjustments: list[Adjustment]) -> tuple[float, bool]:
        """Apply *adjustments* to *base_value*.

        Args:
            base_value: Original numeric value before adjustments.
            adjustments: Sequence of adjustments to apply.

        Returns:
            Tuple of ``(adjusted_value, was_adjusted)`` where *was_adjusted* is
            True if at least one adjustment modified the value.
        """
        return self._manager.apply_adjustments(base_value, adjustments)

    def list_all_adjustments(self) -> list[Adjustment]:
        """Return **all** adjustments currently stored in the manager."""
        return self._manager.get_all_adjustments()

    def clear_all(self) -> None:
        """Remove **every** adjustment from the underlying manager."""
        self._manager.clear_all()

    def was_adjusted(self, node_name: str, period: str, filter_input: AdjustmentFilterInput = None) -> bool:
        """Return True if any adjustments match the criteria (cheap helper)."""
        return bool(self._manager.get_filtered_adjustments(node_name, period, filter_input))
