"""Defines the abstract base class for all nodes in the graph."""

from abc import ABC, abstractmethod


class Node(ABC):
    """Abstract base class for graph nodes.

    Defines the essential interface for all nodes within the financial
    statement model graph, including calculation logic and attribute access.

    Attributes:
        name (str): The unique identifier for the node.
    """

    name: str

    def __init__(self, name: str):
        """Initialize the node with a unique name.

        Args:
            name (str): The unique identifier for the node. Must be non-empty.

        Raises:
            ValueError: If the provided name is empty or not a string.
        """
        if not isinstance(name, str) or not name:
            raise ValueError("Node name must be a non-empty string.")
        self.name = name

    @abstractmethod
    def calculate(self, period: str) -> float:
        """Calculate the node's value for a specific period.

        This method must be implemented by subclasses to define how the
        node's value is determined for a given time period.

        Args:
            period (str): The time period for which to calculate the value.

        Returns:
            float: The calculated value for the specified period.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """

    def clear_cache(self):
        """Clear any cached calculation results for this node.

        Subclasses that implement caching should override this method
        to clear their internal cache. The default implementation does nothing.
        """
        # Default: no cache to clear

    def has_attribute(self, attr_name: str) -> bool:
        """Check if the node instance possesses a specific attribute.

        Args:
            attr_name (str): The name of the attribute to check for.

        Returns:
            bool: True if the attribute exists, False otherwise.
        """
        return hasattr(self, attr_name)

    def get_attribute(self, attribute_name: str) -> object:
        """Get an attribute from the node.

        Raises:
            AttributeError: If the attribute does not exist.
        """
        try:
            return getattr(self, attribute_name)
        except AttributeError:
            raise AttributeError(f"Node '{self.name}' has no attribute '{attribute_name}'")

    def has_value(self, period: str) -> bool:
        """Indicate if the node stores a direct value for the period.

        Primarily intended for nodes that store raw data rather than calculate.
        Calculation nodes typically override `has_calculation`.

        Args:
            period (str): The time period to check for a stored value.

        Returns:
            bool: False by default. Subclasses storing data should override.
        """
        return False

    def get_value(self, period: str) -> float:
        """Retrieve the node's directly stored value for a period.

        This method is intended for nodes that hold raw data. Subclasses
        that store data should implement this.

        Args:
            period (str): The time period for which to retrieve the value.

        Returns:
            float: The stored value for the period.

        Raises:
            NotImplementedError: If the node type does not store direct values.
        """
        raise NotImplementedError(f"Node {self.name} does not implement get_value")

    def has_calculation(self) -> bool:
        """Indicate if this node performs a calculation.

        Distinguishes calculation nodes from data-holding nodes.

        Returns:
            bool: False by default. Calculation nodes should override to True.
        """
        return False
