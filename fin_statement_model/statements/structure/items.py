"""Statement structure items module defining line items, calculated items, and subtotals."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional

from fin_statement_model.core.errors import StatementError

__all__ = [
    "CalculatedLineItem",
    "LineItem",
    "StatementItem",
    "StatementItemType",
    "SubtotalLineItem",
]


class StatementItemType(Enum):
    """Types of statement structure items.

    Attributes:
      SECTION: Section container
      LINE_ITEM: Basic financial line item
      SUBTOTAL: Subtotal of multiple items
      CALCULATED: Derived calculation item
    """

    SECTION = "section"
    LINE_ITEM = "line_item"
    SUBTOTAL = "subtotal"
    CALCULATED = "calculated"


class StatementItem(ABC):
    """Abstract base class for all statement structure items.

    Defines a common interface: id, name, and item_type.
    """

    @property
    @abstractmethod
    def id(self) -> str:
        """Get the unique identifier of the item."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the display name of the item."""

    @property
    @abstractmethod
    def item_type(self) -> StatementItemType:
        """Get the type of this statement item."""


class LineItem(StatementItem):
    """Represents a basic line item in a financial statement.

    Args:
      id: Unique ID for the line item
      name: Display name for the line item
      node_id: ID of the core graph node that holds values
      description: Optional explanatory text
      sign_convention: 1 for normal values, -1 for inverted
      metadata: Optional additional attributes

    Raises:
      StatementError: If inputs are invalid
    """

    def __init__(
        self,
        id: str,
        name: str,
        node_id: str,
        description: str = "",
        sign_convention: int = 1,
        metadata: Optional[dict[str, Any]] = None,
    ):
        """Initialize a basic LineItem.

        Args:
            id: Unique ID for the line item.
            name: Display name for the line item.
            node_id: ID of the core graph node holding values.
            description: Optional explanatory text.
            sign_convention: Sign convention (1 for positive, -1 for negative).
            metadata: Optional additional attributes.

        Raises:
            StatementError: If inputs are invalid.
        """
        if not id or not isinstance(id, str):
            raise StatementError(message=f"Invalid line item ID: {id}")
        if not name or not isinstance(name, str):
            raise StatementError(message=f"Invalid line item name: {name} for ID: {id}")
        if not node_id or not isinstance(node_id, str):
            raise StatementError(message=f"Invalid node ID for line item: {id}")
        if sign_convention not in (1, -1):
            raise StatementError(
                message=f"Invalid sign convention {sign_convention} for item: {id}"
            )
        self._id = id
        self._name = name
        self._node_id = node_id
        self._description = description
        self._sign_convention = sign_convention
        self._metadata = metadata or {}

    @property
    def id(self) -> str:
        """Get the unique identifier of the line item."""
        return self._id

    @property
    def name(self) -> str:
        """Get the display name of the line item."""
        return self._name

    @property
    def node_id(self) -> str:
        """Get the core graph node ID for this line item."""
        return self._node_id

    @property
    def description(self) -> str:
        """Get the description for this line item."""
        return self._description

    @property
    def sign_convention(self) -> int:
        """Get the sign convention (1 or -1)."""
        return self._sign_convention

    @property
    def metadata(self) -> dict[str, Any]:
        """Get custom metadata associated with this item."""
        return self._metadata

    @property
    def item_type(self) -> StatementItemType:
        """Get the type of this item (LINE_ITEM)."""
        return StatementItemType.LINE_ITEM


class CalculatedLineItem(LineItem):
    """Represents a calculated line item whose values come from graph calculations.

    Args:
      id: Unique ID (also used as node_id)
      name: Display name
      calculation: Dict with 'type', 'inputs', optional 'parameters'
      description: Optional description
      sign_convention: 1 or -1
      metadata: Optional metadata

    Raises:
      StatementError: If calculation dictionary is invalid
    """

    def __init__(
        self,
        id: str,
        name: str,
        calculation: dict[str, Any],
        description: str = "",
        sign_convention: int = 1,
        metadata: Optional[dict[str, Any]] = None,
    ):
        """Initialize a CalculatedLineItem based on calculation specification.

        Args:
            id: Unique ID (also used as node_id).
            name: Display name.
            calculation: Calculation spec dict with 'type', 'inputs', optional 'parameters'.
            description: Optional description.
            sign_convention: Sign convention (1 or -1).
            metadata: Optional metadata.

        Raises:
            StatementError: If calculation dictionary is invalid.
        """
        super().__init__(
            id=id,
            name=name,
            node_id=id,
            description=description,
            sign_convention=sign_convention,
            metadata=metadata,
        )
        if not isinstance(calculation, dict):
            raise StatementError(message=f"Invalid calculation spec for item: {id}")
        if "type" not in calculation:
            raise StatementError(message=f"Missing calculation type for item: {id}")
        inputs = calculation.get("inputs")
        if not isinstance(inputs, list) or not inputs:
            raise StatementError(
                message=f"Calculation inputs must be a non-empty list for item: {id}"
            )
        self._calculation = calculation

    @property
    def calculation_type(self) -> str:
        """Get the calculation operation type (e.g., 'addition')."""
        return self._calculation["type"]

    @property
    def input_ids(self) -> list[str]:
        """Get the list of input item IDs for this calculation."""
        return self._calculation["inputs"]

    @property
    def parameters(self) -> dict[str, Any]:
        """Get optional parameters for the calculation."""
        return self._calculation.get("parameters", {})

    @property
    def item_type(self) -> StatementItemType:
        """Get the type of this item (CALCULATED)."""
        return StatementItemType.CALCULATED


class SubtotalLineItem(CalculatedLineItem):
    """Represents a subtotal line item summing multiple other items.

    Args:
      id: Unique ID (also used as node_id)
      name: Display name
      item_ids: List of IDs to sum
      description: Optional description
      sign_convention: 1 or -1
      metadata: Optional metadata

    Raises:
      StatementError: If item_ids is empty or not a list
    """

    def __init__(
        self,
        id: str,
        name: str,
        item_ids: list[str],
        description: str = "",
        sign_convention: int = 1,
        metadata: Optional[dict[str, Any]] = None,
    ):
        """Initialize a SubtotalLineItem summing multiple items.

        Args:
            id: Unique ID (also used as node_id).
            name: Display name.
            item_ids: List of IDs to sum.
            description: Optional description.
            sign_convention: Sign convention (1 or -1).
            metadata: Optional metadata.

        Raises:
            StatementError: If item_ids is empty or not a list.
        """
        if not isinstance(item_ids, list) or not item_ids:
            raise StatementError(message=f"Invalid or empty item IDs for subtotal: {id}")
        calculation = {"type": "addition", "inputs": item_ids, "parameters": {}}
        super().__init__(
            id=id,
            name=name,
            calculation=calculation,
            description=description,
            sign_convention=sign_convention,
            metadata=metadata,
        )
        self._item_ids = item_ids

    @property
    def item_ids(self) -> list[str]:
        """Get the IDs of items summed by this subtotal."""
        return self._item_ids

    @property
    def item_type(self) -> StatementItemType:
        """Get the type of this item (SUBTOTAL)."""
        return StatementItemType.SUBTOTAL
