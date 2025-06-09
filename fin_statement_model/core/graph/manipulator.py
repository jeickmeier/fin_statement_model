"""Provide graph manipulation utilities.

This module defines the GraphManipulator class, encapsulating node-level mutation helpers for Graph.
"""

import logging
from typing import Optional, Any, cast
from fin_statement_model.core.errors import NodeError
from fin_statement_model.core.nodes import Node, CalculationNode

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

    def _update_calculation_nodes(self) -> None:
        """Refresh input references for all calculation nodes after structure changes.

        This method re-resolves `input_names` to current Node objects and clears
        individual node caches.

        Returns:
            None
        """
        for nd in self.graph._nodes.values():
            if (
                isinstance(nd, CalculationNode)
                and hasattr(nd, "input_names")
                and nd.input_names
            ):
                try:
                    resolved_inputs: list[Node] = []
                    for name in nd.input_names:
                        input_node = self.get_node(name)
                        if input_node is None:
                            raise NodeError(
                                f"Input node '{name}' not found for calculation node '{nd.name}'"
                            )
                        resolved_inputs.append(input_node)
                    nd.inputs = resolved_inputs
                    if hasattr(nd, "clear_cache"):
                        nd.clear_cache()
                except NodeError:
                    logger.exception(f"Error updating inputs for node '{nd.name}'")
                except AttributeError:
                    logger.warning(
                        f"Node '{nd.name}' has input_names but no 'inputs' attribute to update."
                    )

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
        self.remove_node(node_name)
        self.add_node(new_node)

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
        self._update_calculation_nodes()

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
