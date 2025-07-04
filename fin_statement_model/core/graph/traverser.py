"""Read-only traversal helpers for :class:`~fin_statement_model.core.graph.graph.Graph`.

The GraphTraverser class provides a *read-only* view on a graph's structure. It offers utility
methods for:
    - Dependency inspection (predecessors/successors)
    - Topological sorting
    - Cycle detection and validation
    - Breadth-first searches for visualization or debugging
    - General graph structure validation

Unlike the manipulator, the traverser **never mutates** the graph; this makes it safe to call from
anywhere, including within calculation routines.

Examples:
    >>> from fin_statement_model.core.graph import Graph
    >>> g = Graph(periods=["2023", "2024"])
    >>> _ = g.add_financial_statement_item("Revenue", {"2023": 100, "2024": 110})
    >>> _ = g.add_financial_statement_item("COGS", {"2023": 60, "2024": 70})
    >>> _ = g.add_calculation(
    ...     name="GrossProfit",
    ...     input_names=["Revenue", "COGS"],
    ...     operation_type="formula",
    ...     formula="input_0 - input_1",
    ...     formula_variable_names=["input_0", "input_1"],
    ... )
    >>> g.traverser.get_dependencies("GrossProfit")
    ['Revenue', 'COGS']
    >>> g.traverser.topological_sort()
    ['Revenue', 'COGS', 'GrossProfit']
    >>> g.traverser.detect_cycles()
    []
    >>> g.traverser.validate()
    []

As with the manipulator, end-users reach the traverser via `graph.traverser` rather than
instantiating it directly.
"""

from collections import deque
import logging
from typing import Any, cast

from fin_statement_model.core.errors import NodeError
from fin_statement_model.core.nodes import Node, is_calculation_node

logger = logging.getLogger(__name__)


