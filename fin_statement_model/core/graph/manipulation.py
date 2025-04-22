"""Provides graph manipulation capabilities as a mixin class.

This mixin is intended to be used by the main `Graph` class. It encapsulates
operations related to adding, removing, retrieving, and modifying nodes within
the graph structure. It assumes the presence of a `nodes` dictionary and
potentially a `_calculation_engine` and `_periods` list in the class it's mixed into.
"""

import logging
from typing import TYPE_CHECKING, Optional

# Import Node for runtime isinstance checks. Other heavy imports are limited to TYPE_CHECKING to
# prevent unnecessary circular dependencies at runtime.
from fin_statement_model.core.nodes import Node

if TYPE_CHECKING:
    from fin_statement_model.core.calculation_engine import CalculationEngine
    from fin_statement_model.core.data_manager import DataManager

from fin_statement_model.core.errors import NodeError

logger = logging.getLogger(__name__)


class GraphManipulationMixin:
    """Mixin class providing methods for manipulating the graph's nodes.

    Includes operations like adding, removing, replacing, and retrieving nodes,
    as well as setting node values and clearing caches. Relies on the main class
    (e.g., `Graph`) to provide the `nodes` dictionary and potentially other
    attributes like `_calculation_engine` and `_periods`.
    """

    # Type hints for attributes assumed to exist in the main Graph class
    _nodes: dict[str, "Node"]
    _calculation_engine: "CalculationEngine"
    _data_manager: "DataManager"
    _periods: list[str]

    def set_calculation_engine(self, engine: "CalculationEngine") -> None:
        """Assigns a calculation engine instance to the graph.

        Validates that the provided engine object has the expected methods
        (`calculate`, `set_graph`) before assigning it.

        Args:
            engine: The calculation engine instance to associate with this graph.
                    Expected to conform to the CalculationEngine interface.

        Raises:
            TypeError: If the provided `engine` object does not have the required
                       methods (`calculate` and `set_graph`).
        """
        # Raise TypeError if required methods are missing
        if not hasattr(engine, "calculate"):
            raise TypeError("Calculation engine instance must have a 'calculate' method.")
        if not hasattr(engine, "set_graph"):
            raise TypeError("Calculation engine instance must have a 'set_graph' method.")

        self._calculation_engine = engine
        # Assuming set_graph exists now due to the checks above
        self._calculation_engine.set_graph(self)

    def add_node(self, node: "Node") -> None:
        """Adds a node to the graph's node registry, replacing if name exists.

        Also informs the DataManager and CalculationEngine about the new node.

        Args:
            node: The Node object to add.

        Raises:
            TypeError: If the provided object is not a Node instance.
        """
        if not isinstance(node, Node):
            raise TypeError(f"Object {node} is not a valid Node instance.")
        if self.has_node(node.name):
            self.remove_node(node.name)

        self._nodes[node.name] = node

        if hasattr(self._data_manager, "_register_node"):
            self._data_manager._register_node(node)
        if hasattr(self._calculation_engine, "_register_node"):
            self._calculation_engine._register_node(node)

    def _update_calculation_nodes(self) -> None:
        """Refreshes input references for all calculation nodes.

        Iterates through all nodes. If a node is a calculation node
        (has `has_calculation()` and `input_names`), it re-resolves its input
        nodes based on their names from the current graph state and updates
        the node's `inputs` attribute. Clears the node's cache if applicable.
        This is crucial after adding, removing, or replacing nodes to maintain
        graph integrity.

        Logs errors if input nodes cannot be found or if a node lacks the
        expected 'inputs' attribute.
        """
        for nd in self._nodes.values():
            if nd.has_calculation() and hasattr(nd, "input_names") and nd.input_names:
                try:
                    resolved_inputs = []
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

    def get_node(self, name: str) -> Optional["Node"]:
        """Retrieves a node from the graph by its unique name.

        Args:
            name: The string name of the node to retrieve.

        Returns:
            The `Node` object if found, otherwise `None`.

        Example:
            >>> class MockGraph(GraphManipulationMixin):
            ...     def __init__(self): self.nodes = {}
            ...     # Simplified methods needed by mixin
            ...     _nodes: Dict[str, Node] = {}
            ...     _calculation_engine: Optional[Any] = None
            ...     _periods: List[str] = []
            ...     def _update_calculation_nodes(self): pass
            ...     def get_node(self, name: str) -> Optional[Node]: return self.nodes.get(name)
            >>> from fin_statement_model.core.nodes import FinancialStatementItemNode # Assume import
            >>> graph = MockGraph()
            >>> graph.nodes["COGS"] = FinancialStatementItemNode("COGS", {"2023": 50})
            >>> cogs_node = graph.get_node("COGS")
            >>> print(cogs_node.name)
            COGS
            >>> non_existent = graph.get_node("NonExistent")
            >>> print(non_existent)
            None
        """
        return self._nodes.get(name)

    def replace_node(self, node_name: str, new_node: "Node") -> None:
        """Replaces an existing node with a new one, ensuring consistency."""
        if not self.has_node(node_name):
            raise NodeError(f"Node '{node_name}' not found, cannot replace.")
        if node_name != new_node.name:
            raise ValueError("New node name must match the name of the node being replaced.")

        self.remove_node(node_name)
        self.add_node(new_node)

    def has_node(self, node_id: str) -> bool:
        """Checks if a node with the given ID (name) exists in the graph.

        Args:
            node_id: The string ID (name) of the node to check for.

        Returns:
            True if a node with the specified ID exists, False otherwise.

        Example:
            >>> class MockGraph(GraphManipulationMixin):
            ...     def __init__(self): self.nodes = {}
            ...     # Simplified methods needed by mixin
            ...     _nodes: Dict[str, Node] = {}
            ...     _calculation_engine: Optional[Any] = None
            ...     _periods: List[str] = []
            ...     def _update_calculation_nodes(self): pass
            ...     def get_node(self, name: str) -> Optional[Node]: return self.nodes.get(name)
            >>> from fin_statement_model.core.nodes import FinancialStatementItemNode # Assume import
            >>> graph = MockGraph()
            >>> graph.nodes["Assets"] = FinancialStatementItemNode("Assets", {"2023": 1000})
            >>> print(graph.has_node("Assets"))
            True
            >>> print(graph.has_node("Liabilities"))
            False
        """
        return node_id in self._nodes

    def remove_node(self, node_name: str) -> None:
        """Removes a node from the graph and updates dependencies."""
        if not self.has_node(node_name):
            return

        removed_node = self._nodes.pop(node_name, None)

        if hasattr(self._data_manager, "_unregister_node") and removed_node:
            self._data_manager._unregister_node(removed_node)
        if hasattr(self._calculation_engine, "_unregister_node") and removed_node:
            self._calculation_engine._unregister_node(removed_node)

        self._update_calculation_nodes()
        if self._calculation_engine:
            try:
                self._calculation_engine.clear_cache()
            except Exception:
                logger.exception("Error clearing calculation engine cache")

    def clear(self) -> None:
        """Removes all nodes and periods from the graph, resetting its state.

        Clears the internal node registry (`nodes`) and the list of periods
        (`_periods`). If a calculation engine is attached, it attempts to
        reset the engine as well.

        Example:
            >>> class MockGraph(GraphManipulationMixin):
            ...     def __init__(self):
            ...         self.nodes = {"Node1": None, "Node2": None} # Assume Nodes
            ...         self._nodes = self.nodes # Link for mixin
            ...         self._periods = ["2023", "2024"]
            ...         self._calculation_engine = None # Mock engine
            >>> graph = MockGraph()
            >>> print(len(graph.nodes))
            2
            >>> print(len(graph._periods))
            2
            >>> graph.clear()
            >>> print(len(graph.nodes))
            0
            >>> print(len(graph._periods))
            0
        """
        self._nodes = {}
        self._periods = []
        if self._calculation_engine:
            try:
                self._calculation_engine.reset()
            except Exception:
                logger.exception("Error resetting calculation engine")

    def set_value(self, node_id: str, period: str, value: float) -> None:
        """Sets the value for a specific node and period, clearing caches.

        This method is typically used for nodes representing input data
        (like `FinancialStatementItemNode`). It finds the node, verifies the
        period exists, and calls the node's `set_value` method.
        Requires the target node to implement a `set_value` method.
        Clears relevant caches after setting the value.

        Args:
            node_id: The string ID (name) of the node to modify.
            period: The string representation of the time period.
            value: The float value to assign to the node for the given period.

        Raises:
            ValueError: If the specified `period` is not found in the graph's
                        list of periods (`self._periods`).
            NodeError: If no node with the specified `node_id` exists.
            TypeError: If the found node does not have a `set_value` method.

        Example:
            >>> class MockGraph(GraphManipulationMixin):
            ...     def __init__(self):
            ...         self.nodes = {}
            ...         self._nodes = self.nodes
            ...         self._periods = ["2023"]
            ...         self._calculation_engine = None
            ...     def get_node(self, name: str) -> Optional[Node]: return self.nodes.get(name)
            ...     def clear_all_caches(self): pass # No-op
            >>> from fin_statement_model.core.nodes import FinancialStatementItemNode
            >>> from fin_statement_model.core.errors import NodeError
            >>> graph = MockGraph()
            >>> item_node = FinancialStatementItemNode("Sales", {"2023": 500})
            >>> graph.nodes["Sales"] = item_node
            >>> graph.set_value("Sales", "2023", 600)
            >>> print(item_node.get_value("2023"))
            600
            >>> try:
            ...     graph.set_value("Sales", "2024", 700) # Invalid period
            ... except ValueError as e:
            ...     print(e)
            Period '2024' not in graph periods
            >>> try:
            ...     graph.set_value("NonExistent", "2023", 100)
            ... except NodeError as e:
            ...     print(e.message)
            Node 'NonExistent' does not exist
        """
        if period not in self._periods:
            raise ValueError(f"Period '{period}' not in graph periods")
        nd = self.get_node(node_id)
        if not nd:
            raise NodeError(message=f"Node '{node_id}' does not exist", node_id=node_id)
        if not hasattr(nd, "set_value"):
            raise TypeError(
                f"Node '{node_id}' of type {type(nd).__name__} does not support set_value."
            )
        nd.set_value(period, value)
        if self._calculation_engine:
            try:
                self._calculation_engine.clear_cache()
            except Exception:
                logger.exception("Error clearing calculation engine cache")
        else:
            self.clear_all_caches()

    def clear_all_caches(self) -> None:
        """Clears caches associated with individual nodes in the graph.

        Iterates through all nodes in the registry and calls the `clear_cache`
        method on each node if it exists. This primarily affects nodes that
        cache their own computed values (e.g., calculation strategies).

        Note:
            This method clears node-level caches. The main `Graph` class might
            have a similar method that also clears the central `CalculationEngine` cache.

        Example:
            >>> class MockNode:
            ...     def __init__(self):
            ...         self.cache_cleared = False
            ...     def clear_cache(self):
            ...         self.cache_cleared = True
            >>> class MockGraph(GraphManipulationMixin):
            ...     def __init__(self):
            ...         self.node1 = MockNode()
            ...         self.node2 = FinancialStatementItemNode("Item", {}) # No cache
            ...         self.node3 = MockNode()
            ...         self.nodes = {"N1": self.node1, "N2": self.node2, "N3": self.node3}
            ...         self._nodes = self.nodes # Link for mixin
            >>> graph = MockGraph()
            >>> print(graph.node1.cache_cleared, graph.node3.cache_cleared)
            False False
            >>> graph.clear_all_caches()
            >>> print(graph.node1.cache_cleared, graph.node3.cache_cleared)
            True True
        """
        for nd in self._nodes.values():
            if hasattr(nd, "clear_cache"):
                nd.clear_cache()
