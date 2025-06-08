"""Define a node representing a basic financial statement item."""

import logging
from typing import Any

# Use absolute imports
from fin_statement_model.core.nodes.base import Node

logger = logging.getLogger(__name__)


class FinancialStatementItemNode(Node):
    """Define a leaf node containing raw financial statement data.

    This node type typically stores actual reported values (e.g., Revenue,
    COGS) for different time periods.

    Attributes:
        name (str): The unique identifier for the financial item (e.g., "Revenue").
        values (Dict[str, float]): A dictionary mapping time periods (str)
            to their corresponding numerical values (float).

    Examples:
        >>> revenue_data = {"2022": 1000.0, "2023": 1200.0}
        >>> revenue_node = FinancialStatementItemNode("Revenue", revenue_data)
        >>> print(revenue_node.name)
        Revenue
        >>> print(revenue_node.get_value("2023"))
        1200.0
        >>> print(revenue_node.calculate("2022")) # Calculate retrieves the value
        1000.0
        >>> revenue_node.set_value("2024", 1500.0)
        >>> print(revenue_node.get_value("2024"))
        1500.0
        >>> print(revenue_node.has_value("2021"))
        False
    """

    values: dict[str, float]

    def __init__(self, name: str, values: dict[str, float]):
        """Initialize the financial statement item node.

        Args:
            name (str): The name of the financial statement item.
            values (Dict[str, float]): Dictionary of period-value pairs.
        """
        super().__init__(name)
        self.values = values

    def calculate(self, period: str) -> float:
        """Retrieve the value for the specified period.

        For this node type, calculation simply means retrieving the stored value.

        Args:
            period (str): The time period for which to retrieve the value.

        Returns:
            float: The value for the given period, or 0.0 if the period is not found.
        """
        return self.get_value(period)

    def set_value(self, period: str, value: float) -> None:
        """Update or add a value for a specific period.

        Modifies the stored data for the given period.

        Args:
            period (str): The time period to set the value for.
            value (float): The numerical value to store for the period.
        """
        self.values[period] = value

    def has_value(self, period: str) -> bool:
        """Check if a value exists for the specified period.

        Args:
            period (str): The time period to check.

        Returns:
            bool: True if a value is stored for the period, False otherwise.
        """
        return period in self.values

    def get_value(self, period: str) -> float:
        """Retrieve the stored value for a specific period.

        Args:
            period (str): The time period for which to get the value.

        Returns:
            float: The stored value, defaulting to 0.0 if the period is not found.
        """
        return self.values.get(period, 0.0)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the node to a dictionary representation.

        Returns:
            Dictionary containing the node's type, name, and values.

        Examples:
            >>> node = FinancialStatementItemNode("Revenue", {"2023": 1000.0})
            >>> data = node.to_dict()
            >>> data['type']
            'financial_statement_item'
            >>> data['name']
            'Revenue'
        """
        return {
            "type": "financial_statement_item",
            "name": self.name,
            "values": self.values.copy(),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "FinancialStatementItemNode":
        """Create a FinancialStatementItemNode from a dictionary representation.

        Args:
            data: Dictionary containing the node's serialized data.
                Must include 'type', 'name', and 'values' fields.

        Returns:
            A new FinancialStatementItemNode instance.

        Raises:
            ValueError: If the data is invalid or missing required fields.

        Examples:
            >>> data = {
            ...     'type': 'financial_statement_item',
            ...     'name': 'Revenue',
            ...     'values': {'2023': 1000.0}
            ... }
            >>> node = FinancialStatementItemNode.from_dict(data)
            >>> node.name
            'Revenue'
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
            raise TypeError("'values' field must be a dictionary")

        return FinancialStatementItemNode(name, values)
