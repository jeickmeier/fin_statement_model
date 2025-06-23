"""Adjustment-related graph operations.

AdjustmentMixin delegates all discretionary adjustment API calls to the underlying adjustment service.
This allows the graph to support scenario analysis and what-if modeling by applying, removing, and listing
adjustments to node values for specific periods and scenarios.

Key responsibilities:
    - Add, remove, and list adjustments for nodes and periods
    - Retrieve adjusted values and check if a value was adjusted
    - List all adjustments and filter by scenario or tags

Examples:
    >>> from fin_statement_model.core.graph import Graph
    >>> g = Graph(periods=["2023"])
    >>> _ = g.add_financial_statement_item("Revenue", {"2023": 100.0})
    >>> g.add_adjustment("Revenue", "2023", 10.0, reason="Scenario boost")
    ... # doctest: +SKIP
    >>> g.get_adjusted_value("Revenue", "2023")
    ... # doctest: +SKIP
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fin_statement_model.core.adjustments.models import (
    AdjustmentFilterInput,
    AdjustmentTag,
    AdjustmentType,
)

if TYPE_CHECKING:
    from uuid import UUID

__all__: list[str] = ["AdjustmentMixin"]


class AdjustmentMixin:
    """Delegate discretionary-adjustment API calls to the underlying service."""

    # Public façade -----------------------------------------------------------
    def get_adjusted_value(
        self,
        node_name: str,
        period: str,
        filter_input: AdjustmentFilterInput | None = None,
        *,
        return_flag: bool = False,
    ) -> Any:
        base_value = self.calculate(node_name, period)  # type: ignore[attr-defined]
        adjustments = self._adjustment_service.get_filtered_adjustments(  # type: ignore[attr-defined]
            node_name,
            period,
            filter_input,
        )
        adjusted_value, was_adjusted = self._adjustment_service.apply_adjustments(  # type: ignore[attr-defined]
            base_value,
            adjustments,
        )
        return (adjusted_value, was_adjusted) if return_flag else adjusted_value

    # Convenience wrappers -----------------------------------------------------
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
    ) -> Any:
        return self._adjustment_service.add_adjustment(  # type: ignore[attr-defined]
            node_name,
            period,
            value,
            reason,
            adj_type,
            scale,
            priority,
            tags,
            scenario,
            user,
            adj_id=adj_id,
        )

    def remove_adjustment(self, adj_id: UUID) -> Any:
        return self._adjustment_service.remove_adjustment(adj_id)  # type: ignore[attr-defined]

    def get_adjustments(
        self,
        node_name: str,
        period: str,
        *,
        scenario: str | None = None,
    ) -> Any:
        return self._adjustment_service.get_adjustments(  # type: ignore[attr-defined]
            node_name,
            period,
            scenario=scenario,
        )

    def list_all_adjustments(self) -> Any:
        return self._adjustment_service.list_all_adjustments()  # type: ignore[attr-defined]

    def was_adjusted(
        self,
        node_name: str,
        period: str,
        filter_input: AdjustmentFilterInput | None = None,
    ) -> Any:
        return self._adjustment_service.was_adjusted(  # type: ignore[attr-defined]
            node_name,
            period,
            filter_input,
        )
