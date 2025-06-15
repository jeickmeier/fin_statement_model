"""Mutable builder for constructing or editing a graph before freezing.

All validation happens on *commit()*; mutation helpers keep minimal logic.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Dict, Iterable, Mapping

from fin_statement_model.core.graph.domain import (
    Node,
    NodeKind,
    Period,
    PeriodIndex,
    parse_inputs,
)
from fin_statement_model.core.graph.engine.topology import toposort

if TYPE_CHECKING:  # pragma: no cover
    from .state import GraphState

__all__: list[str] = ["GraphBuilder"]


class GraphBuilder:
    """Incrementally build a graph; cheap to discard and recreate."""

    def __init__(self, *, base: "GraphState" | None = None):
        self._nodes: Dict[str, Node] = dict(base.nodes) if base else {}
        self._periods: PeriodIndex = base.periods.clone() if base else PeriodIndex()

    # ------------------------------------------------------------------
    # Node operations ---------------------------------------------------
    # ------------------------------------------------------------------
    def add_node(
        self,
        *,
        code: str,
        formula: str | None = None,
        values: Mapping[str, float] | None = None,
    ) -> None:
        if code in self._nodes:
            raise ValueError(f"Node {code!r} already exists.")
        kind = NodeKind.FORMULA if formula else NodeKind.INPUT
        deps = parse_inputs(formula) if formula else frozenset()
        self._nodes[code] = Node(
            code=code,
            kind=kind,
            formula=formula,
            inputs=deps,
            data=MappingProxyType(values or {}),
        )

    def remove_node(self, code: str) -> None:
        if code not in self._nodes:
            raise KeyError(code)
        del self._nodes[code]

    # ------------------------------------------------------------------
    # Period operations -------------------------------------------------
    # ------------------------------------------------------------------
    def add_periods(self, periods: Iterable[str | Period]) -> None:
        for p in periods:
            self._periods.add(p if isinstance(p, Period) else Period.parse(str(p)))

    # ------------------------------------------------------------------
    # Data value operations --------------------------------------------
    # ------------------------------------------------------------------
    def set_node_value(
        self, code: str, period: str, value: float, *, replace_existing: bool = False
    ) -> None:
        """Set or update a single value for an **input** node.

        If *code* refers to a formula/aggregate node a :class:`TypeError` is
        raised because their values are derived during calculation.
        """
        if code not in self._nodes:
            raise KeyError(code)

        node = self._nodes[code]
        if node.kind is not NodeKind.INPUT:
            raise TypeError("Cannot assign values to non-input nodes.")

        # Create a *new* data mapping (copy-on-write) ------------------
        data_dict = dict(node.data)
        if not replace_existing and period in data_dict:
            raise ValueError(
                f"Value for node {code!r} in period {period!r} already exists."
            )

        data_dict[period] = float(value)

        # Replace node --------------------------------------------------
        self._nodes[code] = Node(
            code=node.code,
            kind=node.kind,
            formula=None,
            inputs=node.inputs,
            data=MappingProxyType(data_dict),
        )

    def replace_node(
        self,
        code: str,
        *,
        formula: str | None = None,
        values: Mapping[str, float] | None = None,
    ) -> None:
        """Replace existing node *in-place* (keeps dependencies consistent)."""
        if code not in self._nodes:
            raise KeyError(code)

        # Remove old node and re-add with new definition
        del self._nodes[code]
        self.add_node(code=code, formula=formula, values=values)

    # ------------------------------------------------------------------
    # Finalise ----------------------------------------------------------
    # ------------------------------------------------------------------
    def commit(self) -> "GraphState":
        order = toposort(self._nodes)
        # Freeze nodes mapping and periods ---------------------------------
        nodes_proxy: Mapping[str, Node] = MappingProxyType(self._nodes)
        frozen_periods = self._periods.freeze()
        from .state import GraphState  # local import (safe import time)

        return GraphState(nodes=nodes_proxy, periods=frozen_periods, _order=order)
