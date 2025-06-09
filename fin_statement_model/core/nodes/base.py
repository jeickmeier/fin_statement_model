"""Define the abstract base class for all nodes in the graph.

This module provides the Node base class with interfaces for calculation,
attribute access, and optional caching behavior.
"""

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    pass


class Node(ABC):
    """Define the abstract base class for graph nodes.

    Provide the essential interface for all nodes in the financial statement
    model graph, including calculation, caching, and attribute access.

    Attributes:
    name (str): Unique identifier for the node instance.
    values: dict[str, Any]
    """

    name: str
    values: dict[str, Any]

    def __init__(self, name: str):
        """Initialize the Node instance with a unique name.

        Args:
            name: Unique identifier for the node. Must be a non-empty string.

        Raises:
            ValueError: If `name` is empty or not a string.

        Examples:
            >>> class Dummy(Node):
            ...     def calculate(self, period): return 0.0
            >>> dn = Dummy("Revenue")
            >>> dn.name
            'Revenue'
        """
        # Check if name is a non-empty string
        if not isinstance(name, str) or not name:
            raise ValueError("Node name must be a non-empty string.")
        # Check for invalid characters (including newline, tab)
        if "\n" in name or "\t" in name:
            raise ValueError(
                f"Invalid node name: '{name}'. Contains invalid characters."
            )
        # Check for leading/trailing whitespace
        if name != name.strip():
            raise ValueError(
                f"Invalid node name: '{name}'. Cannot have leading/trailing whitespace."
            )
        self.name = name

    @abstractmethod
    def calculate(self, period: str) -> float:
        """Calculate the node's value for a specific period.

        This abstract method must be implemented by subclasses to define how to
        determine the node's value for a given time period.

        Args:
            period: The time period identifier for the calculation.

        Returns:
            The calculated float value for the specified period.

        Raises:
            NotImplementedError: If the subclass does not implement this method.

        Examples:
            >>> class Dummy(Node):
            ...     def calculate(self, period): return 100.0
            >>> d = Dummy("Test")
            >>> d.calculate("2023")
            100.0
        """

    def clear_cache(self) -> None:
        """Clear cached calculation results for this node.

        Subclasses with caching should override this method to clear their internal cache.

        Returns:
            None

        Examples:
            >>> node.clear_cache()
        """
        # Default: no cache to clear

    def has_attribute(self, attr_name: str) -> bool:
        """Check if the node has a specific attribute.

        Args:
            attr_name: The name of the attribute to check.

        Returns:
            True if the attribute exists, otherwise False.

        Examples:
            >>> node.has_attribute("name")
            True
        """
        return hasattr(self, attr_name)

    def get_attribute(self, attribute_name: str) -> object:
        """Get a named attribute from the node.

        Args:
            attribute_name: The name of the attribute to retrieve.

        Returns:
            The value of the specified attribute.

        Raises:
            AttributeError: If the attribute does not exist.

        Examples:
            >>> node.get_attribute("name")
            'Revenue'
        """
        try:
            return getattr(self, attribute_name)
        except AttributeError:
            raise AttributeError(
                f"Node '{self.name}' has no attribute '{attribute_name}'"
            )

    def set_value(self, period: str, value: float) -> None:
        """Set a value for *period* on data-bearing nodes.

        The base implementation raises NotImplementedError; override in
        subclasses that support mutating stored data.
        """
        raise NotImplementedError(f"Node '{self.name}' does not support set_value")

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Serialize the node to a dictionary representation.

        This method should return a dictionary containing all information
        necessary to reconstruct the node, including:
        - node type
        - name
        - any configuration parameters
        - values (for data nodes)
        - input references (for calculation nodes)

        Returns:
            Dictionary representation of the node.

        Examples:
            >>> node_dict = node.to_dict()
            >>> node_dict['type']
            'financial_statement_item'
        """

    def get_dependencies(self) -> list[str]:
        """Get the names of nodes this node depends on.

        Default implementation returns empty list. Override in nodes that have dependencies.

        Returns:
            List of node names this node depends on.
        """
        return []
