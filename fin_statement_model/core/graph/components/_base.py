"""Foundational mix-in for the public :class:`~fin_statement_model.core.graph.graph.Graph`.

`GraphBaseMixin` owns the constructor and the core helpers that other mix-ins
(building on node operations, calculation, traversal, etc.) rely on.  All state
attributes are created here so the specialised mix-ins can assume their
existence.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Optional, cast

from fin_statement_model.core.adjustments.manager import AdjustmentManager
from fin_statement_model.core.errors import CircularDependencyError, NodeError
from fin_statement_model.core.graph.manipulator import GraphManipulator
from fin_statement_model.core.graph.services import (
    AdjustmentService,
    CalculationEngine,
    PeriodService,
)
from fin_statement_model.core.graph.traverser import GraphTraverser
from fin_statement_model.core.node_factory import NodeFactory
from fin_statement_model.core.nodes import Node

logger = logging.getLogger(__name__)

__all__: list[str] = ["GraphBaseMixin"]


class GraphBaseMixin:
    """Provide constructor and generic helpers shared by all graph mix-ins."""

    # ---------------------------------------------------------------------
    # Construction & core state
    # ---------------------------------------------------------------------
    def __init__(
        self,
        periods: Optional[list[str]] = None,
        *,
        calc_engine_cls: type[CalculationEngine] = CalculationEngine,
        period_service_cls: type[PeriodService] = PeriodService,
        adjustment_service_cls: type[AdjustmentService] = AdjustmentService,
    ) -> None:
        # NOTE: we do **not** call super().__init__() on purpose; this mix-in
        # owns the concrete initialisation logic.

        self._nodes: dict[str, Node] = {}

        self._cache: dict[str, dict[str, float]] = {}
        self._node_factory: NodeFactory = NodeFactory()

        # Service layer ----------------------------------------------------
        self._period_service = period_service_cls()

        self._calc_engine = calc_engine_cls(
            node_resolver=cast(Callable[[str], Node], self.get_node),
            period_provider=lambda: self._period_service.periods,
            node_names_provider=lambda: list(self._nodes.keys()),
            cache=self._cache,
            node_factory=self._node_factory,
            nodes_dict=self._nodes,
            add_node_with_validation=lambda node: self._add_node_with_validation(node),
            resolve_input_nodes=self._resolve_input_nodes,
            add_periods=self.add_periods,
        )

        self.adjustment_manager = AdjustmentManager()
        self._adjustment_service = adjustment_service_cls(
            manager=self.adjustment_manager
        )

        if periods:
            if not isinstance(periods, list):
                raise TypeError("Initial periods must be a list")
            self._period_service.add_periods(periods)

        # Sub-APIs ---------------------------------------------------------
        self.manipulator = GraphManipulator(self)
        self.traverser = GraphTraverser(self)

    # ------------------------------------------------------------------
    # Simple public helpers / properties
    # ------------------------------------------------------------------
    @property
    def nodes(self) -> dict[str, Node]:
        """Dictionary mapping node names to :class:`~fin_statement_model.core.nodes.Node`."""
        return self._nodes

    @property
    def periods(self) -> list[str]:
        """Return the current, sorted list of period identifiers managed by the graph."""
        return self._period_service.periods

    # Delegation wrappers --------------------------------------------------
    def add_periods(self, periods: list[str]) -> None:
        """Add new period identifiers via :class:`~fin_statement_model.core.graph.services.PeriodService`."""
        self._period_service.add_periods(periods)

    # ------------------------------------------------------------------
    # Cache & reset utilities
    # ------------------------------------------------------------------
    def clear_calculation_cache(self) -> None:
        """Invalidate the central calculation cache only."""
        self._calc_engine.clear_all()
        logger.debug("Cleared graph calculation cache via CalculationEngine.")

    def clear_all_caches(self) -> None:
        """Clear calculation cache **and** any per-node caches."""
        for node in self.nodes.values():
            if hasattr(node, "clear_cache"):
                try:
                    node.clear_cache()
                except Exception:  # pragma: no cover – non-fatal best-effort
                    continue
        self.clear_calculation_cache()

    def clear(self) -> None:
        """Fully reset the graph to an empty state (nodes, periods, adjustments, caches)."""
        self._nodes = {}
        self._period_service.clear()
        self._cache.clear()
        self.adjustment_manager.clear_all()
        logger.info("Graph cleared: nodes, periods, adjustments, and caches reset.")

    # ------------------------------------------------------------------
    # Internal helpers shared by other mix-ins
    # ------------------------------------------------------------------
    def _add_node_with_validation(
        self,
        node: Node,
        *,
        check_cycles: bool = True,
        validate_inputs: bool = True,
    ) -> Node:
        if not node.name or not isinstance(node.name, str):
            raise ValueError("Node name must be a non-empty string")

        if node.name in self._nodes:
            logger.warning("Overwriting existing node '%s'", node.name)

        if validate_inputs and hasattr(node, "inputs") and node.inputs:
            self._validate_node_inputs(node)

        if (
            check_cycles
            and hasattr(node, "inputs")
            and node.inputs
            and self.traverser.would_create_cycle(node)
        ):
            cycle_path = None
            for input_node in node.inputs:
                if hasattr(input_node, "name"):
                    path = self.traverser.find_cycle_path(input_node.name, node.name)
                    if path:
                        cycle_path = path
                        break
            raise CircularDependencyError(
                f"Adding node '{node.name}' would create a cycle",
                cycle=cycle_path or [node.name, "...", node.name],
            )

        self._nodes[node.name] = node

        if hasattr(node, "values") and isinstance(node.values, dict):
            self.add_periods(list(node.values.keys()))

        logger.debug("Added node '%s' to graph", node.name)
        return node

    def _validate_node_inputs(self, node: Node) -> None:
        missing_inputs: list[str] = []
        if hasattr(node, "inputs") and node.inputs:
            for input_node in node.inputs:
                if hasattr(input_node, "name") and input_node.name not in self._nodes:
                    missing_inputs.append(input_node.name)
        if missing_inputs:
            raise NodeError(
                (
                    f"Cannot add node '{node.name}': missing required input nodes "
                    f"{missing_inputs}"
                ),
                node_id=node.name,
            )

    def _resolve_input_nodes(self, input_names: list[str]) -> list[Node]:
        resolved_inputs: list[Node] = []
        missing: list[str] = []
        for name in input_names:
            node = self._nodes.get(name)
            if node is None:
                missing.append(name)
            else:
                resolved_inputs.append(node)
        if missing:
            raise NodeError(f"Cannot resolve input nodes: missing nodes {missing}")
        return resolved_inputs

    # ------------------------------------------------------------------
    # Minimal query required by CalculationEngine during construction
    # ------------------------------------------------------------------
    def get_node(self, name: str) -> Optional[Node]:
        """Lightweight resolver used by :pyclass:`CalculationEngine`."""
        return self._nodes.get(name)
