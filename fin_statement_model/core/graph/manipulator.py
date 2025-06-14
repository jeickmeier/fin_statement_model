"""Utilities for mutating a :class:`~fin_statement_model.core.graph.graph.Graph` instance.

The *Graph* class exposes a :pyattr:`graph.manipulator <fin_statement_model.core.graph.graph.Graph.manipulator>`
attribute that is an instance of :class:`GraphManipulator`.  The manipulator
groups together all *write* operations on the graph – adding, removing or
replacing nodes, updating values, and clearing caches – so that the rest of the
code base can rely on a single consistency layer.

Key responsibilities
===================
1. Ensure new nodes are properly registered on the graph.
2. Keep calculation-node input references up-to-date after structural changes.
3. Invalidate per-node and global caches whenever something that could affect
   results is modified.

Although you *can* instantiate `GraphManipulator` directly, in normal usage you
retrieve it from an existing graph:

Examples
~~~~~~~~
>>> from fin_statement_model.core.graph import Graph
>>> g = Graph(periods=["2023"])
>>> _ = g.add_financial_statement_item("Revenue", {"2023": 100.0})
>>> g.calculate("Revenue", "2023")
100.0

Now update the value via the manipulator and observe caches being cleared:

>>> g.manipulator.set_value("Revenue", "2023", 110.0)
>>> g.calculate("Revenue", "2023")
110.0

The manipulator is *internal API*; it is documented here solely to aid
contributors.  End-users should prefer the higher-level convenience methods on
`Graph` itself whenever possible.

# pragma: no cover
"""

import logging
from typing import Optional, Any, cast
from fin_statement_model.core.errors import NodeError
from fin_statement_model.core.nodes import Node

logger = logging.getLogger(__name__)


class GraphManipulator:
    """Encapsulate node-level mutation helpers for Graph.

    Attributes:
        graph: The Graph instance this manipulator operates on.
    """

    def __init__(self, graph: Any) -> None:
        """Initialize the GraphManipulator with a Graph reference.

        Args:
            graph: The Graph instance to manipulate.
        """
        self.graph = graph

    def add_node(self, node: Node) -> None:
        """Add a node to the graph, replacing any existing node with the same name.

        Args:
            node: The Node instance to add.

        Returns:
            None

        Raises:
            TypeError: If the provided object is not a Node instance.

        Examples:
            >>> manipulator.add_node(node)
        """
        if not isinstance(node, Node):
            raise TypeError(f"Object {node} is not a valid Node instance.")
        if self.has_node(node.name):
            self.remove_node(node.name)
        self.graph._nodes[node.name] = node

    def get_node(self, name: str) -> Optional[Node]:
        """Retrieve a node from the graph by its unique name.

        Args:
            name: The unique node name to retrieve.

        Returns:
            The Node instance if found, else None.

        Examples:
            >>> manipulator.get_node("Revenue")
        """
        return cast(Optional[Node], self.graph._nodes.get(name))

    def replace_node(self, node_name: str, new_node: Node) -> None:
        """Replace an existing node with a new one, ensuring consistency.

        Args:
            node_name: Name of the node to replace.
            new_node: The new Node instance; its name must match `node_name`.

        Returns:
            None

        Raises:
            NodeError: If `node_name` does not exist.
            ValueError: If `new_node.name` does not match `node_name`.

        Examples:
            >>> manipulator.replace_node("Revenue", updated_node)
        """
        if not self.has_node(node_name):
            raise NodeError(f"Node '{node_name}' not found, cannot replace.")
        if node_name != new_node.name:
            raise ValueError(
                "New node name must match the name of the node being replaced."
            )
        # ------------------------------------------------------------------
        # Emit replacement event *before* the old reference disappears so
        # subscribers can still access the original node object.
        # ------------------------------------------------------------------
        old_node = self.graph._nodes[node_name]

        registry = getattr(self.graph, "_registry_service", None)
        if registry is not None and hasattr(registry, "emit"):
            registry.emit("node_replaced", old=old_node, new=new_node)

        if registry is not None:
            # Replace node via registry service so name validation & period tracking
            # remain centralised. We skip cycle detection and input validation as the
            # node already existed under the same name, hence the overall structure
            # cannot introduce a new cycle by substitution alone.
            registry.add_node_with_validation(
                new_node,
                check_cycles=False,
                validate_inputs=False,
            )
        else:  # Fallback: direct dictionary replacement (should not happen in prod)
            self.graph._nodes[node_name] = new_node

        # Clearing calculation cache is delegated to subscribers; however we
        # explicitly clear central cache to avoid stale values referencing the
        # old node implementation.
        if hasattr(self.graph, "clear_calculation_cache"):
            self.graph.clear_calculation_cache()

    def has_node(self, node_id: str) -> bool:
        """Check if a node with the given ID exists.

        Args:
            node_id: The name of the node to check.

        Returns:
            True if the node exists, False otherwise.

        Examples:
            >>> manipulator.has_node("Revenue")
        """
        return node_id in self.graph._nodes

    def remove_node(self, node_name: str) -> None:
        """Remove a node from the graph and update calculation nodes.

        Args:
            node_name: The name of the node to remove.

        Returns:
            None

        Examples:
            >>> manipulator.remove_node("OldItem")
        """
        if not self.has_node(node_name):
            return
        self.graph._nodes.pop(node_name, None)

        # Clear central calculation cache to ensure no stale values reference the
        # removed node.
        if hasattr(self.graph, "clear_calculation_cache"):
            self.graph.clear_calculation_cache()

    def set_value(self, node_id: str, period: str, value: float) -> None:
        """Set the value for a specific node and period, clearing all caches.

        Args:
            node_id: The name of the node.
            period: The time period identifier.
            value: The numeric value to assign.

        Returns:
            None

        Raises:
            ValueError: If `period` is not recognized by the graph.
            NodeError: If the node does not exist.
            TypeError: If the node does not support setting a value.

        Examples:
            >>> manipulator.set_value("Revenue", "2023", 1100.0)
        """
        if period not in self.graph._periods:
            raise ValueError(f"Period '{period}' not in graph periods")
        nd = self.get_node(node_id)
        if not nd:
            raise NodeError(message=f"Node '{node_id}' does not exist", node_id=node_id)
        if not hasattr(nd, "set_value"):
            raise TypeError(
                f"Node '{node_id}' of type {type(nd).__name__} does not support set_value."
            )
        nd.set_value(period, value)
        self.graph.clear_all_caches()

    def clear_all_caches(self) -> None:
        """Clear caches associated with individual nodes in the graph.

        Returns:
            None

        Examples:
            >>> manipulator.clear_all_caches()
        """
        for nd in self.graph._nodes.values():
            if hasattr(nd, "clear_cache"):
                nd.clear_cache()
