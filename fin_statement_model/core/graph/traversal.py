"""Provides graph traversal and validation capabilities as a mixin class.

This mixin is intended to be used by the main `Graph` class. It encapsulates
operations related to traversing the graph, such as finding dependencies,
performing topological sorts, and detecting cycles. It assumes the presence of
a `nodes` dictionary and methods like `get_node` and `has_node` in the class
it's mixed into.
"""

import logging
from typing import Optional, TYPE_CHECKING
from fin_statement_model.core.errors import NodeError
from collections import deque

if TYPE_CHECKING:
    from fin_statement_model.core.nodes import Node

logger = logging.getLogger(__name__)


class GraphTraversalMixin:
    """Mixin class providing methods for traversing and validating the graph.

    Includes operations like topological sorting, dependency retrieval,
    cycle detection, and general graph validation. Relies on the main class
    (e.g., `Graph`) to provide the `nodes` dictionary and node access methods
    like `get_node` and `has_node`.
    """

    # Type hints for self attributes/methods expected from the main Graph class
    _nodes: dict[str, "Node"]

    def get_node(self, name: str) -> Optional["Node"]:
        """Retrieve a node from the graph by its name.

        Args:
            name: The name of the node to retrieve.

        Returns:
            The `Node` instance if found; otherwise, `None`.
        """

    def has_node(self, node_id: str) -> bool:
        """Check whether a node exists in the graph.

        Args:
            node_id: The name of the node to check.

        Returns:
            `True` if the node exists in the registry; otherwise, `False`.
        """

    def get_direct_successors(self, node_id: str) -> list[str]:
        """Get immediate successor node IDs for a given node.

        Args:
            node_id: The name of the node whose successors are requested.

        Returns:
            A list of names of nodes that directly depend on the given node.
        """

    def get_direct_predecessors(self, node_id: str) -> list[str]:
        """Get immediate predecessor node IDs (dependencies) for a given node.

        Args:
            node_id: The name of the node whose predecessors are requested.

        Returns:
            A list of names of nodes that the given node depends on directly.
        """

    def nodes(self) -> dict[str, "Node"]:
        """Access the full node registry dictionary.

        Returns:
            A mapping of node names to their corresponding `Node` instances.
        """

    def topological_sort(self) -> list[str]:
        """Performs a topological sort of the nodes based on dependencies.

        Uses Kahn's algorithm to determine a linear ordering of nodes such that for
        every directed edge from node `u` to node `v`, `u` comes before `v` in the
        ordering. This is essential for determining the correct calculation order.

        Returns:
            A list of node names (strings) in a valid topological order.

        Raises:
            ValueError: If a cycle is detected in the graph, as topological sort
                        is only possible on Directed Acyclic Graphs (DAGs).
        """
        in_degree: dict[str, int] = {n: 0 for n in self.nodes}
        adjacency: dict[str, list[str]] = {n: [] for n in self.nodes}
        for name, node in self.nodes.items():
            if hasattr(node, "inputs"):
                for inp in node.inputs:
                    adjacency[inp.name].append(name)
                    in_degree[name] += 1
        queue: list[str] = [n for n, d in in_degree.items() if d == 0]
        topo_order: list[str] = []
        while queue:
            current = queue.pop()
            topo_order.append(current)
            for nbr in adjacency[current]:
                in_degree[nbr] -= 1
                if in_degree[nbr] == 0:
                    queue.append(nbr)
        if len(topo_order) != len(self.nodes):
            raise ValueError("Cycle detected in graph, can't do a valid topological sort.")
        return topo_order

    def get_calculation_nodes(self) -> list[str]:
        """Identifies all nodes in the graph that represent calculations.

        Filters the graph's nodes based on the `has_calculation()` method
        of each node.

        Returns:
            A list of strings, where each string is the name (ID) of a node
            that performs a calculation.
        """
        return [node_id for node_id, node in self.nodes.items() if node.has_calculation()]

    def get_dependencies(self, node_id: str) -> list[str]:
        """Retrieves the direct dependencies (inputs) of a specific node.

        Args:
            node_id: The unique string identifier (name) of the node whose
                     dependencies are requested.

        Returns:
            A list of strings, where each string is the name (ID) of a node
            that the specified `node_id` directly depends on. Returns an empty
            list if the node has no dependencies or doesn't support inputs.

        Raises:
            NodeError: If no node with the specified `node_id` exists in the graph.
        """
        node = self.get_node(node_id)
        if not node:
            raise NodeError(message=f"Node '{node_id}' does not exist", node_id=node_id)
        if hasattr(node, "inputs"):
            return [inp.name for inp in node.inputs]
        return []

    def get_dependency_graph(self) -> dict[str, list[str]]:
        """Constructs a representation of the full dependency graph.

        Iterates through all nodes and maps each node's ID to a list of its
        direct dependencies (input node IDs).

        Returns:
            A dictionary where keys are node IDs (str) and values are lists
            of node IDs (str) representing the direct dependencies of the key node.
        """
        dependencies: dict[str, list[str]] = {}
        for node_id, node in self.nodes.items():
            try:
                if hasattr(node, "inputs"):
                    dependencies[node_id] = [inp.name for inp in node.inputs]
                else:
                    dependencies[node_id] = []
            except NodeError:
                dependencies[node_id] = []
        return dependencies

    def detect_cycles(self) -> list[list[str]]:
        """Detects all cycles present in the graph's dependency structure.

        Uses a depth-first search (DFS) based algorithm to traverse the graph
        and identify back-edges, which indicate cycles.

        Returns:
            A list of lists, where each inner list contains the sequence of
            node names (IDs) forming a detected cycle. If no cycles are found,
            returns an empty list.
        """
        dependency_graph = self.get_dependency_graph()
        visited: set[str] = set()
        rec_stack: set[str] = set()
        cycles: list[list[str]] = []

        def dfs_detect_cycles(node_id: str, path: Optional[list[str]] = None) -> None:
            """Helper function for cycle detection using DFS.

            Keeps track of visited nodes and the recursion stack to identify
            back edges.

            Args:
                node_id: The ID of the current node being visited.
                path: The list of nodes visited in the current DFS path.
            """
            if path is None:
                path = []
            if node_id in rec_stack:
                cycle_start = path.index(node_id)
                cycle = path[cycle_start:] + [node_id]
                if cycle not in cycles:
                    cycles.append(cycle)
                return
            if node_id in visited:
                return
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)
            for dep_id in dependency_graph.get(node_id, []):
                dfs_detect_cycles(dep_id, path[:])
            rec_stack.remove(node_id)

        for node_id in self.nodes:
            if node_id not in visited:
                dfs_detect_cycles(node_id)
        return cycles

    def validate(self) -> list[str]:
        """Performs validation checks on the graph structure.

        Checks for two main types of issues:
        1. Circular dependencies (cycles) using `detect_cycles`.
        2. Missing dependencies (nodes that depend on non-existent nodes).

        Returns:
            A list of strings, where each string describes a validation error
            found. If the graph is valid, returns an empty list.
        """
        errors: list[str] = [
            f"Circular dependency detected: {' -> '.join(cycle)}" for cycle in self.detect_cycles()
        ]

        errors.extend(
            f"Node '{node_id}' depends on non-existent node '{inp.name}'"
            for node_id, node in self.nodes.items()
            if hasattr(node, "inputs")
            for inp in node.inputs
            if not self.has_node(inp.name)
        )

        return errors

    def breadth_first_search(self, start_node: str, direction: str = "successors") -> list[str]:
        """Performs a breadth-first search (BFS) traversal of the graph.

        Args:
            start_node: The ID of the node to start the traversal from.
            direction: The direction of traversal. Can be "successors" or "predecessors".

        Returns:
            A list of node IDs (strings) visited during the traversal.
        """
        if direction not in ["successors", "predecessors"]:
            raise ValueError("Invalid direction. Use 'successors' or 'predecessors'.")

        visited = set()
        queue = deque([start_node])
        visited.add(start_node)
        traversal_order = []

        while queue:
            level_size = len(queue)
            current_level = []
            new_level_nodes = set()

            for _ in range(level_size):
                node_id = queue.popleft()
                current_level.append(node_id)

                # Find neighbors based on direction
                neighbors = (
                    self.get_direct_successors(node_id)
                    if direction == "successors"
                    else self.get_direct_predecessors(node_id)
                )
                # Use extend and list comprehension for PERF401
                new_level_nodes.update(n for n in neighbors if n not in visited)

            # Add new unique neighbors to the queue and visited set
            for neighbor in new_level_nodes:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

            if current_level:
                traversal_order.extend(current_level)

        return traversal_order
