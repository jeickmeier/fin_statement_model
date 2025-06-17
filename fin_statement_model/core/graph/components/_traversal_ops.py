"""Read-only traversal, validation, and dependency-inspection helpers.

TraversalMixin exposes methods from the GraphTraverser for inspecting the structure of the graph
without mutating it. This includes dependency analysis, topological sorting, cycle detection, and
validation.

Key responsibilities:
    - Inspect dependencies, successors, and predecessors
    - Perform topological sorts and detect cycles
    - Validate graph structure
    - Perform breadth-first searches

Examples:
    >>> from fin_statement_model.core.graph import Graph
    >>> g = Graph(periods=["2023"])
    >>> _ = g.add_financial_statement_item("Revenue", {"2023": 100.0})
    >>> _ = g.add_financial_statement_item("COGS", {"2023": 60.0})
    >>> _ = g.add_calculation(
    ...     name="GrossProfit",
    ...     input_names=["Revenue", "COGS"],
    ...     operation_type="formula",
    ...     formula="input_0 - input_1",
    ...     formula_variable_names=["input_0", "input_1"]
    ... )
    >>> g.get_dependencies("GrossProfit")
    ['Revenue', 'COGS']
    >>> g.topological_sort()
    ['Revenue', 'COGS', 'GrossProfit']
"""

from __future__ import annotations

from typing import Any

from fin_statement_model.core.nodes import Node  # for type annotations only

__all__: list[str] = ["TraversalMixin"]


class TraversalMixin:
    """Expose :class:`fin_statement_model.core.graph.traverser.GraphTraverser` methods."""

    # ------------------------------------------------------------------
    # Cycle detection & reachability
    # ------------------------------------------------------------------
    def has_cycle(self, source_node: Node, target_node: Node) -> Any:
        if source_node.name not in self._nodes or target_node.name not in self._nodes:  # type: ignore[attr-defined]
            return False
        return self.traverser._is_reachable(source_node.name, target_node.name)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Simple wrappers – keep return type *Any* to avoid strict coupling to
    # Traverser signatures, which currently return ``Any`` for some methods.
    # ------------------------------------------------------------------
    def topological_sort(self) -> Any:
        return self.traverser.topological_sort()  # type: ignore[attr-defined]

    def get_calculation_nodes(self) -> Any:
        return self.traverser.get_calculation_nodes()  # type: ignore[attr-defined]

    def get_dependencies(self, node_id: str) -> Any:
        return self.traverser.get_dependencies(node_id)  # type: ignore[attr-defined]

    def get_dependency_graph(self) -> Any:
        return self.traverser.get_dependency_graph()  # type: ignore[attr-defined]

    def detect_cycles(self) -> Any:
        return self.traverser.detect_cycles()  # type: ignore[attr-defined]

    def validate(self) -> Any:
        return self.traverser.validate()  # type: ignore[attr-defined]

    def breadth_first_search(
        self, start_node: str, direction: str = "successors"
    ) -> Any:
        return self.traverser.breadth_first_search(start_node, direction)  # type: ignore[attr-defined]

    def get_direct_successors(self, node_id: str) -> Any:
        return self.traverser.get_direct_successors(node_id)  # type: ignore[attr-defined]

    def get_direct_predecessors(self, node_id: str) -> Any:
        return self.traverser.get_direct_predecessors(node_id)  # type: ignore[attr-defined]
