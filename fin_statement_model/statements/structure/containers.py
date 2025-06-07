"""Container classes for defining hierarchical financial statement structures.

This module provides Section and StatementStructure, which organize
LineItem and CalculatedLineItem objects into nested groups.
"""

from typing import Any, Optional, Union

from fin_statement_model.config import cfg_or_param
from fin_statement_model.core.errors import StatementError
from fin_statement_model.statements.structure.items import (
    StatementItem,
    StatementItemType,
    CalculatedLineItem,
    MetricLineItem,
    SubtotalLineItem,
)


__all__ = ["Section", "StatementStructure"]


class Section:
    """Represents a section in a financial statement.

    Sections group related items and subsections into a hierarchical container
    with enhanced display control and units metadata.
    """

    def __init__(
        self,
        id: str,
        name: str,
        description: str = "",
        metadata: Optional[dict[str, Any]] = None,
        default_adjustment_filter: Optional[Any] = None,
        display_format: Optional[str] = None,
        hide_if_all_zero: bool = False,
        css_class: Optional[str] = None,
        notes_references: Optional[list[str]] = None,
        units: Optional[str] = None,
        display_scale_factor: Optional[float] = None,
    ):
        """Initialize a section.

        Args:
            id: Unique identifier for the section.
            name: Display name for the section.
            description: Optional description text.
            metadata: Optional additional metadata.
            default_adjustment_filter: Optional default adjustment filter for this section.
            display_format: Optional specific number format string for section items.
            hide_if_all_zero: Whether to hide this section if all values are zero.
            css_class: Optional CSS class name for HTML/web outputs.
            notes_references: List of footnote/note IDs referenced by this section.
            units: Optional unit description for this section.
            display_scale_factor: Factor to scale values for display in this section.
                                If not provided, uses config default from display.scale_factor.

        Raises:
            StatementError: If id or name is invalid.
        """
        if not id or not isinstance(id, str):
            raise StatementError(f"Invalid section ID: {id}")
        if not name or not isinstance(name, str):
            raise StatementError(f"Invalid section name: {name} for ID: {id}")

        # Use config default if not provided
        display_scale_factor = cfg_or_param(
            "display.scale_factor", display_scale_factor
        )

        if display_scale_factor <= 0:
            raise StatementError(
                f"display_scale_factor must be positive for section: {id}"
            )

        self._id = id
        self._name = name
        self._description = description
        self._metadata = metadata or {}
        self._default_adjustment_filter = default_adjustment_filter
        self._display_format = display_format
        self._hide_if_all_zero = hide_if_all_zero
        self._css_class = css_class
        self._notes_references = notes_references or []
        self._units = units
        self._display_scale_factor = display_scale_factor
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
    def default_adjustment_filter(self) -> Optional[Any]:
        """Get the default adjustment filter for this section."""
        return self._default_adjustment_filter

    @property
    def display_format(self) -> Optional[str]:
        """Get the display format string for this section."""
        return self._display_format

    @property
    def hide_if_all_zero(self) -> bool:
        """Get whether to hide this section if all values are zero."""
        return self._hide_if_all_zero

    @property
    def css_class(self) -> Optional[str]:
        """Get the CSS class for this section."""
        return self._css_class

    @property
    def notes_references(self) -> list[str]:
        """Get the list of note references for this section."""
        return list(self._notes_references)

    @property
    def units(self) -> Optional[str]:
        """Get the unit description for this section."""
        return self._units

    @property
    def display_scale_factor(self) -> float:
        """Get the display scale factor for this section."""
        return self._display_scale_factor

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
            raise StatementError(f"Duplicate item ID: {item.id} in section: {self.id}")
        self._items.append(item)

    def find_item_by_id(
        self, item_id: str
    ) -> Optional[Union["Section", StatementItem]]:
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
        if hasattr(self, "subtotal") and self.subtotal and self.subtotal.id == item_id:
            return self.subtotal
        return None


class StatementStructure:
    """Top-level container for a financial statement structure.

    Manages a hierarchy of Section objects with statement-level display
    and units metadata.
    """

    def __init__(
        self,
        id: str,
        name: str,
        description: str = "",
        metadata: Optional[dict[str, Any]] = None,
        units: Optional[str] = None,
        display_scale_factor: Optional[float] = None,
    ):
        """Initialize a statement structure.

        Args:
            id: Unique identifier for the statement.
            name: Display name for the statement.
            description: Optional description text.
            metadata: Optional additional metadata.
            units: Optional default unit description for the statement.
            display_scale_factor: Default scale factor for displaying values.
                                If not provided, uses config default from display.scale_factor.

        Raises:
            StatementError: If id or name is invalid.
        """
        if not id or not isinstance(id, str):
            raise StatementError(f"Invalid statement ID: {id}")
        if not name or not isinstance(name, str):
            raise StatementError(f"Invalid statement name: {name} for ID: {id}")

        # Use config default if not provided
        display_scale_factor = cfg_or_param(
            "display.scale_factor", display_scale_factor
        )

        if display_scale_factor <= 0:
            raise StatementError(
                f"display_scale_factor must be positive for statement: {id}"
            )

        self._id = id
        self._name = name
        self._description = description
        self._metadata = metadata or {}
        self._units = units
        self._display_scale_factor = display_scale_factor
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
    def units(self) -> Optional[str]:
        """Get the default unit description for the statement."""
        return self._units

    @property
    def display_scale_factor(self) -> float:
        """Get the default display scale factor for the statement."""
        return self._display_scale_factor

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
                f"Duplicate section ID: {section.id} in statement: {self.id}"
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
                if isinstance(item, CalculatedLineItem | SubtotalLineItem):
                    calculation_items.append(item)
                elif isinstance(item, Section):
                    collect_calculation_items(item.items)
                    if hasattr(item, "subtotal") and item.subtotal:
                        if isinstance(item.subtotal, SubtotalLineItem):
                            calculation_items.append(item.subtotal)
                        else:
                            pass

        collect_calculation_items(self._sections)
        return calculation_items

    def get_metric_items(self) -> list[MetricLineItem]:
        """Get all metric items from the statement structure.

        Returns:
            List[MetricLineItem]: List of metric items.
        """
        metric_items = []

        def collect_metric_items(items: list[Union["Section", "StatementItem"]]):
            for item in items:
                if isinstance(item, MetricLineItem):
                    metric_items.append(item)
                elif isinstance(item, Section):
                    collect_metric_items(item.items)
                    # Subtotals are handled by get_calculation_items, not relevant here

        collect_metric_items(self._sections)
        return metric_items

    def get_all_items(self) -> list[StatementItem]:
        """Get all StatementItem instances recursively from the structure.

        Traverses all sections and nested sections, collecting only objects that
        are subclasses of StatementItem (e.g., LineItem, CalculatedLineItem),
        excluding Section objects themselves.

        Returns:
            List[StatementItem]: A flat list of all statement items found.
        """
        all_statement_items: list[StatementItem] = []

        def _collect_items_recursive(
            items_or_sections: list[Union[Section, StatementItem]],
        ) -> None:
            for item in items_or_sections:
                if isinstance(item, Section):
                    _collect_items_recursive(item.items)
                    # Also collect the section's subtotal if it exists and is a StatementItem
                    if hasattr(item, "subtotal") and isinstance(
                        item.subtotal, StatementItem
                    ):
                        all_statement_items.append(item.subtotal)
                elif isinstance(item, StatementItem):
                    all_statement_items.append(item)

        _collect_items_recursive(self._sections)

        return all_statement_items
