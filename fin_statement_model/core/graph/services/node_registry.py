"""NodeRegistryService – single source of truth for the graph's node registry.

The class maintains the mapping ``name → Node`` and enforces structural
invariants such as:

* unique, non-empty node names,
* presence of all referenced input nodes,
* optional cycle detection before registration.

Because the service works exclusively through callables it can be reused by
any object that behaves like a graph.

Example
~~~~~~~
>>> from fin_statement_model.core.graph import Graph
>>> g = Graph()
>>> g.add_financial_statement_item("Cash", {"2023": 50})
>>> "Cash" in g.nodes  # NodeRegistryService performed the registration
True
"""

from __future__ import annotations

import logging
from typing import Callable, List, TYPE_CHECKING, Dict, Any
from collections import defaultdict

from fin_statement_model.core.nodes import Node, CalculationNode
from fin_statement_model.core.errors import NodeError, CircularDependencyError

__all__: list[str] = ["NodeRegistryService"]

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from fin_statement_model.core.graph.traverser import GraphTraverser


class NodeRegistryService:  # pylint: disable=too-few-public-methods
    """Manage the node mapping and related validation helpers."""

    def __init__(
        self,
        *,
        nodes_dict: Dict[str, Node],
        traverser_provider: Callable[[], "GraphTraverser"],
        add_periods: Callable[[List[str]], None],
    ) -> None:
        # We store a direct reference to the shared node dict so mutations are visible.
        self._nodes = nodes_dict
        self._traverser_provider = traverser_provider
        self._add_periods = add_periods

        # ------------------------------------------------------------------
        # Simple signal/slot mechanism -------------------------------------
        # ------------------------------------------------------------------

        # Map event name -> list of subscriber callables.
        self._callbacks: defaultdict[str, list[Callable[..., None]]] = defaultdict(list)

        # Register internal listeners
        self.on("node_replaced", self._rebind_calculation_inputs)

    # ------------------------------------------------------------------
    # Public helpers (used by other services) ---------------------------
    # ------------------------------------------------------------------
    def add_node_with_validation(
        self,
        node: Node,
        *,
        check_cycles: bool = True,
        validate_inputs: bool = True,
    ) -> Node:
        """Add *node* to the registry while enforcing invariants."""
        # 1. Name validation
        if not node.name or not isinstance(node.name, str):
            raise ValueError("Node name must be a non-empty string")

        # 2. Overwrite warning
        if node.name in self._nodes:
            logger.warning("Overwriting existing node '%s'", node.name)

        # 3. Validate inputs exist
        if validate_inputs and hasattr(node, "inputs") and node.inputs:
            self.validate_node_inputs(node)

        # 4. Optional cycle detection
        if (
            check_cycles
            and hasattr(node, "inputs")
            and node.inputs
            and self._traverser_provider().would_create_cycle(node)
        ):
            cycle_path = None
            for inp in node.inputs:
                if hasattr(inp, "name"):
                    path = self._traverser_provider().find_cycle_path(
                        inp.name, node.name
                    )
                    if path:
                        cycle_path = path
                        break
            raise CircularDependencyError(
                f"Adding node '{node.name}' would create a cycle",
                cycle=cycle_path or [node.name, "...", node.name],
            )

        # 5. Register node
        self._nodes[node.name] = node

        # 6. Period tracking (data nodes)
        if hasattr(node, "values") and isinstance(node.values, dict):
            self._add_periods(list(node.values.keys()))

        logger.debug("Added node '%s' to registry", node.name)
        return node

    def resolve_input_nodes(self, input_names: List[str]) -> List[Node]:
        """Convert a list of *names* into real Node objects with validation."""
        resolved: List[Node] = []
        missing: List[str] = []
        for name in input_names:
            nd = self._nodes.get(name)
            if nd is None:
                missing.append(name)
            else:
                resolved.append(nd)
        if missing:
            raise NodeError(f"Cannot resolve input nodes: missing nodes {missing}")
        return resolved

    def validate_node_inputs(self, node: Node) -> None:  # noqa: D401
        """Raise NodeError if any input reference is missing."""
        if not hasattr(node, "inputs") or not node.inputs:
            return

        missing: List[str] = []
        for inp in node.inputs:
            if hasattr(inp, "name"):
                if inp.name not in self._nodes:
                    missing.append(inp.name)
            elif isinstance(inp, str) and inp not in self._nodes:
                missing.append(inp)

        if missing:
            raise NodeError(
                f"Cannot add node '{node.name}': missing required input nodes {missing}",
                node_id=node.name,
            )

    # ------------------------------------------------------------------
    # Event / callback helpers ------------------------------------------
    # ------------------------------------------------------------------

    def on(self, event: str, fn: Callable[..., None]) -> None:
        """Register *fn* to be invoked whenever *event* is emitted."""
        self._callbacks[event].append(fn)

    def emit(self, event: str, /, **kwargs: Any) -> None:
        """Invoke all subscribers for *event* with keyword arguments.*"""
        for subscriber in self._callbacks.get(event, []):
            try:
                subscriber(**kwargs)
            except Exception as exc:  # pragma: no cover
                logger.exception("Callback for event '%s' failed: %s", event, exc)

    # ------------------------------------------------------------------
    # Internal subscribers ----------------------------------------------
    # ------------------------------------------------------------------

    def _rebind_calculation_inputs(self, *, old: Node, new: Node) -> None:  # noqa: D401
        """Replace references to *old* with *new* inside calculation nodes.

        The operation iterates **only** over calculation nodes to keep the
        complexity O(#calculation_nodes) instead of O(N²) rescans of the
        entire graph.
        """
        from typing import cast

        for nd in self._nodes.values():
            if not isinstance(nd, CalculationNode):
                continue

            # At this point, mypy knows nd is a CalculationNode, so inputs exists.
            if not nd.inputs:
                continue

            # Update by identity comparison for maximum reliability.
            nd.inputs = [new if inp is old else inp for inp in nd.inputs]

            # Clear per-node cache if available so downstream calculations
            # pick up the new dependency immediately.
            if hasattr(nd, "clear_cache"):
                try:
                    cast(Any, nd).clear_cache()
                except Exception:  # pragma: no cover
                    logger.debug(
                        "Failed to clear cache on node '%s' after replacement", nd.name
                    )
