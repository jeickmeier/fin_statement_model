"""
Data management functionality for the Financial Statement Model.

This module provides the DataManager class which is responsible for managing
financial data in the graph, including adding and updating financial statement items.
"""

from typing import Dict, List
from .graph import Graph
from .nodes import FinancialStatementItemNode, Node
from .node_factory import NodeFactory


class DataManager:
    """
    Manages financial data in the graph, including adding and updating financial statement items.

    The DataManager is responsible for:
    - Adding financial statement items to the graph
    - Updating item values
    - Validating financial data

    It ensures proper data management according to financial statement conventions.

    Attributes:
        graph (Graph): The graph to manage data for
    """

    def __init__(self, graph: Graph):
        """
        Initialize a DataManager with a reference to the graph.

        Args:
            graph (Graph): The graph to manage data for
        """
        self.graph = graph

    def add_item(self, name: str, values: Dict[str, float]) -> Node:
        """
        Add a financial statement item node to the graph with historical values.

        Args:
            name: The name/identifier of the financial statement item (e.g. "revenue", "expenses")
            values: Dictionary mapping time periods to numerical values (e.g. {"2022": 1000.0})

        Returns:
            Node: The newly created node

        Raises:
            ValueError: If a node with the given name already exists in the graph

        Example:
            data_manager.add_item("revenue", {"2022": 1000.0, "2023": 1200.0})
        """
        # Check if node already exists
        if name in self.graph.nodes:
            raise ValueError(f"Node '{name}' already exists in the graph")

        # Use NodeFactory to create the node
        node = NodeFactory.create_financial_statement_item(name, values)
        self.graph.add_node(node)
        return node

    def update_item(
        self, name: str, values: Dict[str, float], replace_existing: bool = False
    ) -> Node:
        """
        Update values for an existing financial statement item.

        Args:
            name: The name/identifier of the financial statement item to update
            values: Dictionary mapping time periods to numerical values to update
            replace_existing: If True, replace all existing values; if False, merge with existing values

        Returns:
            Node: The updated node

        Raises:
            ValueError: If no node with the given name exists in the graph
        """
        node = self.graph.get_node(name)
        if node is None:
            raise ValueError(f"No node found with name '{name}'")

        if not isinstance(node, FinancialStatementItemNode):
            raise ValueError(f"Node '{name}' is not a financial statement item node")

        if replace_existing:
            node.values = values
        else:
            # Merge new values with existing ones
            for period, value in values.items():
                node.values[period] = value

        # Refresh the node in the graph
        self.graph.add_node(node)
        return node

    def delete_item(self, name: str) -> bool:
        """
        Delete a financial statement item from the graph.

        Args:
            name: The name/identifier of the financial statement item to delete

        Returns:
            bool: True if the item was deleted, False if it didn't exist

        Raises:
            ValueError: If the item is referenced by calculation nodes
        """
        # Check if the node exists
        if name not in self.graph.nodes:
            return False

        # Check if the node is referenced by calculation nodes
        for node_name, node in self.graph.nodes.items():
            # Skip the node we're trying to delete
            if node_name == name:
                continue

            if hasattr(node, "inputs") and node.inputs:
                try:
                    # Handle both regular lists and mock objects
                    for input_node in node.inputs:
                        if hasattr(input_node, "name") and input_node.name == name:
                            raise ValueError(
                                f"Cannot delete node '{name}' because it is referenced by '{node_name}'"
                            )
                except (TypeError, AttributeError):
                    # Skip if inputs is not iterable or has other issues
                    continue  # pragma: no cover

        # Delete the node
        del self.graph.nodes[name]
        return True

    def copy_forward_values(self, periods: List[str]) -> None:
        """
        Copy forward the last historical value for each financial statement item
        to fill in missing forecast periods.

        Args:
            periods: List of all periods in chronological order
        """
        for node_name, node in self.graph.nodes.items():
            if isinstance(node, FinancialStatementItemNode):
                # Find periods with values and their indices
                periods_with_values = {}
                for period in node.values:
                    if period in periods:
                        idx = periods.index(period)
                        periods_with_values[idx] = period

                if not periods_with_values:
                    continue  # No historical data to copy

                # Sort period indices
                sorted_indices = sorted(periods_with_values.keys())

                # Fill in missing periods by copying from the previous known period
                for i, period in enumerate(periods):
                    if period not in node.values:
                        # Find the most recent period with a value
                        prev_idx = None
                        for idx in sorted_indices:
                            if idx < i:
                                prev_idx = idx
                            else:
                                break

                        # Copy value from the previous period if found
                        if prev_idx is not None:
                            prev_period = periods_with_values[prev_idx]
                            node.values[period] = node.values[prev_period]
