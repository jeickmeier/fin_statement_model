"""
Statement structure components for Financial Statement Model.

This module defines classes that represent the hierarchical structure of
financial statements, including sections, line items, and calculated values.
"""

import logging
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod

from ..core.errors import StatementError

# Configure logging
logger = logging.getLogger(__name__)


class StatementItemType(Enum):
    """Types of statement structure items."""

    SECTION = "section"
    LINE_ITEM = "line_item"
    SUBTOTAL = "subtotal"
    CALCULATED = "calculated"


class StatementItem(ABC):
    """
    Abstract base class for all statement structure items.

    This defines the interface for items in a financial statement structure.
    """

    @property
    @abstractmethod
    def id(self) -> str:
        """Get the item ID."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the item name."""
        pass

    @property
    @abstractmethod
    def item_type(self) -> StatementItemType:
        """Get the item type."""
        pass


class LineItem(StatementItem):
    """
    Represents a basic line item in a financial statement.

    Line items are the fundamental elements of a financial statement,
    representing individual values from the underlying data model.
    """

    def __init__(
        self,
        id: str,
        name: str,
        node_id: str,
        description: str = "",
        sign_convention: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a line item.

        Args:
            id: Unique identifier for the line item
            name: Display name for the line item
            node_id: ID of the node in the graph that provides the value
            description: Optional description of the line item
            sign_convention: Sign convention (1 for normal, -1 for inverted)
            metadata: Optional additional metadata for the line item

        Raises:
            StatementError: If the line item has invalid parameters
        """
        if not id or not isinstance(id, str):
            raise StatementError(message=f"Invalid line item ID: {id}")

        if not name or not isinstance(name, str):
            raise StatementError(
                message=f"Invalid line item name: {name} for line item ID: {id}"
            )

        if node_id is not None and not isinstance(node_id, str):
            raise StatementError(
                message=f"Invalid node ID: {node_id} for line item: {id}"
            )

        if sign_convention not in (1, -1):
            raise StatementError(
                message=f"Invalid sign convention for line item: {sign_convention} for item: {id}"
            )

        self._id = id
        self._name = name
        self._node_id = node_id
        self._description = description
        self._sign_convention = sign_convention
        self._metadata = metadata or {}

    @property
    def id(self) -> str:
        """Get the line item ID."""
        return self._id

    @property
    def name(self) -> str:
        """Get the line item name."""
        return self._name

    @property
    def node_id(self) -> str:
        """Get the node ID for this line item."""
        return self._node_id

    @property
    def description(self) -> str:
        """Get the line item description."""
        return self._description

    @property
    def sign_convention(self) -> int:
        """
        Get the sign convention for this line item.

        Returns:
            int: 1 for normal sign, -1 for inverted sign
        """
        return self._sign_convention

    @property
    def metadata(self) -> Dict[str, Any]:
        """Get the line item metadata."""
        return self._metadata

    @property
    def item_type(self) -> StatementItemType:
        """Get the item type."""
        return StatementItemType.LINE_ITEM


class CalculatedLineItem(LineItem):
    """
    Represents a calculated line item in a financial statement.

    Calculated line items derive their values from a calculation based on
    other line items or nodes.
    """

    def __init__(
        self,
        id: str,
        name: str,
        calculation: Dict[str, Any],
        description: str = "",
        sign_convention: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a calculated line item.

        Args:
            id: Unique identifier for the line item
            name: Display name for the line item
            calculation: Dictionary describing the calculation
                Required keys:
                - type: String specifying calculation type
                - inputs: List of input node IDs
                Optional keys:
                - parameters: Dictionary of additional parameters
            description: Optional description of the line item
            sign_convention: Sign convention (1 for normal, -1 for inverted)
            metadata: Optional additional metadata for the line item

        Raises:
            StatementError: If the calculated line item has invalid parameters
        """
        # Use the item's ID as the node ID for calculated items
        super().__init__(
            id=id,
            name=name,
            node_id=id,  # Calculated items use their own ID as the node_id
            description=description,
            sign_convention=sign_convention,
            metadata=metadata,
        )

        # Validate calculation
        if not isinstance(calculation, dict):
            raise StatementError(
                message=f"Invalid calculation specification for item: {id}"
            )

        if "type" not in calculation:
            raise StatementError(message=f"Missing calculation type for item: {id}")

        if "inputs" not in calculation:
            raise StatementError(message=f"Missing calculation inputs for item: {id}")

        if not isinstance(calculation["inputs"], list):
            raise StatementError(
                message=f"Calculation inputs must be a list for item: {id}"
            )

        self._calculation = calculation

    @property
    def calculation_type(self) -> str:
        """Get the calculation type."""
        return self._calculation["type"]

    @property
    def input_ids(self) -> List[str]:
        """Get the input node IDs for the calculation."""
        return self._calculation["inputs"]

    @property
    def parameters(self) -> Dict[str, Any]:
        """Get additional parameters for the calculation."""
        return self._calculation.get("parameters", {})

    @property
    def item_type(self) -> StatementItemType:
        """Get the item type."""
        return StatementItemType.CALCULATED


class SubtotalLineItem(CalculatedLineItem):
    """
    Represents a subtotal line item in a financial statement.

    Subtotal line items sum the values of multiple line items or sections.
    """

    def __init__(
        self,
        id: str,
        name: str,
        item_ids: List[str],
        description: str = "",
        sign_convention: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a subtotal line item.

        Args:
            id: Unique identifier for the line item
            name: Display name for the line item
            item_ids: List of item IDs to sum
            description: Optional description of the line item
            sign_convention: Sign convention (1 for normal, -1 for inverted)
            metadata: Optional additional metadata for the line item

        Raises:
            StatementError: If the subtotal line item has invalid parameters
        """
        if not isinstance(item_ids, list) or not item_ids:
            raise StatementError(
                message=f"Invalid or empty item IDs for subtotal line item: {id}"
            )

        # Create a calculation spec for addition
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
    def item_ids(self) -> List[str]:
        """Get the item IDs that are summed in this subtotal."""
        return self._item_ids

    @property
    def item_type(self) -> StatementItemType:
        """Get the item type."""
        return StatementItemType.SUBTOTAL


class Section:
    """
    Represents a section in a financial statement.

    Sections group related items together and may include subsections,
    line items, and a subtotal.
    """

    def __init__(
        self,
        id: str,
        name: str,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a section.

        Args:
            id: Unique identifier for the section
            name: Display name for the section
            description: Optional description of the section
            metadata: Optional additional metadata for the section

        Raises:
            StatementError: If the section has invalid parameters
        """
        if not id or not isinstance(id, str):
            raise StatementError(message=f"Invalid section ID: {id}")

        if not name or not isinstance(name, str):
            raise StatementError(
                message=f"Invalid section name: {name} for section ID: {id}"
            )

        self._id = id
        self._name = name
        self._description = description
        self._metadata = metadata or {}
        self._items: List[Union[Section, StatementItem]] = []

    @property
    def id(self) -> str:
        """Get the section ID."""
        return self._id

    @property
    def name(self) -> str:
        """Get the section name."""
        return self._name

    @property
    def description(self) -> str:
        """Get the section description."""
        return self._description

    @property
    def metadata(self) -> Dict[str, Any]:
        """Get the section metadata."""
        return self._metadata

    @property
    def items(self) -> List[Union["Section", StatementItem]]:
        """Get the items in this section."""
        return self._items

    @property
    def item_type(self) -> StatementItemType:
        """Get the item type."""
        return StatementItemType.SECTION

    def add_item(self, item: Union["Section", StatementItem]) -> None:
        """
        Add an item to this section.

        Args:
            item: The item to add

        Raises:
            StatementError: If the item is already in this section
        """
        # Check for duplicate IDs
        if any(existing.id == item.id for existing in self._items):
            raise StatementError(
                message=f"Duplicate item ID: {item.id} in section: {self.id}"
            )

        self._items.append(item)

    def find_item_by_id(
        self, item_id: str
    ) -> Optional[Union["Section", StatementItem]]:
        """
        Find an item by ID in this section and its subsections.

        Args:
            item_id: The ID of the item to find

        Returns:
            Optional[Union[Section, StatementItem]]: The found item, or None if not found
        """
        # Check if this section matches the ID
        if self.id == item_id:
            return self

        # Check direct children
        for item in self._items:
            if item.id == item_id:
                return item

            # Recursively check subsections
            if isinstance(item, Section):
                found = item.find_item_by_id(item_id)
                if found:
                    return found

        return None


class StatementStructure:
    """
    Represents the structure of a financial statement.

    This class maintains the hierarchical structure of a financial statement,
    including sections, line items, and calculations.
    """

    def __init__(
        self,
        id: str,
        name: str,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a statement structure.

        Args:
            id: Unique identifier for the statement
            name: Display name for the statement
            description: Optional description of the statement
            metadata: Optional additional metadata for the statement

        Raises:
            StatementError: If the statement structure has invalid parameters
        """
        if not id or not isinstance(id, str):
            raise StatementError(message=f"Invalid statement ID: {id}")

        if not name or not isinstance(name, str):
            raise StatementError(
                message=f"Invalid statement name: {name} for statement ID: {id}"
            )

        self._id = id
        self._name = name
        self._description = description
        self._metadata = metadata or {}
        self._sections: List[Section] = []

    @property
    def id(self) -> str:
        """Get the statement ID."""
        return self._id

    @property
    def name(self) -> str:
        """Get the statement name."""
        return self._name

    @property
    def description(self) -> str:
        """Get the statement description."""
        return self._description

    @property
    def metadata(self) -> Dict[str, Any]:
        """Get the statement metadata."""
        return self._metadata

    @property
    def sections(self) -> List[Section]:
        """Get the top-level sections in this statement."""
        return self._sections

    @property
    def items(self) -> List[Section]:
        """Get the top-level items (sections) in this statement."""
        return self._sections

    def add_section(self, section: Section) -> None:
        """
        Add a section to this statement.

        Args:
            section: The section to add

        Raises:
            StatementError: If the section ID is already in use
        """
        # Check for duplicate IDs
        if any(existing.id == section.id for existing in self._sections):
            raise StatementError(
                message=f"Duplicate section ID: {section.id} in statement: {self.id}"
            )

        if self.find_item_by_id(section.id) is not None:
            raise StatementError(
                message=f"Duplicate item ID: {section.id} in statement: {self.id}"
            )  # pragma: no cover

        self._sections.append(section)

    def find_item_by_id(self, item_id: str) -> Optional[Union[Section, StatementItem]]:
        """
        Find an item by ID in this statement.

        Args:
            item_id: The ID of the item to find

        Returns:
            Optional[Union[Section, StatementItem]]: The found item, or None if not found
        """
        # Check sections
        for section in self._sections:
            if section.id == item_id:
                return section

            # Check items in this section
            found = section.find_item_by_id(item_id)
            if found:
                return found

        return None

    def find_item(self, item_id: str) -> Optional[Union[Section, StatementItem]]:
        """
        Find an item by ID in this statement. Alias for find_item_by_id.

        Args:
            item_id: The ID of the item to find

        Returns:
            Optional[Union[Section, StatementItem]]: The found item, or None if not found
        """
        return self.find_item_by_id(item_id)

    def get_all_items(self) -> List[Union[Section, StatementItem]]:
        """
        Get all items in this statement.

        Returns:
            List[Union[Section, StatementItem]]: List of all items
        """
        items = []

        # Helper to recursively collect items
        def collect_items(container: Union[StatementStructure, Section]) -> None:
            for item in container.items:
                items.append(item)
                if isinstance(item, Section):
                    collect_items(item)

        # Collect items from all sections
        collect_items(self)

        return items

    def get_items_by_type(
        self, item_type: StatementItemType
    ) -> List[Union[Section, StatementItem]]:
        """
        Get all items of a specific type.

        Args:
            item_type: The type of items to get

        Returns:
            List[Union[Section, StatementItem]]: List of items of the specified type
        """
        return [item for item in self.get_all_items() if item.item_type == item_type]

    def get_calculation_items(
        self,
    ) -> List[Union[CalculatedLineItem, SubtotalLineItem]]:
        """
        Get all calculated items in this statement.

        Returns:
            List[Union[CalculatedLineItem, SubtotalLineItem]]: List of calculated items
        """
        return [
            item
            for item in self.get_all_items()
            if isinstance(item, CalculatedLineItem)
        ]
