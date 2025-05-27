"""Define the abstract base class for all nodes in the graph.

This module provides the Node base class with interfaces for calculation,
attribute access, and optional caching behavior.
"""

from abc import ABC, abstractmethod


class Node(ABC):
    """Define the abstract base class for graph nodes.

    Provide the essential interface for all nodes in the financial statement
    model graph, including calculation, caching, and attribute access.

    Attributes:
    name (str): Unique identifier for the node instance.
    """

    name: str

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
            raise ValueError(f"Invalid node name: '{name}'. Contains invalid characters.")
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

    def clear_cache(self):
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
            raise AttributeError(f"Node '{self.name}' has no attribute '{attribute_name}'")

    def has_value(self, period: str) -> bool:
        """Indicate whether the node stores a direct value for a period.

        Primarily for data-bearing nodes; calculation nodes override has_calculation.

        Args:
            period: The time period to check for a stored value.

        Returns:
            True if a direct value is stored, otherwise False.

        Examples:
            >>> node.has_value("2023")
            False
        """
        return False

    def get_value(self, period: str) -> float:
        """Retrieve the node's directly stored value for a period.

        This method must be overridden by data-bearing nodes to return stored values.

        Args:
            period: The time period string for which to retrieve the value.

        Returns:
            The float value stored for the given period.

        Raises:
            NotImplementedError: If the node does not store direct values.

        Examples:
            >>> node.get_value("2023")
        """
        raise NotImplementedError(f"Node {self.name} does not implement get_value")

    def has_calculation(self) -> bool:
        """Indicate whether this node performs calculation.

        Distinguish calculation nodes from data-holding nodes.

        Returns:
            True if the node performs calculations, otherwise False.

        Examples:
            >>> node.has_calculation()
            False
        """
        return False
