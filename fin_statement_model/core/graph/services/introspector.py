"""GraphIntrospector – developer-facing inspection helpers.

Separated from the monolithic ``Graph`` class to keep it below the 300-line
budget and to provide re-usable, graph-agnostic utilities.  The
``GraphIntrospector`` owns non-mutating, read-only diagnostics such as a
compact ``repr`` string and ad-hoc helpers like ``has_cycle``.
"""

from __future__ import annotations

import logging
from typing import Callable, List, TYPE_CHECKING

from fin_statement_model.core.nodes import (
    Node,
    FinancialStatementItemNode,
    is_calculation_node,
)

__all__: list[str] = ["GraphIntrospector"]

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from fin_statement_model.core.graph.traverser import GraphTraverser


class GraphIntrospector:  # pylint: disable=too-few-public-methods
    """Provide lightweight, reusable inspection helpers for graphs.

    The introspector purposefully receives *callables* rather than concrete
    attributes to avoid importing the Graph implementation.

    Args:
        nodes_provider: zero-arg callable returning the ``dict[str, Node]`` registry.
        periods_provider: zero-arg callable returning the sorted list of periods.
        traverser: callable returning the *current* traverser (needed for
            reachability checks; can be a lambda capturing ``self.traverser``).
    """

    def __init__(
        self,
        *,
        nodes_provider: Callable[[], dict[str, Node]],
        periods_provider: Callable[[], List[str]],
        traverser_provider: Callable[[], "GraphTraverser"],
    ) -> None:
        # Runtime import to break circular dependency type-checking.

        self._nodes = nodes_provider
        self._periods = periods_provider
        self._traverser_provider: Callable[[], GraphTraverser] = traverser_provider

    # ------------------------------------------------------------------
    # Developer-friendly __repr__ --------------------------------------
    # ------------------------------------------------------------------
    def make_repr(self) -> str:  # noqa: D401
        """Return the same compact string previously computed in ``Graph.__repr__``."""
        nodes = self._nodes()
        num_nodes = len(nodes)
        periods = self._periods()
        periods_str = ", ".join(map(repr, periods)) if periods else "None"

        fs_item_count = 0
        calc_node_count = 0
        other_node_count = 0
        dependencies_count = 0

        for node in nodes.values():
            if isinstance(node, FinancialStatementItemNode):
                fs_item_count += 1
            elif is_calculation_node(node):
                calc_node_count += 1
                # Prefer get_dependencies when available
                if hasattr(node, "get_dependencies"):
                    try:
                        dependencies_count += len(node.get_dependencies())
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(
                            "Error calling get_dependencies for node '%s': %s",
                            node.name,
                            exc,
                        )
                elif hasattr(node, "inputs"):
                    try:
                        if isinstance(node.inputs, list):
                            dep_names = [
                                inp.name for inp in node.inputs if hasattr(inp, "name")
                            ]
                            dependencies_count += len(dep_names)
                        elif isinstance(node.inputs, dict):
                            dependencies_count += len(node.inputs)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(
                            "Error processing inputs for node '%s': %s", node.name, exc
                        )
            else:
                other_node_count += 1

        parts: list[str] = [
            f"Total Nodes: {num_nodes}",
            f"FS Items: {fs_item_count}",
            f"Calculations: {calc_node_count}",
        ]
        if other_node_count > 0:
            parts.append(f"Other: {other_node_count}")
        parts.append(f"Dependencies: {dependencies_count}")
        parts.append(f"Periods: [{periods_str}]")
        return f"<Graph({', '.join(parts)})>"

    # ------------------------------------------------------------------
    # Cycle helper ------------------------------------------------------
    # ------------------------------------------------------------------
    def has_cycle(self, source_node: Node, target_node: Node) -> bool:  # noqa: D401
        """Return True if an edge from *target_node → source_node* would form a cycle."""
        trav = self._traverser_provider()
        if (
            source_node.name not in self._nodes()
            or target_node.name not in self._nodes()
        ):
            return False
        return trav._is_reachable(
            source_node.name, target_node.name
        )  # pylint: disable=protected-access
