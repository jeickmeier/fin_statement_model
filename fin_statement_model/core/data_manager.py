"""Data management functionality for the Financial Statement Model.

This module provides the DataManager class which is responsible for managing
financial data in the graph, including adding and updating financial statement items.
"""

from typing import Optional
from .nodes import Node, FinancialStatementItemNode
from .node_factory import NodeFactory
import logging

logger = logging.getLogger(__name__)


class DataManager:
    """Manages financial data within a shared node registry.

    Responsibilities:
        - Adding/updating financial statement item nodes to the shared registry.
        - Managing the list of unique time periods encountered.

    Attributes:
        nodes (Dict[str, Node]): The shared dictionary storing all nodes.
        periods (List[str]): A sorted list of unique time periods encountered.

    Example:
        >>> shared_nodes = {}
        >>> data_manager = DataManager(shared_nodes)
        >>> revenue_node = data_manager.add_item(
        ...     "Revenue", {"2023Q1": 1000, "2023Q2": 1100}
        ... )
        >>> print(data_manager.get_node("Revenue"))
        FinancialStatementItemNode(name='Revenue', ...)
        >>> print(data_manager.periods)
        ['2023Q1', '2023Q2']
    """

    def __init__(self, nodes_registry: dict[str, Node]):
        """Initialize the DataManager with a shared node registry.

        Args:
            nodes_registry: The dictionary instance shared across graph components
                            to store all nodes. This dictionary will be mutated
                            by the DataManager.
        """
        self._node_factory = NodeFactory()
        self._nodes = nodes_registry
        self._periods: list[str] = []

    def add_periods(self, periods: list[str]) -> None:
        """Add unique periods based on data encountered.

        Maintains a sorted list of unique periods seen across all data items.

        Args:
            periods: List of period strings to add. If duplicates exist within
                     the list or compared to existing periods, they are ignored.

        Example:
            >>> shared_nodes = {}
            >>> data_manager = DataManager(shared_nodes)
            >>> data_manager.add_periods(["2023Q1", "2023Q2"])
            >>> data_manager.add_periods(["2023Q2", "2023Q3"])
            >>> print(data_manager.periods)
            ['2023Q1', '2023Q2', '2023Q3']
        """
        # Use a set to handle duplicates within the input list efficiently
        unique_incoming = set(periods)
        new_periods = [p for p in unique_incoming if p not in self._periods]
        if new_periods:
            self._periods.extend(new_periods)
            self._periods.sort()
            logger.debug(f"Added periods: {new_periods}. Current periods: {self._periods}")

    def add_node(self, node: Node) -> Node:
        """Add a node directly to the shared registry.

        This method is for adding any type of node, including custom or
        calculation nodes. For standard financial data items, prefer `add_item`.
        If a node with the same name already exists, it will be overwritten,
        and a warning will be logged.

        Args:
            node: The node instance to add.

        Returns:
            Node: The added node.

        Example:
            >>> from fin_statement_model.core.nodes import CalculationNode
            >>> shared_nodes = {}
            >>> data_manager = DataManager(shared_nodes)
            >>> # Assume GrossProfitNode is a subclass of CalculationNode
            >>> # gp_node = GrossProfitNode(name="GrossProfit", ...)
            >>> # data_manager.add_node(gp_node)
            >>> # print(data_manager.get_node("GrossProfit"))
            # GrossProfitNode(name='GrossProfit', ...)
        """
        if node.name in self._nodes:
            logger.warning(f"Overwriting node '{node.name}' in shared registry.")
        self._nodes[node.name] = node
        logger.debug(f"Added node '{node.name}' directly to shared registry.")
        return node

    def get_node(self, name: str) -> Optional[Node]:
        """Get a node by name from the shared registry.

        Args:
            name: The name of the node to retrieve.

        Returns:
            Optional[Node]: The node instance if found, otherwise None.

        Example:
            >>> shared_nodes = {}
            >>> data_manager = DataManager(shared_nodes)
            >>> data_manager.add_item("COGS", {"2023": 500})
            FinancialStatementItemNode(name='COGS', values={'2023': 500.0})
            >>> cogs_node = data_manager.get_node("COGS")
            >>> print(cogs_node.name if cogs_node else None)
            COGS
            >>> print(data_manager.get_node("NonExistent"))
            None
        """
        return self._nodes.get(name)

    def add_item(self, name: str, values: dict[str, float]) -> FinancialStatementItemNode:
        """Add a financial statement item node to the shared registry.

        Creates a `FinancialStatementItemNode` with the given name and values,
        adds it to the registry, and updates the list of known periods.

        Args:
            name: Name of the financial statement item (e.g., "Revenue", "COGS").
            values: Dictionary mapping period strings (e.g., "2023Q1") to
                    numerical values.

        Returns:
            FinancialStatementItemNode: The created and registered node.

        Raises:
            ValueError: If a node with the same name already exists.

        Example:
            >>> shared_nodes = {}
            >>> data_manager = DataManager(shared_nodes)
            >>> revenue = data_manager.add_item("Revenue", {"2023": 1000, "2024": 1200})
            >>> print(revenue.name)
            Revenue
            >>> print(data_manager.get_node("Revenue").values)
            {'2023': 1000.0, '2024': 1200.0}
            >>> print(data_manager.periods)
            ['2023', '2024']
        """
        if name in self._nodes:
            raise ValueError(f"Node with name '{name}' already exists in the registry.")

        node = FinancialStatementItemNode(name=name, values=values)

        self._nodes[name] = node
        logger.info(f"Added FinancialStatementItemNode '{name}' to shared registry.")

        self.add_periods(list(values.keys()))

        return node

    def update_item(
        self, name: str, values: dict[str, float], replace_existing: bool = False
    ) -> FinancialStatementItemNode:
        """Update values for an existing financial statement item in the shared registry.

        Finds the node by name and updates its `values` dictionary. Can either
        merge new values with existing ones or completely replace them. Also
        updates the list of known periods.

        Args:
            name: Name of the financial statement item to update.
            values: Dictionary mapping periods to new or updated values.
            replace_existing: If True, the existing `values` dictionary is
                              discarded and replaced with the provided `values`.
                              If False (default), the existing `values`
                              dictionary is updated with the new key-value pairs,
                              overwriting values for existing periods if they
                              overlap.

        Returns:
            FinancialStatementItemNode: The updated node.

        Raises:
            ValueError: If the node is not found in the registry.
            TypeError: If the found node is not a `FinancialStatementItemNode`.

        Example:
            >>> shared_nodes = {}
            >>> data_manager = DataManager(shared_nodes)
            >>> item_node = data_manager.add_item("Expenses", {"2023": 500})
            >>> # Merge new/updated values
            >>> updated_node = data_manager.update_item(
            ...     "Expenses", {"2023": 550, "2024": 600}
            ... )
            >>> print(updated_node.values)
            {'2023': 550.0, '2024': 600.0}
            >>> # Replace all values
            >>> replaced_node = data_manager.update_item(
            ...     "Expenses", {"2025": 700}, replace_existing=True
            ... )
            >>> print(replaced_node.values)
            {'2025': 700.0}
            >>> print(data_manager.periods)
            ['2023', '2024', '2025']
        """
        node = self._nodes.get(name)
        if node is None:
            raise ValueError(f"Node '{name}' not found in registry for update.")

        if not isinstance(node, FinancialStatementItemNode):
            raise TypeError(
                f"Cannot update item values for node '{name}', "
                f"it is not a FinancialStatementItemNode "
                f"(type: {type(node).__name__})"
            )

        if replace_existing:
            node.values = values.copy()
            logger.debug(f"Replaced values for item '{name}'.")
        else:
            node.values.update(values)
            logger.debug(f"Updated values for item '{name}'.")

        self.add_periods(list(values.keys()))

        return node

    def delete_item(self, name: str) -> bool:
        """Delete a node (presumably an item) from the shared registry.

        Args:
            name: Name of the node to delete.

        Returns:
            bool: True if the node was found and deleted, False otherwise.

        Example:
            >>> shared_nodes = {}
            >>> data_manager = DataManager(shared_nodes)
            >>> data_manager.add_item("TempData", {"2023": 1})
            FinancialStatementItemNode(name='TempData', values={'2023': 1.0})
            >>> deleted = data_manager.delete_item("TempData")
            >>> print(deleted)
            True
            >>> print(data_manager.get_node("TempData"))
            None
            >>> not_deleted = data_manager.delete_item("NonExistent")
            >>> print(not_deleted)
            False
        """
        if name in self._nodes:
            del self._nodes[name]
            logger.info(f"Deleted node '{name}' from shared registry.")
            return True
        logger.warning(f"Attempted to delete non-existent node '{name}'.")
        return False

    @property
    def periods(self) -> list[str]:
        """Get the sorted list of unique periods encountered across all items.

        Returns:
            List[str]: A sorted list of unique period strings.

        Example:
            >>> shared_nodes = {}
            >>> data_manager = DataManager(shared_nodes)
            >>> data_manager.add_item("A", {"2024": 1, "2022": 2})
            FinancialStatementItemNode(...)
            >>> data_manager.add_item("B", {"2023": 3, "2022": 4})
            FinancialStatementItemNode(...)
            >>> print(data_manager.periods)
            ['2022', '2023', '2024']
        """
        return self._periods