class GraphTraverser:
    """Encapsulate traversal and validation helpers for Graph.

    The GraphTraverser provides read-only methods for inspecting the structure of a Graph instance,
    including dependency analysis, cycle detection, topological sorting, and validation.

    Attributes:
        graph: The Graph instance this traverser operates on.

    Examples:
        >>> from fin_statement_model.core.graph import Graph
        >>> g = Graph(periods=["2023", "2024"])
        >>> _ = g.add_financial_statement_item("Revenue", {"2023": 100, "2024": 110})
        >>> _ = g.add_financial_statement_item("COGS", {"2023": 60, "2024": 70})
        >>> _ = g.add_calculation(
        ...     name="GrossProfit",
        ...     input_names=["Revenue", "COGS"],
        ...     operation_type="formula",
        ...     formula="input_0 - input_1",
        ...     formula_variable_names=["input_0", "input_1"],
        ... )
        >>> g.traverser.get_dependencies("GrossProfit")
        ['Revenue', 'COGS']
        >>> g.traverser.topological_sort()
        ['Revenue', 'COGS', 'GrossProfit']
        >>> g.traverser.detect_cycles()
        []
        >>> g.traverser.validate()
        []
    """

    def __init__(self, graph: Any) -> None:
        """Initialize the GraphTraverser with a Graph reference.

        Args:
            graph: The Graph instance to traverse.
        """
        self.graph = graph

    def get_node(self, name: str) -> Node | None:
        """Retrieve a node from the graph by its name.

        Args:
            name: The unique name of the node to retrieve.

        Returns:
            The Node instance if found, else None.

        Examples:
            >>> traverser.get_node("Revenue")
        """
        return cast("Node | None", self.graph.manipulator.get_node(name))

    def has_node(self, node_id: str) -> bool:
        """Check if a node exists in the graph.

        Args:
            node_id: The name of the node to check.

        Returns:
            True if the node exists, False otherwise.

        Examples:
            >>> traverser.has_node("Revenue")
        """
        return cast("bool", self.graph.manipulator.has_node(node_id))

    @property
    def nodes(self) -> dict[str, Node]:
        """Access the full node registry dictionary.

        Returns:
            A dict mapping node names to Node instances.

        Examples:
            >>> list(traverser.nodes.keys())
        """
        return cast("dict[str, Node]", self.graph.nodes)

    def get_direct_successors(self, node_id: str) -> list[str]:
        """Get immediate successor node IDs for a given node.

        Args:
            node_id: The name of the node whose successors to retrieve.

        Returns:
            A list of node IDs that directly follow the given node.

        Examples:
            >>> traverser.get_direct_successors("Revenue")
        """
        successors: list[str] = []
        for other_id, node in self.nodes.items():
            if hasattr(node, "inputs"):
                input_nodes: list[Node] = []
                if isinstance(node.inputs, list):
                    input_nodes = node.inputs
                elif isinstance(node.inputs, dict):
                    input_nodes = list(node.inputs.values())

                if any(inp.name == node_id for inp in input_nodes if hasattr(inp, "name")):
                    successors.append(other_id)
        return successors

    def get_direct_predecessors(self, node_id: str) -> list[str]:
        """Get immediate predecessor node IDs (dependencies) for a given node.

        Args:
            node_id: The name of the node whose dependencies to retrieve.

        Returns:
            A list of node IDs that the given node depends on.

        Raises:
            NodeError: If the node does not exist.

        Examples:
            >>> traverser.get_direct_predecessors("GrossProfit")
        """
        node = self.get_node(node_id)
        if not node:
            raise NodeError(message=f"Node '{node_id}' does not exist", node_id=node_id)
        if hasattr(node, "inputs"):
            return [inp.name for inp in node.inputs]
        return []

    def topological_sort(self) -> list[str]:
        """Perform a topological sort of nodes based on dependencies.

        Returns:
            A list of node IDs in topological order.

        Raises:
            ValueError: If a cycle is detected in the graph.

        Examples:
            >>> traverser.topological_sort()
        """
        in_degree: dict[str, int] = dict.fromkeys(self.nodes, 0)
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
        """Identify all nodes in the graph that represent calculations.

        Returns:
            A list of node IDs for nodes with calculations.

        Examples:
            >>> traverser.get_calculation_nodes()
        """
        return [node_id for node_id, node in self.nodes.items() if is_calculation_node(node)]

    def get_dependencies(self, node_id: str) -> list[str]:
        """Retrieve the direct dependencies (inputs) of a specific node.

        Args:
            node_id: The name of the node to inspect.

        Returns:
            A list of node IDs that the given node depends on.

        Raises:
            NodeError: If the node does not exist.

        Examples:
            >>> traverser.get_dependencies("GrossProfit")
        """
        node = self.get_node(node_id)
        if not node:
            raise NodeError(message=f"Node '{node_id}' does not exist", node_id=node_id)
        if hasattr(node, "inputs"):
            return [inp.name for inp in node.inputs]
        return []

    def get_dependency_graph(self) -> dict[str, list[str]]:
        """Construct a representation of the full dependency graph.

        Returns:
            A dict mapping each node ID to its list of dependency node IDs.

        Examples:
            >>> traverser.get_dependency_graph()
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
        """Detect all cycles present in the graph's dependency structure.

        Returns:
            A list of cycles, each cycle is a list of node IDs forming the cycle.

        Examples:
            >>> traverser.detect_cycles()
        """
        dependency_graph = self.get_dependency_graph()
        visited: set[str] = set()
        rec_stack: set[str] = set()
        cycles: list[list[str]] = []

        def dfs_detect_cycles(n_id: str, path: list[str] | None = None) -> None:
            if path is None:
                path = []
            if n_id in rec_stack:
                cycle_start = path.index(n_id)
                cycle = [*path[cycle_start:], n_id]
                if cycle not in cycles:
                    cycles.append(cycle)
                return
            if n_id in visited:
                return
            visited.add(n_id)
            rec_stack.add(n_id)
            path.append(n_id)
            for dep in dependency_graph.get(n_id, []):
                dfs_detect_cycles(dep, path[:])
            rec_stack.remove(n_id)

        for node_id in self.nodes:
            if node_id not in visited:
                dfs_detect_cycles(node_id)
        return cycles

    def validate(self) -> list[str]:
        """Perform validation checks on the graph structure.

        Returns:
            A list of validation error messages; empty list if graph is valid.

        Examples:
            >>> traverser.validate()
        """
        errors: list[str] = [f"Circular dependency detected: {' -> '.join(cycle)}" for cycle in self.detect_cycles()]
        errors.extend(
            f"Node '{node_id}' depends on non-existent node '{inp.name}'"
            for node_id, node in self.nodes.items()
            if hasattr(node, "inputs")
            for inp in node.inputs
            if not self.has_node(inp.name)
        )
        return errors

    def breadth_first_search(self, start_node: str, direction: str = "successors") -> list[list[str]]:
        """Perform a breadth-first search (BFS) traversal of the graph.

        Args:
            start_node: The starting node ID for the traversal.
            direction: The traversal direction, either 'successors' or 'predecessors'.

        Returns:
            A list of levels, each level is a list of node IDs visited at that depth.

        Raises:
            ValueError: If `direction` is not 'successors' or 'predecessors'.

        Examples:
            >>> traverser.breadth_first_search("Revenue", "successors")
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

            for _ in range(level_size):
                n_id = queue.popleft()
                current_level.append(n_id)

                if direction == "successors":
                    for successor in self.get_direct_successors(n_id):
                        if successor not in visited:
                            visited.add(successor)
                            queue.append(successor)
                elif direction == "predecessors":
                    for predecessor in self.get_direct_predecessors(n_id):
                        if predecessor not in visited:
                            visited.add(predecessor)
                            queue.append(predecessor)

            traversal_order.append(current_level)

        return traversal_order

    def would_create_cycle(self, new_node: "Node") -> bool:
        """Check if adding a node would create a cycle.

        Args:
            new_node: The node to be added (must have 'inputs' attribute)

        Returns:
            True if adding the node would create a cycle
        """
        if not hasattr(new_node, "inputs") or not new_node.inputs:
            return False

        # For each input, check if new_node is reachable from it
        for input_node in new_node.inputs:
            if hasattr(input_node, "name") and self._is_reachable(input_node.name, new_node.name):
                return True
        return False

    def _is_reachable(self, from_node: str, to_node: str) -> bool:
        """Check if to_node is reachable from from_node.

        Args:
            from_node: Starting node name
            to_node: Target node name

        Returns:
            True if to_node is reachable from from_node via successors
        """
        # If from_node doesn't exist, no reachability
        if from_node not in self.graph._nodes:
            return False

        # If to_node doesn't exist yet, check temporary reachability
        if to_node not in self.graph._nodes:
            return False

        try:
            bfs_levels = self.breadth_first_search(start_node=from_node, direction="successors")
            reachable_nodes = {n for level in bfs_levels for n in level}
        except (ValueError, KeyError):
            # Handle cases where BFS fails (e.g., invalid node)
            return False
        else:
            return to_node in reachable_nodes

    def find_cycle_path(self, from_node: str, to_node: str) -> list[str] | None:
        """Find the actual cycle path if one exists.

        Args:
            from_node: Starting node name
            to_node: Target node name that would complete the cycle

        Returns:
            List of node names forming the cycle path, or None if no cycle
        """
        if not self._is_reachable(from_node, to_node):
            return None

        # Use DFS to find the actual path
        visited = set()
        path: list[str] = []

        def dfs_find_path(current: str, target: str) -> bool:
            if current == target and len(path) > 0:
                return True
            if current in visited:
                return False

            visited.add(current)
            path.append(current)

            # Get successors of current node
            for successor in self.get_direct_successors(current):
                if dfs_find_path(successor, target):
                    return True

            path.pop()
            return False

        if dfs_find_path(from_node, to_node):
            return [*path, to_node]  # Complete the cycle
        return None
