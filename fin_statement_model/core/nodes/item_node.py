"""Define a node representing a basic financial statement item."""

import logging
from typing import Any

# Use absolute imports
from fin_statement_model.core.nodes.base import Node

logger = logging.getLogger(__name__)


class FinancialStatementItemNode(Node):
    """Store raw financial statement values for specific periods.

    Represents a leaf node containing actual reported financial data
    (e.g., revenue, COGS) across time periods.

    Attributes:
        name (str): Unique identifier for the financial item.
        values (dict[str, float]): Mapping from period identifiers to their values.

    Examples:
        >>> from fin_statement_model.core.nodes import FinancialStatementItemNode
        >>> data = {"2022": 1000.0, "2023": 1200.0}
        >>> node = FinancialStatementItemNode("revenue", data)
        >>> node.calculate("2023")
        1200.0
        >>> node.set_value("2024", 1500.0)
        >>> node.calculate("2024")
        1500.0
    """

    values: dict[str, float]

    def __init__(self, name: str, values: dict[str, float]):
        """Create a FinancialStatementItemNode.

        Args:
            name (str): Unique identifier for the financial item.
            values (dict[str, float]): Initial mapping of periods to values.

        Raises:
            ValueError: If `name` is empty, contains invalid characters, or has leading/trailing whitespace.
        """
        super().__init__(name)
        self.values = values

    def calculate(self, period: str) -> float:
        """Get the value for a specific period.

        Args:
            period (str): Period identifier to retrieve.

        Returns:
            float: Stored value for `period`, or 0.0 if not present.
        """
        return self.values.get(period, 0.0)

    def set_value(self, period: str, value: float) -> None:
        """Set the value for a specific period.

        Args:
            period (str): Period identifier.
            value (float): Numerical value to store.
        """
        self.values[period] = value

    def to_dict(self) -> dict[str, Any]:
        """Serialize this node to a dictionary.

        Returns:
            dict[str, Any]: Dictionary with keys 'type', 'name', and 'values'.

        Examples:
            >>> from fin_statement_model.core.nodes import FinancialStatementItemNode
            >>> node = FinancialStatementItemNode("Revenue", {"2023": 1000.0})
            >>> data = node.to_dict()
            >>> data['type']
            'financial_statement_item'
        """
        return {
            "type": "financial_statement_item",
            "name": self.name,
            "values": self.values.copy(),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "FinancialStatementItemNode":
        """Create a FinancialStatementItemNode from serialized data.

        Args:
            data (dict[str, Any]): Serialized node data; must contain keys 'type', 'name', and 'values'.

        Returns:
            FinancialStatementItemNode: Reconstructed node.

        Raises:
            ValueError: If 'type' is not 'financial_statement_item' or 'name' is missing.
            TypeError: If 'values' is not a dict.
        """
        if data.get("type") != "financial_statement_item":
            raise ValueError(
                f"Invalid type for FinancialStatementItemNode: {data.get('type')}"
            )

        name = data.get("name")
        if not name:
            raise ValueError("Missing 'name' field in FinancialStatementItemNode data")

        values = data.get("values", {})
        if not isinstance(values, dict):
            raise TypeError("'values' field must be a dict[str, float]")

        return FinancialStatementItemNode(name, values)
