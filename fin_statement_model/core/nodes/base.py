"""Define the abstract base class for all nodes in the graph.

This module provides the Node base class with interfaces for calculation,
attribute access, and optional caching behavior. All node types must implement
Google-style serialization and deserialization via `to_dict` and `from_dict`.

Features:
    - Abstract base class for all node types in the financial statement model graph.
    - Enforces implementation of calculation and serialization methods.
    - Provides attribute access, dependency inspection, and optional cache clearing.
    - Serialization contract: all nodes must implement `to_dict` and `from_dict`.

Example:
    >>> from fin_statement_model.core.nodes.base import Node
    >>> class DummyNode(Node):
    ...     def calculate(self, period): return 42.0
    ...     def to_dict(self): return {'type': 'dummy', 'name': self.name}
    >>> node = DummyNode('test')
    >>> node.calculate('2023')
    42.0
    >>> d = node.to_dict()
    >>> d['type']
    'dummy'
    >>> # Round-trip serialization (subclasses must implement from_dict)
    >>> DummyNode.from_dict({'type': 'dummy', 'name': 'test'})  # doctest: +SKIP
"""

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    pass


class Node(ABC):
    """Abstract base class for all nodes in the financial statement model.

    This class defines the required interface for all node types, including calculation,
    serialization, and dependency inspection. Subclasses must implement `calculate`, `to_dict`,
    and (for deserializable nodes) `from_dict` as a classmethod.

    Serialization contract:
        - `to_dict(self) -> dict`: Serialize the node to a dictionary.
        - `from_dict(cls, data: dict, context: dict[str, Node] | None = None) -> Node`:
            Classmethod to deserialize a node from a dictionary. Nodes with dependencies
            (e.g., calculation, forecast, stat nodes) must use the `context` argument to resolve them.
            Data nodes may ignore `context`.

    Attributes:
        name (str): Unique identifier for the node instance.
        values (dict[str, Any]): Optional mapping of period to value (for data nodes).

    Example:
        >>> class DummyNode(Node):
        ...     def calculate(self, period): return 1.0
        ...     def to_dict(self): return {'type': 'dummy', 'name': self.name}
        ...     @classmethod
        ...     def from_dict(cls, data, context=None): return cls(data['name'])
        >>> node = DummyNode('Revenue')
        >>> d = node.to_dict()
        >>> DummyNode.from_dict(d).name
        'Revenue'
    """

    name: str
    values: dict[str, Any]

    def __init__(self, name: str):
        """Initialize the Node instance with a unique name.

        Args:
            name (str): Unique identifier for the node. Must be a non-empty string.

        Raises:
            ValueError: If `name` is empty, not a string, or contains invalid characters.

        Example:
            >>> Node('Revenue')  # doctest: +ELLIPSIS
            Traceback (most recent call last):
            ...
            TypeError: Can't instantiate abstract class Node...
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
        """Calculate the node's value for a given period.

        Subclasses must override this method to implement specific calculation logic.

        Args:
            period (str): Identifier for the time period.

        Returns:
            float: Calculated value for the period.

        Example:
            >>> class Dummy(Node):
            ...     def calculate(self, period): return 2.0
            ...     def to_dict(self): return {'type': 'dummy', 'name': self.name}
            >>> Dummy('Test').calculate('2023')
            2.0
        """

    def clear_cache(self) -> None:
        """Clear cached calculation results for this node.

        Subclasses with caching should override this method to clear their internal cache.

        Returns:
            None

        Example:
            >>> class Dummy(Node):
            ...     def calculate(self, period): return 1.0
            ...     def to_dict(self): return {'type': 'dummy', 'name': self.name}
            ...     def clear_cache(self): print('Cache cleared!')
            >>> node = Dummy('Test')
            >>> node.clear_cache()
            Cache cleared!
        """
        # Default: no cache to clear

    def has_attribute(self, attr_name: str) -> bool:
        """Check if the node has a specific attribute.

        Args:
            attr_name (str): The name of the attribute to check.

        Returns:
            bool: True if the attribute exists, otherwise False.

        Example:
            >>> class Dummy(Node):
            ...     def calculate(self, period): return 1.0
            ...     def to_dict(self): return {'type': 'dummy', 'name': self.name}
            >>> node = Dummy('Test')
            >>> node.has_attribute('name')
            True
        """
        return hasattr(self, attr_name)

    def get_attribute(self, attribute_name: str) -> object:
        """Get a named attribute from the node.

        Args:
            attribute_name (str): The name of the attribute to retrieve.

        Returns:
            object: The value of the specified attribute.

        Raises:
            AttributeError: If the attribute does not exist.

        Example:
            >>> class Dummy(Node):
            ...     def calculate(self, period): return 1.0
            ...     def to_dict(self): return {'type': 'dummy', 'name': self.name}
            >>> node = Dummy('Test')
            >>> node.get_attribute('name')
            'Test'
        """
        try:
            return getattr(self, attribute_name)
        except AttributeError:
            raise AttributeError(
                f"Node '{self.name}' has no attribute '{attribute_name}'"
            )

    def set_value(self, period: str, value: float) -> None:
        """Set a value for a specific period on data-bearing nodes.

        Override in subclasses to support mutating stored data.

        Args:
            period (str): Period identifier.
            value (float): Numerical value to store.

        Raises:
            NotImplementedError: Always in base class.

        Example:
            >>> class Dummy(Node):
            ...     def calculate(self, period): return 1.0
            ...     def to_dict(self): return {'type': 'dummy', 'name': self.name}
            ...     def set_value(self, period, value): print(f"Set {period} to {value}")
            >>> node = Dummy('Test')
            >>> node.set_value('2023', 100)
            Set 2023 to 100
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
            dict[str, Any]: Dictionary representation of the node.

        Example:
            >>> class Dummy(Node):
            ...     def calculate(self, period): return 1.0
            ...     def to_dict(self): return {'type': 'dummy', 'name': self.name}
            >>> node = Dummy('Test')
            >>> node.to_dict()['type']
            'dummy'
        """

    def get_dependencies(self) -> list[str]:
        """Get the names of nodes this node depends on.

        Default implementation returns empty list. Override in nodes that have dependencies.

        Returns:
            list[str]: List of node names this node depends on.

        Example:
            >>> class Dummy(Node):
            ...     def calculate(self, period): return 1.0
            ...     def to_dict(self): return {'type': 'dummy', 'name': self.name}
            ...     def get_dependencies(self): return ['dep1', 'dep2']
            >>> node = Dummy('Test')
            >>> node.get_dependencies()
            ['dep1', 'dep2']
        """
        return []

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        context: dict[str, "Node"] | None = None,
    ) -> "Node":
        """Deserialize a node from its dictionary representation.

        Subclasses that support deserialization must override this method.
        Nodes with dependencies (e.g., calculation, forecast, stat nodes) must use the
        `context` argument to resolve them. Data nodes may ignore `context`.

        Args:
            data: The serialized node dictionary (usually produced by :py:meth:`to_dict`).
            context: Optional mapping of node names to node objects that have already been deserialized.

        Returns:
            Node: A fully instantiated node object.

        Raises:
            NotImplementedError: If not overridden in a subclass.

        Example:
            >>> class DummyNode(Node):
            ...     def calculate(self, period): return 1.0
            ...     def to_dict(self): return {'type': 'dummy', 'name': self.name}
            ...     @classmethod
            ...     def from_dict(cls, data, context=None): return cls(data['name'])
            >>> node = DummyNode('Revenue')
            >>> d = node.to_dict()
            >>> DummyNode.from_dict(d).name
            'Revenue'
        """
        raise NotImplementedError(
            f"{cls.__name__}.from_dict() is not implemented. Subclasses requiring deserialization must override this method."
        )
