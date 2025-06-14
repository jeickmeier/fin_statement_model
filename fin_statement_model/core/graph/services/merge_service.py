"""MergeService – reusable helper that implements *graph-to-graph* merging.

The service operates purely through dependency-injected callables so it
remains agnostic of the concrete `Graph` implementation.  Typical tasks
performed during a merge include:

1. Union of period lists while maintaining sort order.
2. Addition of new nodes absent from the target graph.
3. In-place update of value dictionaries on nodes that exist in both graphs.

Example
~~~~~~~
>>> from fin_statement_model.core.graph import Graph
>>> base = Graph(periods=["2023"])
>>> other = Graph(periods=["2023", "2024"])
>>> _ = other.add_financial_statement_item("Revenue", {"2024": 120})
>>> base.merge_from(other)  # internally delegates to MergeService
(1, 0)  # nodes_added, nodes_updated
"""

from __future__ import annotations

import logging
from typing import Callable, Optional, Any

from fin_statement_model.core.nodes import Node

__all__: list[str] = ["MergeService"]

logger = logging.getLogger(__name__)


class MergeService:  # pylint: disable=too-few-public-methods
    """Provide a *graph-agnostic* merge helper.

    The service assumes two graph-like objects that expose the following
    attributes / behaviours:

    • ``periods`` – a *list[str]* (property or attribute) on *both* graphs.
    • ``nodes`` – a *dict[str, Node]* mapping on *both* graphs.

    Args:
        add_periods: Callable to add new periods to the target graph.
        periods_provider: Returns current periods of the target graph.
        node_getter: Return a node by name from the target graph.
        add_node: Add a fully-constructed Node to the target graph.
        nodes_provider: Return nodes dict of the target graph (for iteration).
    """

    def __init__(
        self,
        *,
        add_periods: Callable[[list[str]], None],
        periods_provider: Callable[[], list[str]],
        node_getter: Callable[[str], Optional[Node]],
        add_node: Callable[[Node], None],
        nodes_provider: Callable[[], dict[str, Node]],
    ) -> None:
        self._add_periods = add_periods
        self._periods = periods_provider
        self._get_node = node_getter
        self._add_node = add_node
        self._nodes = nodes_provider  # returns mutable dict

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def merge_from(self, other_graph: Any) -> tuple[int, int]:
        """Merge *other_graph* into the target graph (self collaborates).

        Returns a tuple ``(nodes_added, nodes_updated)`` for instrumentation.
        For logic see original ``Graph.merge_from`` implementation – almost a
        verbatim copy but rewritten to avoid direct ``Graph`` imports.
        """
        logger.info("Starting merge from graph %%s", other_graph)

        # 1. Periods -------------------------------------------------------
        other_periods = getattr(other_graph, "periods", [])
        if not isinstance(other_periods, list):  # defensive
            other_periods = list(other_periods)
        new_periods = [p for p in other_periods if p not in self._periods()]
        if new_periods:
            self._add_periods(new_periods)
            logger.debug("Merged periods: %s", new_periods)

        # 2. Nodes ---------------------------------------------------------
        nodes_added = 0
        nodes_updated = 0
        other_nodes = getattr(other_graph, "nodes", {})
        if not isinstance(other_nodes, dict):  # pragma: no cover – defensive
            logger.warning("other_graph.nodes is not a dict – skipping merge")
            return (nodes_added, nodes_updated)

        for node_name, other_node in other_nodes.items():
            existing_node = self._get_node(node_name)
            if existing_node is not None:
                # Node exists – try to merge .values if both are dicts
                if (
                    hasattr(existing_node, "values")
                    and hasattr(other_node, "values")
                    and isinstance(getattr(existing_node, "values", None), dict)
                    and isinstance(getattr(other_node, "values", None), dict)
                ):
                    try:
                        existing_node.values.update(other_node.values)
                        nodes_updated += 1
                        logger.debug("Merged values into existing node '%s'", node_name)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(
                            "Could not merge values for node '%s': %s", node_name, exc
                        )
            else:
                try:
                    # Add node directly; assumes immutability or safe sharing.
                    self._add_node(other_node)
                    nodes_added += 1
                except Exception as exc:  # noqa: BLE001
                    logger.exception(
                        "Failed to add new node '%s' during merge: %s", node_name, exc
                    )

        logger.info(
            "Merge complete: nodes_added=%s, nodes_updated=%s",
            nodes_added,
            nodes_updated,
        )
        return (nodes_added, nodes_updated)
