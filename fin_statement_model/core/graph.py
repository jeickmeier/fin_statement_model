"""
Graph data structure for Financial Statement Model.

This module provides the graph data structure for the Financial Statement Model,
representing nodes and their relationships.
"""

import logging
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

from .nodes import Node, CalculationNode, FinancialStatementItemNode
from .errors import (
    NodeError,
)



# Configure logging
logger = logging.getLogger(__name__)


class Graph:
    """
    A Graph holds nodes and their relationships, enabling calculation of financial metrics across multiple periods.

    The Graph class provides the core data structure for representing financial statements and calculations as a directed graph.
    Each node in the graph represents either a raw financial statement item (like revenue or expenses) or a calculation
    between other nodes (like profit = revenue - expenses).

    The graph structure ensures proper dependency management and calculation order, allowing complex financial metrics
    to be derived from raw financial data across multiple time periods.

    Attributes:
        nodes (Dict[str, Node]): Dictionary mapping node names to Node objects

    Example:
        graph = Graph()
        revenue_node = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        expenses_node = FinancialStatementItemNode("expenses", {"2022": 600.0})
        graph.add_node(revenue_node)
        graph.add_node(expenses_node)
        profit = graph.calculate("revenue", "2022") - graph.calculate("expenses", "2022")
    """

    def __init__(self, periods=None):
        """
        Initialize a Graph with optional periods.

        Args:
            periods: Optional list of period identifiers

        Raises:
            TypeError: If periods is not a list
            ValueError: If periods is not sorted
        """
        if periods is not None and not isinstance(periods, list):
            raise TypeError("Periods must be a list")
        if periods is not None and periods != sorted(periods):
            raise ValueError("Periods must be sorted")
        self.nodes = {}
        self._periods = periods or []
        self._calculation_engine = None

    def set_calculation_engine(self, engine):
        """Set the calculation engine for this graph."""
        # Check if it's a mock object or a real CalculationEngine
        if not (hasattr(engine, "calculate") and hasattr(engine, "set_graph")):
            raise TypeError("Expected CalculationEngine instance")
        self._calculation_engine = engine
        self._calculation_engine.set_graph(self)

    def add_node(self, node: Node):
        """
        Add a node to the graph.

        Args:
            node (Node): The node object to add to the graph. Must be a subclass of Node.

        Raises:
            ValueError: If a node with the same name already exists in the graph.
            TypeError: If the provided node is not a subclass of Node.

        Example:
            # Add a financial statement item node
            revenue_node = FinancialStatementItemNode("revenue", {"2022": 1000.0})
            graph.add_node(revenue_node)

            # Add a calculation node
            profit_node = SubtractionCalculationNode("profit", [revenue_node, expenses_node])
            graph.add_node(profit_node)
        """
        old_node = self.nodes.get(node.name)
        self.nodes[node.name] = node

        # If we're replacing a node, update any calculation nodes that depend on it
        if old_node is not None:
            self._update_calculation_nodes()

    def _update_calculation_nodes(self):
        """Update calculation nodes when their input nodes change."""
        for node in self.nodes.values():
            if isinstance(node, CalculationNode) and hasattr(node, "input_names"):
                # Update the inputs list with current nodes
                node.inputs = [self.get_node(name) for name in node.input_names]

    def get_node(self, name: str) -> Optional[Node]:
        """
        Retrieve a node from the graph by its name.

        Args:
            name (str): The name/identifier of the node to retrieve

        Returns:
            Optional[Node]: The node with the given name if it exists, None otherwise

        Example:
            # Get a node by name
            revenue_node = graph.get_node("revenue")
            if revenue_node:
                value = revenue_node.calculate("2022")

            # Handle missing node
            expenses_node = graph.get_node("expenses")
            if expenses_node is None:
                print("Expenses node not found")
        """
        return self.nodes.get(name)

    def calculate(self, node_name: str, period: str) -> float:
        """
        Calculate the value of a node for a given period.

        Args:
            node_name (str): The name/identifier of the node to calculate
            period (str): The time period to calculate the value for (e.g. "FY2022")

        Returns:
            float: The calculated value for the specified node and period

        Raises:
            ValueError: If the node does not exist in the graph
            ValueError: If the period is not found in the node's data
            ValueError: If there is an error performing the calculation (e.g. division by zero)

        Example:
            # Calculate revenue for FY2022
            revenue = graph.calculate("revenue", "FY2022")

            # Calculate gross profit margin for FY2021
            gpm = graph.calculate("gross_profit_margin", "FY2021")
        """
        # Use calculation engine if available
        if self._calculation_engine:
            return self._calculation_engine.calculate(node_name, period)

        # Fall back to direct node calculation
        node = self.get_node(node_name)
        if node is None:
            raise ValueError(f"Node '{node_name}' not found.")
        return node.calculate(period)

    def clear_all_caches(self):
        """
        Clear calculation caches for all nodes in the graph.

        This method iterates through all nodes in the graph and calls their clear_cache()
        method, removing any cached calculation results. This ensures future calculations
        will be recomputed rather than using cached values.

        Example:
            # Clear all node caches
            graph.clear_all_caches()

            # Future calculations will be recomputed
            revenue = graph.calculate("revenue", "FY2022")
        """
        for node in self.nodes.values():
            node.clear_cache()

    def topological_sort(self):
        """
        Perform a topological sort of the nodes in the graph.

        This method analyzes the dependencies between nodes and returns them in a valid
        processing order where each node appears after all of its dependencies. The sort
        is based on the input nodes referenced by calculation and metric nodes.

        Returns:
            List[str]: A list of node names in topologically sorted order

        Raises:
            ValueError: If a cycle is detected in the node dependencies

        Example:
            # Get nodes in dependency order
            sorted_nodes = graph.topological_sort()

            # Process nodes in correct order
            for node_name in sorted_nodes:
                node = graph.get_node(node_name)
                value = node.calculate("2022")
        """
        # Build adjacency (reverse: from inputs to node)
        in_degree = {node_name: 0 for node_name in self.nodes}
        adjacency = {node_name: [] for node_name in self.nodes}

        # Determine dependencies:
        for node_name, node in self.nodes.items():
            # Identify input nodes if this is a calculation node
            if hasattr(node, "inputs"):
                for inp in node.inputs:
                    # inp is a Node, adjacency from inp to node_name
                    adjacency[inp.name].append(node_name)
                    in_degree[node_name] += 1

        # Topological sort using Kahn's algorithm
        queue = [n for n in in_degree if in_degree[n] == 0]
        topo_order = []
        while queue:
            current = queue.pop()
            topo_order.append(current)
            for nbr in adjacency[current]:
                in_degree[nbr] -= 1
                if in_degree[nbr] == 0:
                    queue.append(nbr)

        if len(topo_order) != len(self.nodes):
            raise ValueError(
                "Cycle detected in graph, can't do a valid topological sort."
            )

        return topo_order

    def recalculate_all(self, period: str):
        """
        Recalculate all nodes for the given period.

        Args:
            period: The time period to recalculate values for

        Raises:
            ValueError: If the period is not in graph periods
        """
        if period not in self._periods:
            raise ValueError(f"Period '{period}' not in graph periods")

        # Clear all caches first
        self.clear_all_caches()

        # Get topologically sorted order to ensure proper calculation order
        order = self.topological_sort()

        # Force recalculation of each node
        for node_name in order:
            node = self.get_node(node_name)
            try:
                # Force recalculation by clearing individual node cache
                if hasattr(node, "_cache"):
                    node._cache.clear()
                value = node.calculate(period)
                # Store the result back in cache if needed
                if hasattr(node, "_cache"):
                    node._cache[period] = value
            except ValueError:
                # Skip if period not valid for this node
                continue

    def replace_node(self, node_name: str, new_node: Node):
        """
        Replace a node in the graph while updating any calculation nodes that reference it.

        Args:
            node_name: The name of the node to replace
            new_node: The new node instance
        """
        self.nodes[node_name] = new_node
        self._update_calculation_nodes()

    def import_data(self, data: Dict[str, Dict[str, float]]) -> None:
        """
        Import data into the graph.

        Args:
            data: Dictionary mapping node IDs to period values
                Format: {node_id: {period: value, ...}, ...}

        Raises:
            ValueError: If the data format is invalid
        """
        # Validate data structure first
        for node_id, period_values in data.items():
            if not isinstance(period_values, dict):
                raise ValueError(
                    f"Invalid data format for node '{node_id}': expected dict, got {type(period_values)}"
                )

            # Validate values are numbers
            for period, value in period_values.items():
                if not isinstance(value, (int, float)):
                    raise ValueError(
                        f"Invalid value for node '{node_id}' period '{period}': expected number, got {type(value)}"
                    )

        # Collect all periods from the data
        all_periods = set()
        for period_values in data.values():
            all_periods.update(period_values.keys())

        # Update graph periods if not already set
        if not self._periods:
            self._periods = sorted(all_periods)
        elif not all_periods.issubset(self._periods):
            raise ValueError("Data contains periods not in graph periods")

        # Create nodes and set values
        for node_id, period_values in data.items():
            # Create node if it doesn't exist
            if not self.has_node(node_id):
                self.add_node(FinancialStatementItemNode(node_id, {}))

            # Set values
            for period, value in period_values.items():
                self.set_value(node_id, period, value)

    def export_data(self) -> Dict[str, Dict[str, float]]:
        """
        Export data from the graph.

        Returns:
            Dict[str, Dict[str, float]]: Dictionary mapping node IDs to period values
                Format: {node_id: {period: value, ...}, ...}
        """
        data = {}
        for node_id, node in self.nodes.items():
            if hasattr(node, "values"):
                data[node_id] = node.values.copy()
        return data

    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert the graph data to a DataFrame.

        Returns:
            pd.DataFrame: DataFrame with node IDs as index and periods as columns
        """
        # Get all periods
        periods = sorted(self._periods)

        # Create data
        data = {}
        for node_id, node in self.nodes.items():
            row = {}
            for period in periods:
                row[period] = node.values.get(period, np.nan)
            data[node_id] = row

        # Create DataFrame
        df = pd.DataFrame.from_dict(data, orient="index")

        # Set index name
        df.index.name = "node_id"

        return df

    @property
    def periods(self) -> List[str]:
        """
        Get all periods in the graph.

        Returns:
            List[str]: List of periods
        """
        return sorted(self._periods)

    def get_calculation_nodes(self) -> List[str]:
        """
        Get all nodes that have calculations.

        Returns:
            List[str]: List of node IDs
        """
        return [
            node_id for node_id, node in self.nodes.items() if node.has_calculation()
        ]

    def get_dependencies(self, node_id: str) -> List[str]:
        """
        Get the dependencies of a node.

        Args:
            node_id: ID of the node to get dependencies for

        Returns:
            List[str]: List of dependency node IDs

        Raises:
            NodeError: If the node doesn't exist
        """
        node = self.get_node(node_id)
        if not node:
            raise NodeError(message=f"Node '{node_id}' does not exist", node_id=node_id)

        # If node has inputs, those are the dependencies
        if hasattr(node, "inputs"):
            return [inp.name for inp in node.inputs]

        # No dependencies
        return []

    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """
        Get the full dependency graph.

        Returns:
            Dict[str, List[str]]: Dictionary mapping node IDs to their dependencies
        """
        dependencies = {}
        for node_id, node in self.nodes.items():
            try:
                # If node has inputs, those are the dependencies
                if hasattr(node, "inputs"):
                    dependencies[node_id] = [inp.name for inp in node.inputs]
                else:
                    dependencies[node_id] = []
            except NodeError:
                dependencies[node_id] = []
        return dependencies

    def detect_cycles(self) -> List[List[str]]:
        """
        Detect cycles in the dependency graph.

        Returns:
            List[List[str]]: List of cycles, each represented as a list of node IDs
        """
        # Get dependency graph
        dependency_graph = self.get_dependency_graph()

        # Initialize tracking variables
        visited = set()
        rec_stack = set()
        cycles = []

        # DFS function to detect cycles
        def dfs_detect_cycles(node_id, path=None):
            if path is None:
                path = []

            # Node is in recursion stack, cycle detected
            if node_id in rec_stack:
                # Find cycle start index
                cycle_start = path.index(node_id)
                cycle = path[cycle_start:] + [node_id]
                # Only add if this cycle hasn't been found before
                if cycle not in cycles:
                    cycles.append(cycle)
                return

            # Node already visited, no need to process again
            if node_id in visited:
                return

            # Add node to visited and recursion stack
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            # Visit dependencies
            for dep_id in dependency_graph.get(node_id, []):
                dfs_detect_cycles(dep_id, path[:])

            # Remove node from recursion stack
            rec_stack.remove(node_id)

        # Run DFS for each node
        for node_id in self.nodes:
            if node_id not in visited:
                dfs_detect_cycles(node_id)

        return cycles

    def validate(self) -> List[str]:
        """
        Validate the graph structure.

        Returns:
            List[str]: List of validation errors, or empty list if valid
        """
        errors = []

        # Check for cycles
        cycles = self.detect_cycles()
        if cycles:
            for cycle in cycles:
                errors.append(f"Circular dependency detected: {' -> '.join(cycle)}")

        # Check for missing dependencies
        for node_id, node in self.nodes.items():
            if hasattr(node, "inputs"):
                for inp in node.inputs:
                    if not self.has_node(inp.name):
                        errors.append(
                            f"Node '{node_id}' depends on non-existent node '{inp.name}'"
                        )

        return errors

    def has_node(self, id: str) -> bool:
        """
        Check if a node exists.

        Args:
            id: The ID of the node to check

        Returns:
            bool: True if the node exists, False otherwise
        """
        return id in self.nodes

    def remove_node(self, id: str) -> None:
        """
        Remove a node from the graph.

        Args:
            id: The ID of the node to remove

        Raises:
            NodeError: If the node doesn't exist
        """
        if id not in self.nodes:
            raise NodeError(message=f"Node '{id}' does not exist", node_id=id)

        # Remove node
        del self.nodes[id]

        # Clear calculation cache if engine exists
        if self._calculation_engine:
            try:
                self._calculation_engine.clear_cache()
            except Exception as e:
                logger.error(f"Error clearing calculation engine cache: {e}")

    def clear(self) -> None:
        """Clear all nodes from the graph."""
        self.nodes = {}
        self._periods = []
        if self._calculation_engine:
            try:
                self._calculation_engine.reset()
            except Exception as e:
                logger.error(f"Error resetting calculation engine: {e}")

    def set_value(self, node_id: str, period: str, value: float) -> None:
        """
        Set the value for a node in a specific period.

        Args:
            node_id: ID of the node to set the value for
            period: Period to set the value for
            value: Value to set

        Raises:
            NodeError: If the node doesn't exist
            ValueError: If the period is not in graph periods
        """
        if period not in self._periods:
            raise ValueError(f"Period '{period}' not in graph periods")

        node = self.get_node(node_id)
        if not node:
            raise NodeError(message=f"Node '{node_id}' does not exist", node_id=node_id)

        # Set value
        node.set_value(period, value)

        # Clear calculation cache if engine exists
        if self._calculation_engine:
            try:
                self._calculation_engine.clear_cache()
            except Exception as e:
                logger.error(f"Error clearing calculation engine cache: {e}")
