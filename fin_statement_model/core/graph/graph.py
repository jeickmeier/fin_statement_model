"""Graph module for core graph operations.

This module provides the `Graph` class that combines manipulation, traversal,
forecasting, and calculation capabilities for building and evaluating financial
statement models.
"""

from __future__ import annotations
import logging
from typing import Any

from .manipulation import GraphManipulationMixin
from .traversal import GraphTraversalMixin
from .forecast_mixin import ForecastOperationsMixin
from fin_statement_model.core.data_manager import DataManager
from fin_statement_model.core.calculation_engine import CalculationEngine
from fin_statement_model.core.nodes import Node

# Configure logging
logger = logging.getLogger(__name__)


class Graph(
    GraphManipulationMixin,
    GraphTraversalMixin,
    ForecastOperationsMixin,
):
    """Represents the financial statement model as a directed graph.

    This class integrates graph manipulation (adding/removing nodes and edges)
    and traversal capabilities. It serves as the central orchestrator, owning
    the shared registry of nodes and managing core components like the
    `DataManager` and `CalculationEngine`.

    Nodes in the graph represent financial items or calculations, and edges
    represent dependencies between them. The `DataManager` handles the storage
    and retrieval of time-series data associated with nodes, while the
    `CalculationEngine` manages the execution of calculations defined by
    calculation nodes.

    Attributes:
        _nodes: A dictionary storing all nodes in the graph, keyed by node name.
                This serves as the single source of truth shared with managers.
        _data_manager: An instance of `DataManager` responsible for handling
                       time-series data (items and periods).
        _calculation_engine: An instance of `CalculationEngine` responsible for
                             managing and executing calculations.
    """

    def __init__(self, periods: list[str] | None = None):
        """Initializes the Graph instance.

        Sets up the core components: the node registry, `DataManager`, and
        `CalculationEngine`. Optionally initializes the graph with a list of
        time periods.

        Args:
            periods: An optional list of strings representing the initial time
                     periods for the financial model (e.g., ["2023", "2024"]).
                     The `DataManager` will handle sorting and ensuring uniqueness.

        Raises:
            TypeError: If `periods` is provided but is not a list.

        Example:
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

        # Create the single source of truth for nodes
        self._nodes: dict[str, Node] = {}

        # Instantiate managers, passing the shared node registry
        # These managers handle their own initialization logic.
        self._data_manager = DataManager(nodes_registry=self._nodes)
        self._calculation_engine = CalculationEngine(nodes_registry=self._nodes)

        # Handle initial periods by adding them via the DataManager
        if periods:
            # Basic validation before passing to manager
            if not isinstance(periods, list):
                raise TypeError("Initial periods must be a list")
            # DataManager.add_periods handles sorting and uniqueness
            self._data_manager.add_periods(periods)

    @property
    def nodes(self) -> dict[str, Node]:
        """Provides access to the dictionary of all nodes in the graph.

        Returns:
            A dictionary where keys are node names (str) and values are
            `Node` objects. This dictionary represents the shared node registry.

        Example:
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
        """Retrieves the list of time periods currently managed by the graph.

        Delegates to the `DataManager` to get the sorted list of unique periods.

        Returns:
            A list of strings representing the time periods in the model.

        Example:
            >>> graph = Graph(periods=["2024", "2023"])
            >>> print(graph.periods)
            ['2023', '2024']
            >>> graph.add_periods(["2025"])
            >>> print(graph.periods)
            ['2023', '2024', '2025']
        """
        return self._data_manager.periods

    def add_periods(self, periods: list[str]) -> None:
        """Adds new time periods to the graph's `DataManager`.

        The `DataManager` ensures that periods are sorted and unique.

        Args:
            periods: A list of strings representing the time periods to add.

        Raises:
            TypeError: If `periods` is not a list.
            ValueError: If any period format is invalid (handled by DataManager).

        Example:
            >>> graph = Graph(periods=["2022"])
            >>> graph.add_periods(["2023", "2022", "2024"])
            >>> print(graph.periods)
            ['2022', '2023', '2024']
            >>> try:
            ...     graph.add_periods("2025") # Must be a list
            ... except TypeError as e:
            ...     print(e)
            Periods must be provided as a list.
        """
        self._data_manager.add_periods(periods)

    def add_calculation(
        self,
        name: str,
        input_names: list[str],
        operation_type: str,
        **kwargs: dict[str, Any],
    ) -> Node:
        """Adds a new calculation node to the graph via the `CalculationEngine`.

        The `CalculationEngine` creates the appropriate `CalculationNode` subclass
        based on `operation_type`, resolves input nodes using the shared registry,
        adds the new node to the registry, and establishes dependencies.

        Args:
            name: The unique name for the new calculation node.
            input_names: A list of names of the nodes that serve as inputs to
                         this calculation.
            operation_type: A string identifying the type of calculation
                            (e.g., "addition", "percentage_growth"). This maps
                            to a specific calculation strategy.
            **kwargs: Additional keyword arguments required by the specific
                      calculation strategy identified by `operation_type`.

        Returns:
            The newly created `Node` object representing the calculation.

        Raises:
            NodeNotFoundError: If any node specified in `input_names` does not
                              exist in the graph's node registry.
            ValueError: If the `name` is invalid, already exists, or if the
                        `operation_type` is not recognized or fails validation.
            TypeError: If the provided `kwargs` do not match the signature
                       required by the chosen calculation strategy.
            CalculationError: For issues during calculation node setup within
                              the engine.

        Example (assuming 'addition' strategy is registered):
            >>> graph = Graph(periods=["2023"])
            >>> rev_node = graph.add_financial_statement_item("Revenue", {"2023": 100})
            >>> cost_node = graph.add_financial_statement_item("Costs", {"2023": 60})
            >>> # Note: The default CalculationEngine uses FormulaCalculationNode for simple ops
            >>> # This example assumes a more sophisticated engine or pre-registration
            >>> # gross_profit = graph.add_calculation(
            >>> #    "GrossProfit", ["Revenue", "Costs"], "subtraction"
            >>> # )
            >>> # Let's assume a simple formula node is created instead for demonstration
            >>> from fin_statement_model.core.nodes import FormulaCalculationNode
            >>> gp_node = FormulaCalculationNode("GrossProfit", {"r": rev_node, "c": cost_node}, "r - c")
            >>> graph.add_node(gp_node) # Add directly for this example
            >>> print("GrossProfit" in graph.nodes)
            True
            >>> print(graph.calculate("GrossProfit", "2023")) # Calculation depends on engine
            40.0
        """
        node = self._calculation_engine.add_calculation(name, input_names, operation_type, **kwargs)
        return node

    def calculate(self, node_name: str, period: str) -> float:
        """Calculates the value of a specific node for a given period.

        Delegates the calculation request to the `CalculationEngine`, which
        handles dependency resolution, execution, and caching.

        Args:
            node_name: The name of the node whose value is to be calculated.
            period: The specific time period for which to calculate the value.

        Returns:
            The calculated float value of the node for the specified period.

        Raises:
            NodeNotFoundError: If the node `node_name` does not exist.
            PeriodNotFoundError: If the `period` does not exist in the `DataManager`.
            CalculationError: If the calculation fails due to missing inputs,
                              cyclic dependencies, or errors within the node's
                              calculation logic.

        Example:
            >>> graph = Graph(periods=["2023"])
            >>> rev_node = graph.add_financial_statement_item("Revenue", {"2023": 100})
            >>> print(graph.calculate("Revenue", "2023"))
            100.0
            >>> cost_node = graph.add_financial_statement_item("Costs", {"2023": 60})
            >>> from fin_statement_model.core.nodes import FormulaCalculationNode
            >>> gp_node = FormulaCalculationNode("GrossProfit", {"r": rev_node, "c": cost_node}, "r - c")
            >>> graph.add_node(gp_node)
            >>> print(graph.calculate("GrossProfit", "2023"))
            40.0
            >>> try:
            ...     graph.calculate("NonExistent", "2023")
            ... except Exception as e: # Actual exception type depends on engine
            ...     print(f"Error: {e}") # Example: Node 'NonExistent' not found
            Error: Node 'NonExistent' not found in registry.
            >>> try:
            ...     graph.calculate("Revenue", "2024")
            ... except Exception as e:
            ...     print(f"Error: {e}") # Example: Period '2024' not found
            Error: Period '2024' not found.
        """
        return self._calculation_engine.calculate(node_name, period)

    def recalculate_all(self, periods: list[str] | None = None) -> None:
        """Triggers a recalculation of all calculation nodes for specified periods.

        Clears existing calculation caches and then instructs the
        `CalculationEngine` to re-evaluate all calculation nodes for the given
        periods (or all managed periods if none are specified). This is useful
        after data updates or changes to the graph structure.

        Args:
            periods: An optional list of periods to recalculate. If None,
                     recalculates for all periods managed by the `DataManager`.
                     Can also be a single period string.

        Example:
            >>> graph = Graph(periods=["2023"])
            >>> rev = graph.add_financial_statement_item("Revenue", {"2023": 100})
            >>> costs = graph.add_financial_statement_item("Costs", {"2023": 50})
            >>> from fin_statement_model.core.nodes import FormulaCalculationNode
            >>> gp = FormulaCalculationNode("GP", {"r": rev, "c": costs}, "r - c")
            >>> graph.add_node(gp)
            >>> # First calculation might populate cache
            >>> val1 = graph.calculate("GP", "2023")
            >>> print(val1)
            50.0
            >>> # Simulate data change
            >>> graph.set_value("Costs", "2023", 60)
            >>> # Value might be stale if cached
            >>> # Recalculate to ensure freshness
            >>> graph.recalculate_all("2023")
            >>> val2 = graph.calculate("GP", "2023")
            >>> print(val2)
            40.0
            >>> # Recalculate all periods (only 2023 here)
            >>> graph.set_value("Revenue", "2023", 110)
            >>> graph.recalculate_all()
            >>> print(graph.calculate("GP", "2023"))
            50.0
        """
        periods_to_use = periods
        if periods_to_use is None:
            periods_to_use = self.periods
        elif isinstance(periods_to_use, str):
            periods_to_use = [periods_to_use]
        elif not isinstance(periods_to_use, list):
            raise TypeError("Periods must be a list of strings, a single string, or None.")

        self.clear_all_caches()
        self._calculation_engine.recalculate_all(periods_to_use)

    def clear_all_caches(self) -> None:
        """Clears all calculation-related caches within the graph.

        This includes clearing caches possibly held by individual nodes
        (like `StrategyCalculationNode`) and the central cache within the
        `CalculationEngine`. This ensures subsequent calculations start fresh.
        Logs warnings if clearing fails for specific nodes or the engine.

        Example:
            >>> graph = Graph(periods=["2023"])
            >>> # ... add nodes and perform calculations ...
            >>> # Assume some caches might be populated in nodes or engine
            >>> graph.clear_all_caches()
            >>> # Subsequent calls to graph.calculate will recompute from scratch
        """
        logger.debug(f"Clearing caches for {len(self.nodes)} nodes.")
        for node in self.nodes.values():
            if hasattr(node, "clear_cache"):
                try:
                    node.clear_cache()
                except Exception as e:
                    logger.warning(f"Failed to clear cache for node '{node.name}': {e}")

        logger.debug("Clearing calculation engine cache.")
        if hasattr(self._calculation_engine, "clear_cache"):
            try:
                self._calculation_engine.clear_cache()
            except Exception as e:
                logger.warning(f"Could not clear calculation engine cache: {e}", exc_info=True)

    def add_financial_statement_item(self, name: str, values: dict[str, float]) -> Node:
        """Adds a basic financial statement item (data node) to the graph.

        Delegates the creation and storage of the `FinancialStatementItemNode`
        and its associated time-series data to the `DataManager`.

        Args:
            name: The unique name for the financial statement item node.
            values: A dictionary where keys are period strings and values are
                    the corresponding float values for this item.

        Returns:
            The newly created `FinancialStatementItemNode` object.

        Raises:
            NodeError: If a node with the same name already exists.
            PeriodNotFoundError: If any period key in `values` is not recognized
                                by the `DataManager`.
            TypeError: If `values` is not a dictionary or contains invalid types.

        Example:
            >>> graph = Graph(periods=["2023", "2024"])
            >>> item_node = graph.add_financial_statement_item("SG&A", {"2023": 50.0})
            >>> print(item_node.name)
            SG&A
            >>> print(item_node.get_value("2023"))
            50.0
            >>> print("SG&A" in graph.nodes)
            True
            >>> # Add data for another period later
            >>> graph.set_value("SG&A", "2024", 55.0)
            >>> print(item_node.get_value("2024"))
            55.0
            >>> try:
            ...     graph.add_financial_statement_item("Existing", {"2023": 10})
            ...     graph.add_financial_statement_item("Existing", {"2023": 20})
            ... except Exception as e: # Actual exception type depends on DataManager
            ...     print(f"Error: {e}") # Example: Node 'Existing' already exists
            Error: Node 'Existing' already exists.
        """
        node = self._data_manager.add_item(name, values)
        return node

    def get_financial_statement_items(self) -> list[Node]:
        """Retrieves all nodes that represent basic financial statement items.

        Filters the main node registry to return only instances of
        `FinancialStatementItemNode`.

        Returns:
            A list containing all `FinancialStatementItemNode` objects
            currently in the graph.

        Example:
            >>> graph = Graph(periods=["2023"])
            >>> item1 = graph.add_financial_statement_item("Item1", {"2023": 1})
            >>> item2 = graph.add_financial_statement_item("Item2", {"2023": 2})
            >>> # Add a non-item node (example)
            >>> from fin_statement_model.core.nodes import Node
            >>> graph.add_node(Node("CalcNode"))
            >>> fs_items = graph.get_financial_statement_items()
            >>> print(len(fs_items))
            2
            >>> print(sorted([item.name for item in fs_items]))
            ['Item1', 'Item2']
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
        """Provides a concise, developer-friendly string representation of the graph.

        Summarizes key statistics like the total number of nodes, counts of
        different node types (Financial Statement Items, Calculations), the
        number of dependencies (edges), and the list of managed periods.

        Returns:
            A string summarizing the graph's structure and contents.

        Example:
            >>> graph = Graph(periods=["2023"])
            >>> graph.add_financial_statement_item("Revenue", {"2023": 100})
            >>> graph.add_financial_statement_item("COGS", {"2023": 60})
            >>> # Assume a calculation node 'GP' depends on Revenue, COGS
            >>> from fin_statement_model.core.nodes import FormulaCalculationNode
            >>> gp_node = FormulaCalculationNode("GP", {"r": graph.nodes['Revenue'], "c": graph.nodes['COGS']}, "r - c")
            >>> graph.add_node(gp_node)
            >>> print(repr(graph))
            <Graph(Total Nodes: 3, FS Items: 2, Calculations: 1, Dependencies: 2, Periods: ['2023'])>
            >>> graph_empty = Graph()
            >>> print(repr(graph_empty))
            <Graph(Total Nodes: 0, FS Items: 0, Calculations: 0, Dependencies: 0, Periods: [None])>
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
        """Checks if there is a cycle in the graph starting from a given source node to a target node.

        This method uses Depth-First Search (DFS) to detect cycles in the graph.

        Args:
            source_node: The starting node of the cycle detection.
            target_node: The target node to which the cycle detection is performed.

        Returns:
            True if there is a cycle in the graph from the source node to the target node, False otherwise.

        Raises:
            NodeNotFoundError: If the source_node or target_node does not exist in the graph.
        """
        if source_node not in self._nodes or target_node not in self._nodes:
            return False  # Or raise error?

        # Simple DFS to detect cycles
        path = {source_node}
        stack = [source_node]
        while stack:
            curr = stack[-1]
            if curr not in path:
                path.add(curr)

            # Add neighbors to stack
            pushed = False
            neighbors = self.get_direct_predecessors(curr)
            # Use list comprehension for PERF401
            unvisited_neighbors = [n for n in neighbors if n not in path]

            for neighbor in unvisited_neighbors:
                if neighbor == target_node:
                    return True
                stack.append(neighbor)
                pushed = True
                break

            if not pushed:
                stack.pop()

        return False
