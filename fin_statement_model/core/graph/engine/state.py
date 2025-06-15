"""Immutable snapshot of a fully-validated graph.

Instances are produced exclusively by :pyclass:`GraphBuilder.commit` and can be
shared safely across threads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Tuple

from fin_statement_model.core.graph.domain import Node, PeriodIndex

__all__: list[str] = ["GraphState"]


@dataclass(frozen=True, slots=True)
class GraphState:
    """Immutable graph snapshot containing nodes and periods."""

    nodes: Mapping[str, Node]  # MappingProxyType in practice
    periods: PeriodIndex
    _order: Tuple[str, ...] = field(repr=False, hash=False, default_factory=tuple)

    # Convenience accessors -------------------------------------------
    def __contains__(self, code: str) -> bool:
        return code in self.nodes

    def __getitem__(self, code: str) -> Node:
        return self.nodes[code]

    @property
    def order(self) -> Tuple[str, ...]:
        """Return cached topological order of node codes."""
        return self._order
