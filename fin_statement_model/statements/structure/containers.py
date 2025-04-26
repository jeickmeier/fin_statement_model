"""Container classes for defining hierarchical financial statement structures.

This module provides Section and StatementStructure, which organize
LineItem and CalculatedLineItem objects into nested groups.
"""

from typing import Any, Optional, Union, List

from fin_statement_model.core.errors import StatementError
from fin_statement_model.statements.structure.items import (
    StatementItem,
    StatementItemType,
    CalculatedLineItem,
    SubtotalLineItem,
)


__all__ = ["Section", "StatementStructure"]


class Section:
    """Represents a section in a financial statement.

    Sections group related items and subsections into a hierarchical container.
    """

    def __init__(
        self,
        id: str,
        name: str,
        description: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ):
        """Initialize a section.

        Args:
            id: Unique identifier for the section.
            name: Display name for the section.
            description: Optional description text.
            metadata: Optional additional metadata.

        Raises:
            StatementError: If id or name is invalid.
        """
        if not id or not isinstance(id, str):
            raise StatementError(message=f"Invalid section ID: {id}")
        if not name or not isinstance(name, str):
            raise StatementError(message=f"Invalid section name: {name} for ID: {id}")

        self._id = id
        self._name = name
        self._description = description
        self._metadata = metadata or {}
        self._items: list[Union[Section, StatementItem]] = []

    @property
    def id(self) -> str:
        """Get the section identifier."""
        return self._id

    @property
    def name(self) -> str:
        """Get the section display name."""
        return self._name

    @property
    def description(self) -> str:
        """Get the section description."""
        return self._description

    @property
    def metadata(self) -> dict[str, Any]:
        """Get the section metadata."""
        return self._metadata

    @property
    def items(self) -> list[Union["Section", StatementItem]]:
        """Get the child items and subsections."""
        return list(self._items)

    @property
    def item_type(self) -> StatementItemType:
        """Get the item type (SECTION)."""
        return StatementItemType.SECTION

    def add_item(self, item: Union["Section", StatementItem]) -> None:
        """Add a child item or subsection to this section.

        Args:
            item: The Section or StatementItem to add.

        Raises:
            StatementError: If an item with the same id already exists.
        """
        if any(existing.id == item.id for existing in self._items):
            raise StatementError(message=f"Duplicate item ID: {item.id} in section: {self.id}")
        self._items.append(item)

    def find_item_by_id(self, item_id: str) -> Optional[Union["Section", StatementItem]]:
        """Recursively find an item by its identifier within this section.

        Args:
            item_id: Identifier of the item to search for.

        Returns:
            The found Section or StatementItem, or None if not found.
        """
        if self.id == item_id:
            return self
        for child in self._items:
            if child.id == item_id:
                return child
            if isinstance(child, Section):
                found = child.find_item_by_id(item_id)
                if found:
                    return found
        return None


class StatementStructure:
    """Top-level container for a financial statement structure.

    Manages a hierarchy of Section objects.
    """

    def __init__(
        self,
        id: str,
        name: str,
        description: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ):
        """Initialize a statement structure.

        Args:
            id: Unique identifier for the statement.
            name: Display name for the statement.
            description: Optional description text.
            metadata: Optional additional metadata.

        Raises:
            StatementError: If id or name is invalid.
        """
        if not id or not isinstance(id, str):
            raise StatementError(message=f"Invalid statement ID: {id}")
        if not name or not isinstance(name, str):
            raise StatementError(message=f"Invalid statement name: {name} for ID: {id}")

        self._id = id
        self._name = name
        self._description = description
        self._metadata = metadata or {}
        self._sections: list[Section] = []

    @property
    def id(self) -> str:
        """Get the statement identifier."""
        return self._id

    @property
    def name(self) -> str:
        """Get the statement display name."""
        return self._name

    @property
    def description(self) -> str:
        """Get the statement description."""
        return self._description

    @property
    def metadata(self) -> dict[str, Any]:
        """Get the statement metadata."""
        return self._metadata

    @property
    def sections(self) -> list[Section]:
        """Get the top-level sections."""
        return list(self._sections)

    @property
    def items(self) -> list[Section]:
        """Alias for sections to ease iteration."""
        return self.sections

    def add_section(self, section: Section) -> None:
        """Add a section to the statement.

        Args:
            section: Section to add.

        Raises:
            StatementError: If a section with the same id already exists.
        """
        if any(s.id == section.id for s in self._sections):
            raise StatementError(
                message=f"Duplicate section ID: {section.id} in statement: {self.id}"
            )
        self._sections.append(section)

    def find_item_by_id(self, item_id: str) -> Optional[Union[Section, StatementItem]]:
        """Find an item by its ID in the statement structure.

        Args:
            item_id: The ID of the item to find.

        Returns:
            Optional[Union[Section, StatementItem]]: The found item or None if not found.
        """
        for section in self._sections:
            item = section.find_item_by_id(item_id)
            if item:
                return item
        return None

    def get_calculation_items(
        self,
    ) -> list[Union[CalculatedLineItem, SubtotalLineItem]]:
        """Get all calculation items from the statement structure.

        Returns:
            List[Union[CalculatedLineItem, SubtotalLineItem]]: List of calculation items.
        """
        calculation_items = []

        def collect_calculation_items(items: list[Union["Section", "StatementItem"]]):
            for item in items:
                if isinstance(item, (CalculatedLineItem, SubtotalLineItem)):
                    calculation_items.append(item)
                elif isinstance(item, Section):
                    collect_calculation_items(item.items)

        collect_calculation_items(self._sections)
        return calculation_items

    def get_all_items(self) -> List[StatementItem]:
        """Get all StatementItem instances recursively from the structure.

        Traverses all sections and nested sections, collecting only objects that
        are subclasses of StatementItem (e.g., LineItem, CalculatedLineItem),
        excluding Section objects themselves.

        Returns:
            List[StatementItem]: A flat list of all statement items found.
        """
        all_statement_items: List[StatementItem] = []

        def _collect_items_recursive(items_or_sections: List[Union[Section, StatementItem]]) -> None:
            for item in items_or_sections:
                if isinstance(item, Section):
                    _collect_items_recursive(item.items)
                elif isinstance(item, StatementItem):
                    all_statement_items.append(item)

        _collect_items_recursive(self._sections)

        return all_statement_items
