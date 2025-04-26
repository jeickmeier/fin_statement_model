"""Provide graph operations for the financial statement model.

This module provides the `Graph` class that combines manipulation, traversal,
forecasting, and calculation capabilities for building and evaluating
financial statement models.
"""

import logging
from typing import Any, Callable, Optional

from fin_statement_model.core.node_factory import NodeFactory
from fin_statement_model.core.nodes import Node, FinancialStatementItemNode, MetricCalculationNode, CalculationNode
from fin_statement_model.core.errors import NodeError, ConfigurationError, CalculationError
from fin_statement_model.core.metrics import metric_registry
from fin_statement_model.core.calculations import Registry
from fin_statement_model.core.graph.manipulator import GraphManipulator
from fin_statement_model.core.graph.traverser import GraphTraverser


# Configure logging
logger = logging.getLogger(__name__)

__all__ = ["Graph"]

class Graph:
    """Represent the financial statement model as a directed graph.

    This class integrates graph manipulation, traversal, forecasting, and
    calculation capabilities. It serves as the central orchestrator for nodes,
    periods, caching, and calculation workflows.

    Attributes:
        _nodes: A dict mapping node names (str) to Node objects.
        _periods: A list of time period identifiers (str) managed by the graph.
        _cache: A nested dict caching calculated values per node per period.
        _metric_names: A set of node names (str) corresponding to metric nodes.
        _node_factory: An instance of NodeFactory for creating new nodes.
    """

    def __init__(self, periods: Optional[list[str]] = None):
        """Initialize the Graph instance.

        Set up core components: node registry, `DataManager`, and `CalculationEngine`.
        Optionally initialize the graph with a list of time periods.

        Args:
            periods: An optional list of strings representing the initial time
                     periods for the financial model (e.g., ["2023", "2024"]).
                     The `DataManager` will handle sorting and ensuring uniqueness.

        Raises:
            TypeError: If `periods` is provided but is not a list.

        Examples:
            >>> graph_no_periods = Graph()
            >>> print(graph_no_periods.periods)
            []
            >>> graph_with_periods = Graph(periods=["2023", "2022"])
            >>> print(graph_with_periods.periods) # Periods are sorted
            ['2022', '2023']
            >>> try:
            ...     Graph(periods="2023") # Invalid type
            ... except TypeError as e:
            ...     print(e)
            Initial periods must be a list
        """
        # No super().__init__() needed as mixins don't have __init__
        # and GraphCore is removed.

        self._nodes: dict[str, Node] = {}

        # Initialize core attributes for periods, cache, metrics, and node factory
        self._periods: list[str] = []
        self._cache: dict[str, dict[str, float]] = {}
        self._metric_names: set[str] = set()
        self._node_factory: NodeFactory = NodeFactory()

        # Handle initial periods directly
        if periods:
            if not isinstance(periods, list):
                raise TypeError("Initial periods must be a list")
            self.add_periods(periods)

        self.manipulator = GraphManipulator(self)
        self.traverser = GraphTraverser(self)

    @property
    def nodes(self) -> dict[str, Node]:
        """Provide access to the dictionary of all nodes in the graph.

        Returns:
            A dictionary where keys are node names (str) and values are
            `Node` objects. This dictionary represents the shared node registry.

        Examples:
            >>> graph = Graph()
            >>> item_node = graph.add_financial_statement_item("Revenue", {"2023": 100})
            >>> print(list(graph.nodes.keys()))
            ['Revenue']
            >>> print(graph.nodes["Revenue"] == item_node)
            True
        """
        return self._nodes

    @property
    def periods(self) -> list[str]:
        """Retrieve the list of time periods currently managed by the graph.

        Returns:
            A sorted list of unique time period strings managed by the graph.

        Examples:
            >>> graph = Graph(periods=["2024", "2023"])
            >>> print(graph.periods)
            ['2023', '2024']
            >>> graph.add_periods(["2025"])
            >>> print(graph.periods)
            ['2023', '2024', '2025']
        """
        return self._periods

    def add_periods(self, periods: list[str]) -> None:
        """Add new time periods to the graph.

        Update the internal period list, ensuring uniqueness and sorting.

        Args:
            periods: A list of strings representing the time periods to add.

        Raises:
            TypeError: If `periods` is not a list.
        """
        if not isinstance(periods, list):
            raise TypeError("Periods must be provided as a list.")
        # Ensure unique and sorted periods
        combined = set(self._periods).union(periods)
        self._periods = sorted(combined)
        logger.debug(f"Added periods {periods}; current periods: {self._periods}")

    def add_calculation(
        self,
        name: str,
        input_names: list[str],
        operation_type: str,
        **kwargs: dict[str, Any],
    ) -> Node:
        """Add a new calculation node to the graph using the node factory.

        Resolve input node names to Node objects, create a CalculationNode,
        register it in the graph, and return it.

        Args:
            name: Unique name for the calculation node.
            input_names: List of node names to use as inputs.
            operation_type: Calculation type key (e.g., 'addition').
            **kwargs: Additional parameters for the calculation.

        Returns:
            The created calculation node.

        Raises:
            NodeError: If any input node name does not exist.
            ValueError: If the name is invalid or creation fails.
            TypeError: If inputs are invalid.
        """
        # Validate name
        if not name or not isinstance(name, str):
            raise ValueError("Calculation node name must be a non-empty string.")
        # Resolve input node names
        if not isinstance(input_names, list):
            raise TypeError("input_names must be a list of node names.")
        resolved_inputs: list[Node] = []
        missing = []
        for nm in input_names:
            nd = self._nodes.get(nm)
            if nd is None:
                missing.append(nm)
            else:
                resolved_inputs.append(nd)
        if missing:
            raise NodeError(
                f"Cannot create calculation node '{name}': missing input nodes {missing}",
                node_id=name,
            )
        # Create the node via factory
        try:
            node = self._node_factory.create_calculation_node(
                name=name,
                inputs=resolved_inputs,
                calculation_type=operation_type,
                **kwargs,
            )
        except (ValueError, TypeError):
            logger.exception(
                f"Failed to create calculation node '{name}' with type '{operation_type}'"
            )
            raise
        # Register node in graph
        if name in self._nodes:
            logger.warning(f"Overwriting existing node '{name}' in graph.")
        self._nodes[name] = node
        logger.info(
            f"Added calculation node '{name}' of type '{operation_type}' with inputs {input_names}"
        )
        return node

    def add_metric(
        self, metric_name: str, node_name: Optional[str] = None
    ) -> MetricCalculationNode:
        """Add a metric calculation node based on a metric definition.

        If `node_name` is None, uses `metric_name` as the node name.

        Use the metric registry to load inputs and formula, create a MetricCalculationNode,
        register it, and track it as a metric.

        Args:
            metric_name: Key of the metric definition to add.
            node_name: Optional name for the metric node; defaults to metric_name.

        Returns:
            The created MetricCalculationNode.

        Raises:
            TypeError: If node_name is invalid.
            ValueError: If node_name already exists.
            ConfigurationError: If metric definition is missing or invalid.
            NodeError: If required input nodes are missing.
        """
        # Default node_name to metric_name if not provided
        if node_name is None:
            node_name = metric_name
        if not node_name or not isinstance(node_name, str):
            raise TypeError("Metric node name must be a non-empty string.")
        # Check for name conflict
        if node_name in self._nodes:
            raise ValueError(f"A node with name '{node_name}' already exists in the graph.")
        # Load metric definition
        try:
            metric_def = metric_registry.get(metric_name)
        except KeyError as e:
            raise ConfigurationError(f"Unknown metric definition: '{metric_name}'") from e
        # Validate definition fields
        required_inputs = metric_def.get("inputs")
        if not isinstance(required_inputs, list):
            raise ConfigurationError(
                f"Metric definition for '{metric_name}' is invalid: 'inputs' must be a list."
            )
        if "formula" not in metric_def:
            raise ConfigurationError(
                f"Metric definition for '{metric_name}' is invalid: missing 'formula'."
            )
        # Resolve input nodes
        resolved_inputs: dict[str, Node] = {}
        missing = []
        for req in required_inputs:
            nd = self._nodes.get(req)
            if nd is None:
                missing.append(req)
            else:
                resolved_inputs[req] = nd
        if missing:
            raise NodeError(
                f"Cannot create metric '{metric_name}': missing required nodes {missing}",
                node_id=node_name,
            )
        # Create metric node via factory
        try:
            metric_node = self._node_factory.create_metric_node(
                name=node_name,
                metric_name=metric_name,
                input_nodes=resolved_inputs,
            )
        except (ValueError, TypeError, ConfigurationError):
            logger.exception(
                f"Failed to create metric node '{node_name}' for metric '{metric_name}'"
            )
            raise
        # Register metric node
        self._nodes[node_name] = metric_node
        self._metric_names.add(node_name)
        logger.info(
            f"Added metric '{metric_name}' as node '{node_name}' with inputs {list(resolved_inputs)}"
        )
        return metric_node

    def add_custom_calculation(
        self,
        name: str,
        calculation_func: Callable[..., float],
        inputs: Optional[list[str]] = None,
        description: str = "",
    ) -> Node:
        """Add a custom calculation node using a Python callable.

        Args:
            name: Unique name for the custom calculation node.
            calculation_func: A callable that accepts (period, **inputs) and returns float.
            inputs: Optional list of node names to use as inputs.
            description: Optional description of the calculation.

        Returns:
            The created custom calculation node.

        Raises:
            NodeError: If any specified input nodes are missing.
            TypeError: If calculation_func is not callable.
        """
        # Validate inputs list
        resolved_inputs: list[Node] = []
        if inputs is not None:
            if not isinstance(inputs, list):
                raise TypeError("inputs must be a list of node names.")
            missing = []
            for nm in inputs:
                nd = self._nodes.get(nm)
                if nd is None:
                    missing.append(nm)
                else:
                    resolved_inputs.append(nd)
            if missing:
                raise NodeError(
                    f"Cannot create custom calculation '{name}': missing input nodes {missing}",
                    node_id=name,
                )
        # Validate callable
        if not callable(calculation_func):
            raise TypeError("calculation_func must be callable.")
        # Create custom node via factory
        try:
            custom_node = self._node_factory._create_custom_node_from_callable(
                name=name,
                inputs=resolved_inputs,
                formula=calculation_func,
                description=description,
            )
        except (ValueError, TypeError):
            logger.exception(f"Failed to create custom calculation node '{name}'")
            raise
        # Register custom node
        if name in self._nodes:
            logger.warning(f"Overwriting existing node '{name}' in graph.")
        self._nodes[name] = custom_node
        logger.info(f"Added custom calculation node '{name}' with inputs {inputs}")
        return custom_node

    def change_calculation_method(
        self,
        node_name: str,
        new_method_key: str,
        **kwargs: dict[str, Any],
    ) -> None:
        """Change the calculation method for an existing calculation-based node.

        Args:
            node_name: Name of the existing calculation node.
            new_method_key: Key of the new calculation method to apply.
            **kwargs: Additional parameters required by the new calculation.

        Returns:
            None

        Raises:
            NodeError: If the target node does not exist or is not a CalculationNode.
            ValueError: If `new_method_key` is not a recognized calculation key.
            TypeError: If the new calculation cannot be instantiated with the provided arguments.

        Examples:
            >>> graph.change_calculation_method("GrossProfit", "addition")
        """
        node = self.manipulator.get_node(node_name)
        if node is None:
            raise NodeError("Node not found for calculation change", node_id=node_name)
        if not isinstance(node, CalculationNode):
            raise NodeError(
                f"Node '{node_name}' is not a CalculationNode", node_id=node_name
            )
        # Map method key to registry name
        if new_method_key not in self._node_factory._calculation_methods:
            raise ValueError(
                f"Calculation '{new_method_key}' is not recognized."
            )
        calculation_class_name = self._node_factory._calculation_methods[new_method_key]
        try:
            calculation_cls = Registry.get(calculation_class_name)
        except KeyError as e:
            raise ValueError(
                f"Calculation class '{calculation_class_name}' not found in registry."
            ) from e
        try:
            calculation_instance = calculation_cls(**kwargs)
        except TypeError as e:
            raise TypeError(
                f"Failed to instantiate calculation '{new_method_key}': {e}"
            )
        # Apply new calculation
        node.set_calculation(calculation_instance)
        # Clear cached calculations for this node
        if node_name in self._cache:
            del self._cache[node_name]
        logger.info(
            f"Changed calculation for node '{node_name}' to '{new_method_key}'"
        )

    def get_metric(self, metric_id: str) -> Optional[Node]:
        """Return the metric node for a given metric ID, if present.

        Args:
            metric_id: Identifier of the metric node to retrieve.

        Returns:
            The MetricCalculationNode corresponding to `metric_id`, or None if not found.

        Examples:
            >>> m = graph.get_metric("current_ratio")
            >>> if m:
            ...     print(m.name)
        """
        node = self._nodes.get(metric_id)
        return node if node and metric_id in self._metric_names else None

    def get_available_metrics(self) -> list[str]:
        """Return a sorted list of all metric node IDs currently in the graph.

        Returns:
            A sorted list of metric node names.

        Examples:
            >>> graph.get_available_metrics()
            ['current_ratio', 'debt_equity_ratio']
        """
        return sorted(self._metric_names)

    def get_metric_info(self, metric_id: str) -> dict:
        """Return detailed information for a specific metric node.

        Args:
            metric_id: Identifier of the metric node to inspect.

        Returns:
            A dict containing 'id', 'name', 'description', and 'inputs' for the metric.

        Raises:
            ValueError: If `metric_id` does not correspond to a metric node.

        Examples:
            >>> info = graph.get_metric_info("current_ratio")
            >>> print(info['inputs'])
        """
        metric_node = self.get_metric(metric_id)
        if metric_node is None:
            if metric_id in self._nodes:
                raise ValueError(f"Node '{metric_id}' exists but is not a metric.")
            raise ValueError(f"Metric '{metric_id}' not found in graph.")
        # Extract info from the MetricCalculationNode
        try:
            description = metric_node.definition.get("description")  # type: ignore
            name = metric_node.definition.get("name")  # type: ignore
            inputs = metric_node.get_dependencies()
        except Exception as e:
            raise ValueError(
                f"Failed to retrieve metric info for '{metric_id}': {e}"
            )
        return {"id": metric_id, "name": name, "description": description, "inputs": inputs}

    def calculate(self, node_name: str, period: str) -> float:
        """Calculate and return the value of a specific node for a given period.

        This method uses internal caching to speed repeated calls, and wraps
        underlying errors in CalculationError for clarity.

        Args:
            node_name: Name of the node to calculate.
            period: Time period identifier for the calculation.

        Returns:
            The calculated float value for the node and period.

        Raises:
            NodeError: If the specified node does not exist.
            TypeError: If the node has no callable `calculate` method.
            CalculationError: If an error occurs during the node's calculation.

        Examples:
            >>> value = graph.calculate("Revenue", "2023")
        """
        # Return cached value if present
        if node_name in self._cache and period in self._cache[node_name]:
            logger.debug(f"Cache hit for node '{node_name}', period '{period}'")
            return self._cache[node_name][period]
        # Resolve node
        node = self.manipulator.get_node(node_name)
        if node is None:
            raise NodeError(f"Node '{node_name}' not found", node_id=node_name)
        # Validate calculate method
        if not hasattr(node, "calculate") or not callable(node.calculate):
            raise TypeError(f"Node '{node_name}' has no callable calculate method.")
        # Perform calculation with error handling
        try:
            value = node.calculate(period)
        except (NodeError, ConfigurationError, CalculationError, ValueError, KeyError, ZeroDivisionError) as e:
            logger.error(f"Error calculating node '{node_name}' for period '{period}': {e}", exc_info=True)
            raise CalculationError(
                message=f"Failed to calculate node '{node_name}'",
                node_id=node_name,
                period=period,
                details={"original_error": str(e)},
            ) from e
        # Cache and return
        self._cache.setdefault(node_name, {})[period] = value
        logger.debug(f"Cached value for node '{node_name}', period '{period}': {value}")
        return value

    def recalculate_all(self, periods: Optional[list[str]] = None) -> None:
        """Recalculate all nodes for given periods, clearing all caches first.

        Args:
            periods: List of period strings, a single string, or None to use all periods.

        Returns:
            None

        Raises:
            TypeError: If `periods` is not a list, string, or None.

        Examples:
            >>> graph.recalculate_all(["2023", "2024"])
        """
        # Normalize periods input
        if periods is None:
            periods_to_use = self.periods
        elif isinstance(periods, str):
            periods_to_use = [periods]
        elif isinstance(periods, list):
            periods_to_use = periods
        else:
            raise TypeError("Periods must be a list of strings, a single string, or None.")
        # Clear all caches (node-level and central) to force full recalculation
        self.clear_all_caches()
        if not periods_to_use:
            return
        # Recalculate each node for each period
        for node_name in list(self._nodes.keys()):
            for period in periods_to_use:
                try:
                    self.calculate(node_name, period)
                except Exception as e:
                    logger.warning(f"Error recalculating node '{node_name}' for period '{period}': {e}")

    def clear_all_caches(self) -> None:
        """Clear all node-level and central calculation caches.

        Returns:
            None

        Examples:
            >>> graph.clear_all_caches()
        """
        logger.debug(f"Clearing node-level caches for {len(self.nodes)} nodes.")
        for node in self.nodes.values():
            if hasattr(node, "clear_cache"):
                try:
                    node.clear_cache()
                except Exception as e:
                    logger.warning(f"Failed to clear cache for node '{node.name}': {e}")
        # Clear central calculation cache
        self.clear_calculation_cache()
        logger.debug("Cleared central calculation cache.")

    def clear_calculation_cache(self) -> None:
        """Clear the graph's internal calculation cache.

        Returns:
            None

        Examples:
            >>> graph.clear_calculation_cache()
        """
        self._cache.clear()
        logger.debug("Cleared graph calculation cache.")

    def clear(self) -> None:
        """Reset the graph by clearing nodes, periods, metrics, and caches.

        Returns:
            None

        Examples:
            >>> graph.clear()
        """
        self._nodes = {}
        self._periods = []
        self._cache = {}
        self._metric_names = set()
        logger.info("Graph cleared: nodes, periods, metrics, and caches reset.")

    def add_financial_statement_item(self, name: str, values: dict[str, float]) -> FinancialStatementItemNode:
        """Add a basic financial statement item (data node) to the graph.

        Args:
            name: Unique name for the financial statement item node.
            values: Mapping of period strings to float values for this item.

        Returns:
            The newly created `FinancialStatementItemNode`.

        Raises:
            NodeError: If a node with the same name already exists.
            TypeError: If `values` is not a dict or contains invalid types.

        Examples:
            >>> item_node = graph.add_financial_statement_item("SG&A", {"2023": 50.0})
            >>> item_node.get_value("2023")
            50.0
        """
        if name in self._nodes:
            raise NodeError("Node with name already exists", node_id=name)
        if not isinstance(values, dict):
            raise TypeError("Values must be provided as a dict[str, float]")
        # Create a new financial statement item node
        new_node = self._node_factory.create_financial_statement_item(
            name=name, values=values.copy()
        )
        self._nodes[name] = new_node
        # Update periods from node values
        self.add_periods(list(values.keys()))
        logger.info(f"Added FinancialStatementItemNode '{name}' with periods {list(values.keys())}")
        return new_node

    def update_financial_statement_item(
        self, name: str, values: dict[str, float], replace_existing: bool = False
    ) -> FinancialStatementItemNode:
        """Update values for an existing financial statement item node.

        Args:
            name: Name of the existing financial statement item node.
            values: Mapping of new period strings to float values.
            replace_existing: If True, replace existing values entirely; otherwise merge.

        Returns:
            The updated `FinancialStatementItemNode`.

        Raises:
            NodeError: If the node does not exist.
            TypeError: If the node is not a `FinancialStatementItemNode` or `values` is not a dict.

        Examples:
            >>> graph.update_financial_statement_item("SG&A", {"2024": 60.0})
        """
        node = self.manipulator.get_node(name)
        if node is None:
            raise NodeError("Node not found", node_id=name)
        if not isinstance(node, FinancialStatementItemNode):
            raise TypeError(f"Node '{name}' is not a FinancialStatementItemNode")
        if not isinstance(values, dict):
            raise TypeError("Values must be provided as a dict[str, float]")
        if replace_existing:
            node.values = values.copy()
        else:
            node.values.update(values)
        self.add_periods(list(values.keys()))
        logger.info(f"Updated FinancialStatementItemNode '{name}' with periods {list(values.keys())}; replace_existing={replace_existing}")
        return node

    def get_financial_statement_items(self) -> list[Node]:
        """Retrieve all financial statement item nodes from the graph.

        Returns:
            A list of `FinancialStatementItemNode` objects currently in the graph.

        Examples:
            >>> items = graph.get_financial_statement_items()
        """
        from fin_statement_model.core.nodes import (
            FinancialStatementItemNode,
        )  # Keep import local as it's specific

        return [
            node
            for node in self.nodes.values()
            if isinstance(node, FinancialStatementItemNode)
        ]

    def __repr__(self) -> str:
        """Provide a concise, developer-friendly string representation of the graph.

        Summarize total nodes, FS items, calculations, dependencies, and periods.

        Returns:
            A string summarizing the graph's structure and contents.

        Examples:
            >>> repr(graph)
        """
        from fin_statement_model.core.nodes import (
            FinancialStatementItemNode,
        )  # Keep import local

        num_nodes = len(self.nodes)
        periods_str = ", ".join(map(repr, self.periods)) if self.periods else "None"

        fs_item_count = 0
        calc_node_count = 0
        other_node_count = 0
        dependencies_count = 0

        for node in self.nodes.values():
            if isinstance(node, FinancialStatementItemNode):
                fs_item_count += 1
            elif node.has_calculation():
                calc_node_count += 1
                # Prioritize get_dependencies if available, otherwise check inputs
                if hasattr(node, "get_dependencies"):
                    try:
                        dependencies_count += len(node.get_dependencies())
                    except Exception as e:
                        logger.warning(
                            f"Error calling get_dependencies for node '{node.name}': {e}"
                        )
                elif hasattr(node, "inputs"):
                    try:
                        if isinstance(node.inputs, list):
                            # Ensure inputs are nodes with names
                            dep_names = [inp.name for inp in node.inputs if hasattr(inp, "name")]
                            dependencies_count += len(dep_names)
                        elif isinstance(node.inputs, dict):
                            # Assume keys are dependency names for dict inputs
                            dependencies_count += len(node.inputs)
                    except Exception as e:
                        logger.warning(f"Error processing inputs for node '{node.name}': {e}")
            else:
                other_node_count += 1

        repr_parts = [
            f"Total Nodes: {num_nodes}",
            f"FS Items: {fs_item_count}",
            f"Calculations: {calc_node_count}",
        ]
        if other_node_count > 0:
            repr_parts.append(f"Other: {other_node_count}")
        repr_parts.append(f"Dependencies: {dependencies_count}")
        repr_parts.append(f"Periods: [{periods_str}]")

        return f"<{type(self).__name__}({', '.join(repr_parts)})>"

    def has_cycle(self, source_node: Node, target_node: Node) -> bool:
        """Check if a cycle exists from a source node to a target node.

        This method delegates to GraphTraverser.breadth_first_search to determine
        if `target_node` is reachable from `source_node` via dependencies, indicating
        that adding an edge from `target_node` to `source_node` would create a cycle.

        Args:
            source_node: The starting node for cycle detection.
            target_node: The node to detect return path to.

        Returns:
            True if a cycle exists, False otherwise.
        """
        if source_node.name not in self._nodes or target_node.name not in self._nodes:
            return False

        # Use BFS to check reachability via predecessors (dependencies)
        bfs_levels = self.traverser.breadth_first_search(source_node.name, direction="predecessors")
        reachable_nodes = {n for level in bfs_levels for n in level}
        return target_node.name in reachable_nodes

    def get_node(self, name: str) -> Optional[Node]:
        """Retrieve a node from the graph by its name.

        Args:
            name: The unique name of the node to retrieve.

        Returns:
            The `Node` instance if found, else None.

        Examples:
            >>> node = graph.get_node("Revenue")
        """
        return self.manipulator.get_node(name)

    def add_node(self, node: Node) -> None:
        """Add a node to the graph, replacing any existing node with the same name.

        Args:
            node: The `Node` instance to add.

        Returns:
            None

        Examples:
            >>> graph.add_node(custom_node)
        """
        return self.manipulator.add_node(node)

    def remove_node(self, node_name: str) -> None:
        """Remove a node from the graph by name, updating dependencies.

        Args:
            node_name: The name of the node to remove.

        Returns:
            None

        Examples:
            >>> graph.remove_node("OldItem")
        """
        return self.manipulator.remove_node(node_name)

    def replace_node(self, node_name: str, new_node: Node) -> None:
        """Replace an existing node with a new node instance.

        Args:
            node_name: Name of the node to replace.
            new_node: The new `Node` instance to substitute.

        Returns:
            None

        Examples:
            >>> graph.replace_node("Item", updated_node)
        """
        return self.manipulator.replace_node(node_name, new_node)

    def has_node(self, node_id: str) -> bool:
        """Check if a node with the given ID exists in the graph.

        Args:
            node_id: The name of the node to check.

        Returns:
            True if the node exists, False otherwise.

        Examples:
            >>> graph.has_node("Revenue")
        """
        return self.manipulator.has_node(node_id)

    def set_value(self, node_id: str, period: str, value: float) -> None:
        """Set or update the value for a node in a specific period.

        Args:
            node_id: The name of the node.
            period: The period identifier to set the value for.
            value: The float value to assign.

        Returns:
            None

        Raises:
            ValueError: If the period is not recognized by the graph.
            NodeError: If the node does not exist.
            TypeError: If the node does not support setting a value.

        Examples:
            >>> graph.set_value("SG&A", "2024", 55.0)
        """
        return self.manipulator.set_value(node_id, period, value)

    def topological_sort(self) -> list[str]:
        """Perform a topological sort of all graph nodes.

        Returns:
            A list of node IDs in topological order.

        Raises:
            ValueError: If a cycle is detected in the graph.

        Examples:
            >>> order = graph.topological_sort()
        """
        return self.traverser.topological_sort()

    def get_calculation_nodes(self) -> list[str]:
        """Get all calculation node IDs in the graph.

        Returns:
            A list of node names that have associated calculations.

        Examples:
            >>> graph.get_calculation_nodes()
        """
        return self.traverser.get_calculation_nodes()

    def get_dependencies(self, node_id: str) -> list[str]:
        """Get the direct predecessor node IDs (dependencies) for a given node.

        Args:
            node_id: The name of the node to inspect.

        Returns:
            A list of node IDs that the given node depends on.

        Examples:
            >>> graph.get_dependencies("GrossProfit")
        """
        return self.traverser.get_dependencies(node_id)

    def get_dependency_graph(self) -> dict[str, list[str]]:
        """Get the full dependency graph mapping of node IDs to their inputs.

        Returns:
            A dict mapping each node ID to a list of its dependency node IDs.

        Examples:
            >>> graph.get_dependency_graph()
        """
        return self.traverser.get_dependency_graph()

    def detect_cycles(self) -> list[list[str]]:
        """Detect all cycles in the graph's dependency structure.

        Returns:
            A list of cycles, each represented as a list of node IDs.

        Examples:
            >>> graph.detect_cycles()
        """
        return self.traverser.detect_cycles()

    def validate(self) -> list[str]:
        """Validate the graph structure for errors such as cycles or missing nodes.

        Returns:
            A list of validation error messages, empty if valid.

        Examples:
            >>> graph.validate()
        """
        return self.traverser.validate()

    def breadth_first_search(self, start_node: str, direction: str = "successors") -> list[str]:
        """Perform a breadth-first search (BFS) traversal of the graph.

        Args:
            start_node: The starting node ID for BFS.
            direction: Either 'successors' or 'predecessors' to traverse.

        Returns:
            A nested list of node IDs per BFS level.

        Raises:
            ValueError: If `direction` is not 'successors' or 'predecessors'.

        Examples:
            >>> graph.breadth_first_search("Revenue", "successors")
        """
        return self.traverser.breadth_first_search(start_node, direction)

    def get_direct_successors(self, node_id: str) -> list[str]:
        """Get immediate successor node IDs for a given node.

        Args:
            node_id: The name of the node to inspect.

        Returns:
            A list of node IDs that directly follow the given node.

        Examples:
            >>> graph.get_direct_successors("Revenue")
        """
        return self.traverser.get_direct_successors(node_id)

    def get_direct_predecessors(self, node_id: str) -> list[str]:
        """Get immediate predecessor node IDs (inputs) for a given node.

        Args:
            node_id: The name of the node to inspect.

        Returns:
            A list of node IDs that the given node directly depends on.

        Examples:
            >>> graph.get_direct_predecessors("GrossProfit")
        """
        return self.traverser.get_direct_predecessors(node_id)
