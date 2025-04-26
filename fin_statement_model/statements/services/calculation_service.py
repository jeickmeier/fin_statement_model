"""Calculation service for financial statements.

Encapsulates creation of calculation nodes and detection of circular dependencies.
"""

import logging
from typing import Union, Any

from fin_statement_model.core.errors import (
    NodeError,
    CalculationError,
    CircularDependencyError,
)
from fin_statement_model.statements.structure import (
    StatementStructure,
    CalculatedLineItem,
    SubtotalLineItem,
)
from fin_statement_model.core.graph import Graph

__all__ = ["CalculationService"]

logger = logging.getLogger(__name__)


class CalculationService:
    """Service to create calculation nodes in the graph for a given statement."""

    def __init__(self, engine: Graph):
        """Initialize the CalculationService with a Graph instance for calculations.

        Args:
            engine: The Graph instance used for adding and evaluating calculation nodes.
        """
        self.engine = engine
        self._input_values: dict[str, Any] = {}  # Track input values for dependency resolution

    def set_input_values(self, values: dict[str, Any]) -> None:
        """Set input values for calculations.

        Args:
            values: Dictionary mapping node IDs to their values.
        """
        self._input_values = values
        # Update engine's shared registry with input values
        for node_id in values:
            if node_id not in self.engine._nodes:
                logger.warning(
                    f"Input value provided for {node_id}, but node does not exist in engine registry. "
                    "Cannot directly add value without creating a node."
                )
            else:
                # Node exists, potentially update its value if needed
                pass

    def create_calculations(self, statement: StatementStructure) -> list[str]:
        """Create calculation nodes for all calculated items in the statement.

        Args:
            statement (StatementStructure): The statement structure containing calculations.

        Returns:
            List[str]: List of created calculation node IDs.

        Raises:
            CircularDependencyError: If a circular dependency is detected.
            NodeError: If dependencies cannot be satisfied.
        """
        items = statement.get_calculation_items()

        if not items:
            return []

        processed: set[str] = set(self._input_values.keys())  # Start with known input values
        created_nodes: list[str] = []

        # Add input values to the processed set if they exist in the engine's registry
        for node_id in self._input_values:
            if node_id in self.engine._nodes:
                processed.add(node_id)
            else:
                pass

        remaining = items.copy()
        while remaining:
            progress = False

            for item in remaining[:]:
                deps_satisfied = all(
                    (
                        dep_id in processed
                        or dep_id in self._input_values
                        or dep_id in self.engine._nodes
                    )  # Check engine registry
                    for dep_id in item.input_ids
                )

                if deps_satisfied:
                    try:
                        self._create_calculation_node(item)
                        created_nodes.append(item.id)
                        processed.add(item.id)  # Mark this item's ID as processed
                        remaining.remove(item)
                        progress = True
                    except Exception:
                        logger.exception(f"Failed to create calculation node for {item.id}")
                        raise

            if not progress and remaining:
                cycle = self._detect_cycle(remaining)
                if cycle:
                    logger.error(f"Circular dependency detected: {cycle}")
                    raise CircularDependencyError(
                        message=f"Circular dependency detected in calculations: {cycle}",
                        cycle=cycle,
                    )
                else:
                    missing_deps = set()
                    for item in remaining:
                        missing_deps.update(
                            dep_id
                            for dep_id in item.input_ids
                            if not (
                                dep_id in processed
                                or dep_id in self._input_values
                                or dep_id in self.engine._nodes
                            )  # Check engine registry
                        )
                    if missing_deps:
                        raise NodeError(
                            message=f"Missing dependencies for calculations: {missing_deps}",
                            node_id=remaining[0].id,  # Report first problematic item
                        )
                    else:
                        logger.error(
                            f"Calculation stalled for items: {[it.id for it in remaining]}. No progress made, no cycle detected, and no explicit missing dependencies found in registry."
                        )
                        raise CalculationError(
                            message="Calculation stalled without clear cause.",
                            node_id=remaining[0].id,
                        )

        return created_nodes

    def _detect_cycle(self, items: list[Union[CalculatedLineItem, SubtotalLineItem]]) -> list[str]:
        """Detects a cycle in the calculation dependency graph.

        Args:
            items: List of calculation items with unresolved dependencies.

        Returns:
            List[str]: List of item IDs forming a cycle, or empty if none found.
        """
        if not items:
            return []

        item_ids = {item.id for item in items}
        graph_map = {item.id: {i for i in item.input_ids if i in item_ids} for item in items}

        visited = set()
        rec_stack = set()

        def dfs(node: str, path: list[str]) -> list[str]:
            if node in rec_stack:
                try:
                    start = path.index(node)
                    return path[start:]  # Return the cycle path
                except ValueError:
                    logger.exception(
                        f"Internal error: Node {node} in rec_stack but not in path {path}"
                    )
                    return [node]  # Fallback
            if node in visited:
                return []  # Already visited this path, no cycle found here

            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for nbr in graph_map.get(node, set()):
                cycle = dfs(nbr, path)
                if cycle:
                    return cycle  # Propagate cycle found deeper

            rec_stack.remove(node)
            path.pop()
            return []

        for nid in graph_map:
            if nid not in visited:
                cycle = dfs(nid, [])
                if cycle:
                    return cycle
        return []  # No cycle found

    def _create_calculation_node(self, item: Union[CalculatedLineItem, SubtotalLineItem]) -> None:
        """Create a calculation node in the graph for a given calculation item.

        Args:
            item: The calculation item defining type, inputs, and parameters.

        Raises:
            NodeError: If an input node does not exist in the graph.
            CalculationError: If the calculation type is unsupported.
        """
        calc_type = item.calculation_type
        inputs = item.input_ids

        for input_id in inputs:
            if input_id not in self.engine._nodes and input_id not in self._input_values:
                raise NodeError(
                    message=f"Missing input node '{input_id}' in engine registry for '{item.id}'",
                    node_id=item.id,
                )

        try:
            if calc_type in ["addition", "subtraction", "multiplication", "division"]:
                self.engine.add_calculation(item.id, inputs, calc_type, **item.parameters)
            elif calc_type == "weighted_average":
                weights = item.parameters.get("weights")
                if not weights:
                    raise CalculationError(
                        message="Weights required for weighted_average calculation",
                        node_id=item.id,
                    )
                self.engine.add_calculation(item.id, inputs, "weighted_average", weights=weights)
            elif isinstance(item, SubtotalLineItem):
                self.engine.add_calculation(item.id, inputs, "addition", **item.parameters)
            else:
                raise CalculationError(
                    message=f"Unsupported calculation type: {calc_type}",
                    node_id=item.id,
                )
        except (NodeError, CalculationError, ValueError, TypeError) as e:
            logger.exception(f"CalculationEngine failed to add calculation for '{item.id}'")
            raise CalculationError(
                message=f"Engine failed to create calculation node for {item.id}",
                node_id=item.id,
                details={"original_error": str(e)},
            )
