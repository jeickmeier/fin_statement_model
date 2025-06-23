"""Define a node representing a basic financial statement item.

This module provides the FinancialStatementItemNode class, which stores raw financial statement values
for specific periods. It is typically used as a leaf node in the financial statement model graph.

Features:
    - Stores period-to-value mappings for reported financial data (e.g., revenue, COGS).
    - Supports value retrieval and mutation for specific periods.
    - Implements serialization to and from dictionary representations via `to_dict` and `from_dict`.

Example:
    >>> from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode
    >>> data = {"2022": 1000.0, "2023": 1200.0}
    >>> node = FinancialStatementItemNode("revenue", data)
    >>> node.calculate("2023")
    1200.0
    >>> node.set_value("2024", 1500.0)
    >>> node.calculate("2024")
    1500.0
    >>> d = node.to_dict()
    >>> d["type"]
    'financial_statement_item'
    >>> # Round-trip serialization
    >>> node2 = FinancialStatementItemNode.from_dict(d)
    >>> node2.calculate("2023")
    1200.0
"""

import logging
from typing import Any

from fin_statement_model.core.node_factory.registries import node_type

# Use absolute imports
from fin_statement_model.core.nodes.base import Node

logger = logging.getLogger(__name__)


@node_type("financial_statement_item")
class FinancialStatementItemNode(Node):
    """Store raw financial statement values for specific periods.

    Represents a leaf node containing actual reported financial data
    (e.g., revenue, COGS) across time periods.

    Serialization contract:
        - `to_dict(self) -> dict`: Serialize the node to a dictionary.
        - `from_dict(cls, data: dict, context: dict[str, Node] | None = None) -> FinancialStatementItemNode`:
            Classmethod to deserialize a node from a dictionary. `context` is ignored for data nodes.

    Attributes:
        name (str): Unique identifier for the financial item.
        values (dict[str, float]): Mapping from period identifiers to their values.

    Example:
        >>> from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode
        >>> data = {"2022": 1000.0, "2023": 1200.0}
        >>> node = FinancialStatementItemNode("revenue", data)
        >>> d = node.to_dict()
        >>> node2 = FinancialStatementItemNode.from_dict(d)
        >>> node2.calculate("2023")
        1200.0
    """

    values: dict[str, float]

    def __init__(self, name: str, values: dict[str, float]):
        """Create a FinancialStatementItemNode.

        Args:
            name (str): Unique identifier for the financial item.
            values (dict[str, float]): Initial mapping of periods to values.

        Raises:
            ValueError: If `name` is empty, contains invalid characters, or has leading/trailing whitespace.

        Example:
            >>> FinancialStatementItemNode("Revenue", {"2023": 1000.0})
            FinancialStatementItemNode object
        """
        super().__init__(name)
        self.values = values

    def calculate(self, period: str) -> float:
        """Get the value for a specific period.

        Args:
            period (str): Period identifier to retrieve.

        Returns:
            float: Stored value for `period`, or 0.0 if not present.

        Example:
            >>> node = FinancialStatementItemNode("Revenue", {"2023": 1000.0})
            >>> node.calculate("2023")
            1000.0
            >>> node.calculate("2022")
            0.0
        """
        return self.values.get(period, 0.0)

    def set_value(self, period: str, value: float) -> None:
        """Set the value for a specific period.

        Args:
            period (str): Period identifier.
            value (float): Numerical value to store.

        Example:
            >>> node = FinancialStatementItemNode("Revenue", {"2023": 1000.0})
            >>> node.set_value("2024", 1500.0)
            >>> node.calculate("2024")
            1500.0
        """
        self.values[period] = value

    def to_dict(self) -> dict[str, Any]:
        """Serialize this node to a dictionary.

        Returns:
            dict[str, Any]: Dictionary with keys 'type', 'name', and 'values'.

        Example:
            >>> node = FinancialStatementItemNode("Revenue", {"2023": 1000.0})
            >>> data = node.to_dict()
            >>> data["type"]
            'financial_statement_item'
        """
        return {
            "type": "financial_statement_item",
            "name": self.name,
            "values": self.values.copy(),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        context: dict[str, "Node"] | None = None,
    ) -> "FinancialStatementItemNode":
        """Deserialize a FinancialStatementItemNode from a dictionary.

        Args:
            data (dict[str, Any]): Serialized node data; must contain keys 'type', 'name', and 'values'.
            context (dict[str, Node] | None): Optional context for deserialization (ignored).

        Returns:
            FinancialStatementItemNode: Reconstructed node.

        Raises:
            ValueError: If 'type' is not 'financial_statement_item' or 'name' is missing.
            TypeError: If 'values' is not a dict.

        Example:
            >>> d = {"type": "financial_statement_item", "name": "Revenue", "values": {"2023": 1000.0}}
            >>> node = FinancialStatementItemNode.from_dict(d)
            >>> node.name
            'Revenue'
            >>> node.calculate("2023")
            1000.0
        """
        if data.get("type") != "financial_statement_item":
            raise ValueError(f"Invalid type for FinancialStatementItemNode: {data.get('type')}")

        name = data.get("name")
        if not name:
            raise ValueError("Missing 'name' field in FinancialStatementItemNode data")

        values = data.get("values", {})
        if not isinstance(values, dict):
            raise TypeError("'values' field must be a dict[str, float]")

        # Context is intentionally ignored for simple data nodes but referenced to avoid
        # unused-argument linter violations and to aid future debugging.
        if context is not None:
            logger.debug(
                "FinancialStatementItemNode.from_dict received a non-null 'context' argument, which is currently ignored. Node: %s",
                name,
            )

        return cls(name, values)
