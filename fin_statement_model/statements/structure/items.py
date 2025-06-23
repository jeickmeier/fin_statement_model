"""Statement structure items module defining line items, calculated items, and subtotals."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional, cast

from fin_statement_model.core.errors import StatementError
from fin_statement_model.core.nodes.standard_registry import StandardNodeRegistry
from fin_statement_model.config.access import cfg_or_param

__all__ = [
    "CalculatedLineItem",
    "LineItem",
    "MetricLineItem",
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
      METRIC: Derived metric item from registry
    """

    SECTION = "section"
    LINE_ITEM = "line_item"
    SUBTOTAL = "subtotal"
    CALCULATED = "calculated"
    METRIC = "metric"


class StatementItem(ABC):
    """Abstract base class for all statement structure items.

    Defines a common interface: id, name, item_type, default_adjustment_filter,
    and enhanced display control and units metadata.
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

    @property
    @abstractmethod
    def default_adjustment_filter(self) -> Optional[Any]:
        """Get the default adjustment filter for this item."""

    @property
    @abstractmethod
    def display_format(self) -> Optional[str]:
        """Get the display format string for this item."""

    @property
    @abstractmethod
    def hide_if_all_zero(self) -> bool:
        """Get whether to hide this item if all values are zero."""

    @property
    @abstractmethod
    def css_class(self) -> Optional[str]:
        """Get the CSS class for this item."""

    @property
    @abstractmethod
    def notes_references(self) -> list[str]:
        """Get the list of note references for this item."""

    @property
    @abstractmethod
    def units(self) -> Optional[str]:
        """Get the unit description for this item."""

    @property
    @abstractmethod
    def display_scale_factor(self) -> float:
        """Get the display scale factor for this item."""

    @property
    @abstractmethod
    def is_contra(self) -> bool:
        """Get whether this is a contra item for special display formatting."""


class LineItem(StatementItem):
    """Represents a basic line item in a financial statement.

    Args:
      id: Unique ID for the line item
      name: Display name for the line item
      node_id: ID of the core graph node that holds values (optional if standard_node_ref provided)
      standard_node_ref: Reference to a standard node name from the registry (optional if node_id provided)
      description: Optional explanatory text
      sign_convention: 1 for normal values, -1 for inverted
      metadata: Optional additional attributes
      default_adjustment_filter: Optional default adjustment filter for this item
      display_format: Optional specific number format string
      hide_if_all_zero: Whether to hide this item if all values are zero
      css_class: Optional CSS class name for HTML/web outputs
      notes_references: List of footnote/note IDs referenced by this item
      units: Optional unit description
      display_scale_factor: Factor to scale values for display
      is_contra: Whether this is a contra item for special display formatting

    Raises:
      StatementError: If inputs are invalid
    """

    def __init__(
        self,
        id: str,
        name: str,
        node_id: Optional[str] = None,
        standard_node_ref: Optional[str] = None,
        description: str = "",
        sign_convention: int = 1,
        metadata: Optional[dict[str, Any]] = None,
        default_adjustment_filter: Optional[Any] = None,
        display_format: Optional[str] = None,
        hide_if_all_zero: bool = False,
        css_class: Optional[str] = None,
        notes_references: Optional[list[str]] = None,
        units: Optional[str] = None,
        display_scale_factor: Optional[float] = None,
        is_contra: bool = False,
    ):
        """Initialize a basic LineItem.

        Args:
            id: Unique ID for the line item.
            name: Display name for the line item.
            node_id: ID of the core graph node holding values (optional if standard_node_ref provided).
            standard_node_ref: Reference to a standard node name (optional if node_id provided).
            description: Optional explanatory text.
            sign_convention: Sign convention (1 for positive, -1 for negative).
            metadata: Optional additional attributes.
            default_adjustment_filter: Optional default adjustment filter for this item.
            display_format: Optional specific number format string (e.g., ",.2f").
            hide_if_all_zero: Whether to hide this item if all values are zero.
            css_class: Optional CSS class name for HTML/web outputs.
            notes_references: List of footnote/note IDs referenced by this item.
            units: Optional unit description (e.g., "USD Thousands").
            display_scale_factor: Factor to scale values for display (e.g., 0.001 for thousands).
                                If not provided, uses config default from display.scale_factor.
            is_contra: Whether this is a contra item for special display formatting.

        Raises:
            StatementError: If inputs are invalid.
        """
        if not id or not isinstance(id, str):
            raise StatementError(f"Invalid line item ID: {id}")
        if not name or not isinstance(name, str):
            raise StatementError(f"Invalid line item name: {name} for ID: {id}")

        # Validate that exactly one of node_id or standard_node_ref is provided
        if not node_id and not standard_node_ref:
            raise StatementError(
                f"Must provide either 'node_id' or 'standard_node_ref' for line item: {id}"
            )
        if node_id and standard_node_ref:
            raise StatementError(
                f"Cannot provide both 'node_id' and 'standard_node_ref' for line item: {id}"
            )

        if sign_convention not in (1, -1):
            raise StatementError(
                f"Invalid sign convention {sign_convention} for item: {id}"
            )

        # Use config default if not provided (import only when needed)
        display_scale_factor = cfg_or_param(
            "display.scale_factor", display_scale_factor
        )

        if display_scale_factor is None or display_scale_factor <= 0:
            raise StatementError(
                f"display_scale_factor must be positive for item: {id}"
            )

        self._id = id
        self._name = name
        self._node_id = node_id
        self._standard_node_ref = standard_node_ref
        self._description = description
        self._sign_convention = sign_convention
        self._metadata = metadata or {}
        self._default_adjustment_filter = default_adjustment_filter
        self._display_format = display_format
        self._hide_if_all_zero = hide_if_all_zero
        self._css_class = css_class
        self._notes_references = notes_references or []
        self._units = units
        self._display_scale_factor = display_scale_factor
        self._is_contra = is_contra

    @property
    def id(self) -> str:
        """Get the unique identifier of the line item."""
        return self._id

    @property
    def name(self) -> str:
        """Get the display name of the line item."""
        return self._name

    @property
    def node_id(self) -> Optional[str]:
        """Get the core graph node ID for this line item (if provided directly)."""
        return self._node_id

    @property
    def standard_node_ref(self) -> Optional[str]:
        """Get the standard node reference for this line item (if provided)."""
        return self._standard_node_ref

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
    def default_adjustment_filter(self) -> Optional[Any]:
        """Get the default adjustment filter for this item."""
        return self._default_adjustment_filter

    @property
    def display_format(self) -> Optional[str]:
        """Get the display format string for this item."""
        return self._display_format

    @property
    def hide_if_all_zero(self) -> bool:
        """Get whether to hide this item if all values are zero."""
        return self._hide_if_all_zero

    @property
    def css_class(self) -> Optional[str]:
        """Get the CSS class for this item."""
        return self._css_class

    @property
    def notes_references(self) -> list[str]:
        """Get the list of note references for this item."""
        return list(self._notes_references)

    @property
    def units(self) -> Optional[str]:
        """Get the unit description for this item."""
        return self._units

    @property
    def display_scale_factor(self) -> float:
        """Get the display scale factor for this item."""
        return self._display_scale_factor

    @property
    def is_contra(self) -> bool:
        """Get whether this is a contra item for special display formatting."""
        return self._is_contra

    @property
    def item_type(self) -> StatementItemType:
        """Get the type of this item (LINE_ITEM)."""
        return StatementItemType.LINE_ITEM

    def get_resolved_node_id(self, registry: StandardNodeRegistry) -> Optional[str]:
        """Get the resolved node ID, handling both direct node_id and standard_node_ref.

        Args:
            registry: Standard node registry for resolving references.

        Returns:
            The resolved node ID, or None if no node ID could be resolved.
        """
        if self._node_id:
            return self._node_id

        if self._standard_node_ref:
            # Try to get the standard name (handles alternate names too)
            return registry.get_standard_name(self._standard_node_ref)

        return None


class MetricLineItem(LineItem):
    """Represents a line item whose calculation is defined by a core metric.

    Args:
      id: Unique ID (also used as node_id)
      name: Display name
      metric_id: ID of the metric in the core.metrics.registry
      inputs: Dict mapping metric input names to statement item IDs
      description: Optional description
      sign_convention: 1 or -1
      metadata: Optional metadata
      default_adjustment_filter: Optional default adjustment filter for this item
      display_format: Optional specific number format string
      hide_if_all_zero: Whether to hide this item if all values are zero
      css_class: Optional CSS class name for HTML/web outputs
      notes_references: List of footnote/note IDs referenced by this item
      units: Optional unit description
      display_scale_factor: Factor to scale values for display
      is_contra: Whether this is a contra item for special display formatting

    Raises:
      StatementError: If metric_id or inputs are invalid
    """

    def __init__(
        self,
        id: str,
        name: str,
        metric_id: str,
        inputs: dict[str, str],
        description: str = "",
        sign_convention: int = 1,
        metadata: Optional[dict[str, Any]] = None,
        default_adjustment_filter: Optional[Any] = None,
        display_format: Optional[str] = None,
        hide_if_all_zero: bool = False,
        css_class: Optional[str] = None,
        notes_references: Optional[list[str]] = None,
        units: Optional[str] = None,
        display_scale_factor: Optional[float] = None,
        is_contra: bool = False,
    ):
        """Initialize a MetricLineItem referencing a registered metric.

        Args:
            id: Unique ID (also used as node_id).
            name: Display name.
            metric_id: ID of the metric in the core.metrics.registry.
            inputs: Dict mapping metric input names to statement item IDs.
            description: Optional description.
            sign_convention: Sign convention (1 or -1).
            metadata: Optional metadata.
            default_adjustment_filter: Optional default adjustment filter for this item.
            display_format: Optional specific number format string.
            hide_if_all_zero: Whether to hide this item if all values are zero.
            css_class: Optional CSS class name for HTML/web outputs.
            notes_references: List of footnote/note IDs referenced by this item.
            units: Optional unit description.
            display_scale_factor: Factor to scale values for display.
                                If not provided, uses config default from display.scale_factor.
            is_contra: Whether this is a contra item for special display formatting.

        Raises:
            StatementError: If metric_id or inputs are invalid.
        """
        super().__init__(
            id=id,
            name=name,
            node_id=id,
            description=description,
            sign_convention=sign_convention,
            metadata=metadata,
            default_adjustment_filter=default_adjustment_filter,
            display_format=display_format,
            hide_if_all_zero=hide_if_all_zero,
            css_class=css_class,
            notes_references=notes_references,
            units=units,
            display_scale_factor=display_scale_factor,
            is_contra=is_contra,
        )
        if not metric_id or not isinstance(metric_id, str):
            raise StatementError(f"Invalid metric_id '{metric_id}' for item: {id}")
        if not isinstance(inputs, dict) or not inputs:
            raise StatementError(
                f"Metric inputs must be a non-empty dictionary for item: {id}"
            )
        if not all(
            isinstance(k, str) and isinstance(v, str) for k, v in inputs.items()
        ):
            raise StatementError(
                f"Metric input keys and values must be strings for item: {id}"
            )

        self._metric_id = metric_id
        self._inputs = inputs

    @property
    def metric_id(self) -> str:
        """Get the ID of the metric referenced from the core registry."""
        return self._metric_id

    @property
    def inputs(self) -> dict[str, str]:
        """Get the mapping from metric input names to statement item IDs."""
        return self._inputs

    @property
    def item_type(self) -> StatementItemType:
        """Get the type of this item (METRIC)."""
        return StatementItemType.METRIC


class CalculatedLineItem(LineItem):
    """Represents a calculated line item whose values come from graph calculations.

    Args:
      id: Unique ID (also used as node_id)
      name: Display name
      calculation: Dict with 'type', 'inputs', optional 'parameters'
      description: Optional description
      sign_convention: 1 or -1
      metadata: Optional metadata
      default_adjustment_filter: Optional default adjustment filter for this item
      display_format: Optional specific number format string
      hide_if_all_zero: Whether to hide this item if all values are zero
      css_class: Optional CSS class name for HTML/web outputs
      notes_references: List of footnote/note IDs referenced by this item
      units: Optional unit description
      display_scale_factor: Factor to scale values for display
      is_contra: Whether this is a contra item for special display formatting

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
        default_adjustment_filter: Optional[Any] = None,
        display_format: Optional[str] = None,
        hide_if_all_zero: bool = False,
        css_class: Optional[str] = None,
        notes_references: Optional[list[str]] = None,
        units: Optional[str] = None,
        display_scale_factor: Optional[float] = None,
        is_contra: bool = False,
    ):
        """Initialize a CalculatedLineItem based on calculation specification.

        Args:
            id: Unique ID (also used as node_id).
            name: Display name.
            calculation: Calculation spec dict with 'type', 'inputs', optional 'parameters'.
            description: Optional description.
            sign_convention: Sign convention (1 or -1).
            metadata: Optional metadata.
            default_adjustment_filter: Optional default adjustment filter for this item.
            display_format: Optional specific number format string.
            hide_if_all_zero: Whether to hide this item if all values are zero.
            css_class: Optional CSS class name for HTML/web outputs.
            notes_references: List of footnote/note IDs referenced by this item.
            units: Optional unit description.
            display_scale_factor: Factor to scale values for display.
                                If not provided, uses config default from display.scale_factor.
            is_contra: Whether this is a contra item for special display formatting.

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
            default_adjustment_filter=default_adjustment_filter,
            display_format=display_format,
            hide_if_all_zero=hide_if_all_zero,
            css_class=css_class,
            notes_references=notes_references,
            units=units,
            display_scale_factor=display_scale_factor,
            is_contra=is_contra,
        )
        if not isinstance(calculation, dict):
            raise StatementError(f"Invalid calculation spec for item: {id}")
        if "type" not in calculation:
            raise StatementError(f"Missing calculation type for item: {id}")
        inputs = calculation.get("inputs")
        if not isinstance(inputs, list) or not inputs:
            raise StatementError(
                f"Calculation inputs must be a non-empty list for item: {id}"
            )
        self._calculation = calculation

    @property
    def calculation_type(self) -> str:
        """Get the calculation operation type (e.g., 'addition')."""
        return cast(str, self._calculation["type"])

    @property
    def input_ids(self) -> list[str]:
        """Get the list of input item IDs for this calculation."""
        return cast(list[str], self._calculation["inputs"])

    @property
    def parameters(self) -> dict[str, Any]:
        """Get optional parameters for the calculation."""
        return cast(dict[str, Any], self._calculation.get("parameters", {}))

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
      default_adjustment_filter: Optional default adjustment filter for this item
      display_format: Optional specific number format string
      hide_if_all_zero: Whether to hide this item if all values are zero
      css_class: Optional CSS class name for HTML/web outputs
      notes_references: List of footnote/note IDs referenced by this item
      units: Optional unit description
      display_scale_factor: Factor to scale values for display

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
        default_adjustment_filter: Optional[Any] = None,
        display_format: Optional[str] = None,
        hide_if_all_zero: bool = False,
        css_class: Optional[str] = None,
        notes_references: Optional[list[str]] = None,
        units: Optional[str] = None,
        display_scale_factor: Optional[float] = None,
        is_contra: bool = False,
    ):
        """Initialize a SubtotalLineItem summing multiple items.

        Args:
            id: Unique ID (also used as node_id).
            name: Display name.
            item_ids: List of IDs to sum.
            description: Optional description.
            sign_convention: Sign convention (1 or -1).
            metadata: Optional metadata.
            default_adjustment_filter: Optional default adjustment filter for this item.
            display_format: Optional specific number format string.
            hide_if_all_zero: Whether to hide this item if all values are zero.
            css_class: Optional CSS class name for HTML/web outputs.
            notes_references: List of footnote/note IDs referenced by this item.
            units: Optional unit description.
            display_scale_factor: Factor to scale values for display.
                                If not provided, uses config default from display.scale_factor.
            is_contra: Whether this is a contra item for special display formatting.

        Raises:
            StatementError: If item_ids is empty or not a list.
        """
        if not isinstance(item_ids, list) or not item_ids:
            raise StatementError(f"Invalid or empty item IDs for subtotal: {id}")
        calculation = {"type": "addition", "inputs": item_ids, "parameters": {}}
        super().__init__(
            id=id,
            name=name,
            calculation=calculation,
            description=description,
            sign_convention=sign_convention,
            metadata=metadata,
            default_adjustment_filter=default_adjustment_filter,
            display_format=display_format,
            hide_if_all_zero=hide_if_all_zero,
            css_class=css_class,
            notes_references=notes_references,
            units=units,
            display_scale_factor=display_scale_factor,
            is_contra=is_contra,
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
