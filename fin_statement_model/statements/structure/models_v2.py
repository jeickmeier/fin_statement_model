"""fin_statement_model.statements.structure.models_v2.

New immutable Pydantic-v2 models that serve as *both* the validated config **and**
runtime representation for statement structures.  These models are intentionally
kept separate from the legacy hand-rolled runtime classes so that existing code
continues to function unchanged while the package gradually migrates to the new
API.

The public surface of this module follows the design proposed in the `feat/statements-v2-models`
initiative:

    StatementStructure  (root)
      ├─ Section
      └─ StatementItem (discriminated union)
          ├─ LineItem
          ├─ CalculatedLineItem
          ├─ SubtotalLineItem
          └─ MetricLineItem

A handful of auxiliary helpers (``CalculationSpec`` and the ``StatementItemType``
literals) are also included for convenience.

Key implementation details:

* All models are immutable (`frozen=True`) and forbid extra fields
  (`extra='forbid'`).
* The discriminator field is ``item_type`` **but** accepts/serialises using the
  alias ``type`` so that existing YAML/JSON fixtures continue to load without
  modification.
* A ``computed_field`` named ``all_item_ids`` on ``StatementStructure``
  recursively collects the identifiers of every concrete item in the
  structure.
* Public type aliases are re-exported via ``__all__`` for convenient import.
"""

from __future__ import annotations

# The *Sequence* ABC is required at runtime for tree traversal helpers.  While
# we keep the TYPE_CHECKING import for static analysers, an unconditional
# import avoids `NameError` exceptions when these helpers execute.
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Literal, cast, overload

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, computed_field
import yaml

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "CalculatedLineItem",
    # Base spec helpers
    "CalculationSpec",
    "LineItem",
    "MetricLineItem",
    # Container models
    "Section",
    # Discriminated union & concrete subclasses
    "StatementItem",
    # Literal enum
    "StatementItemType",
    "StatementStructure",
    "SubtotalLineItem",
    # Top-level helpers
    "load_structure",
]

# ---------------------------------------------------------------------------
# Helper / shared types
# ---------------------------------------------------------------------------

StatementItemType = Literal[
    "line_item",  # basic line linked to a core node
    "calculated",  # calculated from other items
    "subtotal",  # subtotal of sibling items
    "metric",  # value calculated by the metrics engine
    "section",  # section container (needed for Section subclass)
]


class CalculationSpec(BaseModel):
    """Specification for a simple arithmetic calculation.

    This is a minimal abstraction required by *CalculatedLineItem* and
    *SubtotalLineItem* so that existing YAML fixtures validate.  More elaborate
    calculation grammars can be introduced later without affecting the public
    contract of the parent objects.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: str = Field(..., description="Calculation type identifier, e.g. 'addition'.")
    inputs: list[str] = Field(..., description="Identifiers (node IDs or item IDs) used as inputs to the calculation.")


# ---------------------------------------------------------------------------
# Base class for all concrete items (excluding *Section*)
# ---------------------------------------------------------------------------


class _BaseItem(BaseModel):
    """Common attributes shared across concrete StatementItems."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(..., description="Unique identifier. Must not contain spaces.")
    name: str = Field(..., description="Human-readable display name.")
    description: str | None = Field(None, description="Optional description.")
    metadata: dict[str, Any] | None = Field(None, description="Arbitrary metadata.")

    # Discriminator — aliased to keep existing YAML files intact
    item_type: StatementItemType = Field(..., alias="type", description="Discriminator for the item subtype.")

    # Optional display / formatting helpers — kept minimal for now so as not to
    # replicate the full legacy API yet.  They are treated as opaque to the new
    # runtime consumers (formatter, renderer, etc.) and merely preserved so
    # they can be round-tripped without loss.
    sign_convention: int | None = Field(
        None,
        description="Sign convention (1 or -1) indicating the natural sign of the value.",
    )
    display_format: str | None = Field(None, description="Override for numeric display format, e.g. ',.1f'.")
    hide_if_all_zero: bool | None = Field(None, description="Hide row if all values are zero.")
    css_class: str | None = Field(None, description="Optional CSS class for HTML outputs.")
    notes_references: list[str] | None = Field(None, description="List of note IDs referenced by this item.")

    # Units & scaling
    units: str | None = Field(None, description="Unit descriptor, e.g. 'USD thousands'.")
    display_scale_factor: float | None = Field(None, description="Scale factor applied when displaying the value.")


# ---------------------------------------------------------------------------
# Concrete item subclasses
# ---------------------------------------------------------------------------


class LineItem(_BaseItem):
    """A basic line item directly mapped to a graph node."""

    item_type: Literal["line_item"] = Field("line_item", alias="type")

    node_id: str | None = Field(None, description="ID of the core graph node backing this line item.")
    standard_node_ref: str | None = Field(
        None,
        description="Optional reference to a standard node in the registry (used instead of *node_id*).",
    )

    # -----------------------------------------------------------------
    # Legacy-compatibility helpers
    # -----------------------------------------------------------------

    def get_resolved_node_id(self, registry: Any) -> str | None:
        """Return the concrete graph node ID for this line item.

        This mirrors the behaviour of the legacy ``LineItem.get_resolved_node_id``
        method so that existing population utilities (e.g. ``IDResolver``)
        continue to operate unchanged.

        Args:
            registry: The standard-node registry providing canonical node names.

        Returns:
            The resolved node identifier or ``None`` when the item cannot be
            mapped to a concrete node.
        """
        # Resolve via explicit node_id first.
        if self.node_id is not None:
            return self.node_id

        if self.standard_node_ref is not None:
            try:
                return cast("str", registry.get_standard_name(self.standard_node_ref))
            except (LookupError, AttributeError, ValueError):
                # A wide but *not* blanket set of errors expected when the registry
                # cannot resolve the supplied reference.
                return None

        return None


class MetricLineItem(_BaseItem):
    """A line item whose value comes from the *metrics* subsystem."""

    item_type: Literal["metric"] = Field("metric", alias="type")

    metric_id: str = Field(..., description="Identifier of the metric definition.")
    inputs: dict[str, str] = Field(
        default_factory=dict, description="Mapping of metric input names to statement item IDs."
    )


class CalculatedLineItem(_BaseItem):
    """An explicit calculation between sibling items or nodes."""

    item_type: Literal["calculated"] = Field("calculated", alias="type")

    calculation: CalculationSpec = Field(..., description="Calculation specification.")

    # -----------------------------------------------------------------
    # Legacy-compatibility helpers
    # -----------------------------------------------------------------

    @property
    def input_ids(self) -> list[str]:
        """Return the identifiers of the calculation inputs.

        Provided for backwards-compatibility with the legacy runtime which
        expected a dedicated ``input_ids`` attribute.
        """
        return self.calculation.inputs

    @property
    def calculation_type(self) -> str:
        """Return the operation identifier (e.g. ``'addition'``)."""
        return self.calculation.type

    @property
    def parameters(self) -> dict[str, Any]:
        """Return optional calculation parameters.

        The minimal v2 grammar currently does not expose additional
        parameters, but the attribute is kept for interface parity with the
        legacy implementation.
        """
        return {}


class SubtotalLineItem(_BaseItem):
    """A subtotal of a list of sibling items or an ad-hoc calculation."""

    item_type: Literal["subtotal"] = Field("subtotal", alias="type")

    # Either *calculation* **or** *items_to_sum* should be provided (enforced by
    # a simple validator below).
    calculation: CalculationSpec | None = Field(
        None, description="Optional explicit calculation overriding *items_to_sum*."
    )
    items_to_sum: list[str] | None = Field(
        None,
        description="IDs of items to sum (ignored when *calculation* is set).",
    )

    # -----------------------------------------------------------------
    # Legacy-compatibility helpers
    # -----------------------------------------------------------------

    @property
    def item_ids(self) -> list[str]:
        """Return the list of item identifiers contributing to this subtotal."""
        if self.items_to_sum is not None:
            return self.items_to_sum
        if self.calculation is not None:
            return self.calculation.inputs
        return []

    # ---------------------------------------------------------------------
    # Validators
    # ---------------------------------------------------------------------

    @classmethod
    def model_validate(cls, obj: Any, **kwargs: Any) -> SubtotalLineItem:
        """Validate incoming data and enforce exclusive presence of *calculation* xor *items_to_sum*."""
        model = super().model_validate(obj, **kwargs)
        if (model.calculation is None) == (not model.items_to_sum):
            # Exactly *one* of the two should be provided
            raise ValueError("Provide *either* 'calculation' or 'items_to_sum' (but not both) on a subtotal item.")
        return model


# ---------------------------------------------------------------------------
# Discriminated union type alias
# ---------------------------------------------------------------------------

StatementItem = Annotated[
    LineItem | CalculatedLineItem | SubtotalLineItem | MetricLineItem,
    Field(discriminator="item_type"),
]

# ---------------------------------------------------------------------------
# Section (recursive container) & StatementStructure (root)
# ---------------------------------------------------------------------------


class Section(_BaseItem):
    """A recursive container grouping line items and/or nested sections."""

    item_type: Literal["section"] = Field("section", alias="type")

    items: list[Section | StatementItem] = Field(
        default_factory=list,
        description="Child items (sections or concrete statement items).",
    )

    subtotal: SubtotalLineItem | None = Field(
        None, description="Optional subtotal automatically computed for this section."
    )


class StatementStructure(BaseModel):
    """Root model representing the entire statement definition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(..., description="Unique identifier (slug).")
    name: str = Field(..., description="Human-readable statement name.")
    description: str | None = Field(None, description="Optional description.")
    metadata: dict[str, Any] | None = Field(None, description="Arbitrary metadata.")

    sections: list[Section] = Field(..., description="Top-level sections of the statement.")

    # Statement-level units & scaling
    units: str | None = Field(None, description="Default unit descriptor for the statement.")
    display_scale_factor: float | None = Field(None, description="Default display scale factor.")

    # ---------------------------------------------------------------------
    # Derived conveniences
    # ---------------------------------------------------------------------

    @computed_field(return_type=list[str])
    def all_item_ids(self) -> list[str]:
        """Return *all* item IDs (recursively) in the statement (excluding sections)."""
        ids: list[str] = []

        def _collect(items: Sequence[Section | StatementItem]) -> None:
            for item in items:
                if isinstance(item, Section):
                    _collect(item.items)
                    if item.subtotal is not None:
                        ids.append(item.subtotal.id)
                else:
                    ids.append(item.id)

        _collect(self.sections)
        return ids

    # -----------------------------------------------------------------
    # Legacy-compatibility helpers - traversal utilities
    # -----------------------------------------------------------------

    def find_item_by_id(self, item_id: str) -> Section | StatementItem | None:
        """Recursively search for an item (or section) with *item_id*."""

        def _search(items: Sequence[Section | StatementItem]) -> Section | StatementItem | None:
            for itm in items:
                if itm.id == item_id:
                    return itm
                if isinstance(itm, Section):
                    found = _search(itm.items)
                    if found is not None:
                        return found
                    if itm.subtotal is not None and itm.subtotal.id == item_id:
                        return itm.subtotal
            return None

        return _search(self.sections)

    # The following helper collections reproduce the legacy public API so that
    # downstream utilities (population, formatting, etc.) can operate on either
    # v1 *or* v2 structures transparently.

    def get_all_items(self) -> list[StatementItem]:
        """Return *all* concrete items (excluding sections) in a flat list."""
        collected: list[StatementItem] = []

        def _collect(items: Sequence[Section | StatementItem]) -> None:
            for itm in items:
                if isinstance(itm, Section):
                    _collect(itm.items)
                    if itm.subtotal is not None:
                        collected.append(itm.subtotal)
                else:
                    collected.append(itm)

        _collect(self.sections)
        return collected

    def get_calculation_items(self) -> list[CalculatedLineItem | SubtotalLineItem]:
        """Return calculation and subtotal items (excluding metrics)."""
        items: list[CalculatedLineItem | SubtotalLineItem] = []

        def _collect(children: Sequence[Section | StatementItem]) -> None:
            for itm in children:
                if isinstance(itm, CalculatedLineItem | SubtotalLineItem):
                    items.append(itm)
                elif isinstance(itm, Section):
                    _collect(itm.items)
                    if itm.subtotal is not None:
                        items.append(itm.subtotal)

        _collect(self.sections)
        return items

    def get_metric_items(self) -> list[MetricLineItem]:
        """Return all metric items within the structure."""
        metrics: list[MetricLineItem] = []

        def _collect(children: Sequence[Section | StatementItem]) -> None:
            for itm in children:
                if isinstance(itm, MetricLineItem):
                    metrics.append(itm)
                elif isinstance(itm, Section):
                    _collect(itm.items)

        _collect(self.sections)
        return metrics


# ---------------------------------------------------------------------------
# Public loader helper
# ---------------------------------------------------------------------------


@overload
def load_structure(raw_cfg: dict[str, Any]) -> StatementStructure: ...


@overload
def load_structure(raw_cfg: str | Path) -> StatementStructure: ...


def load_structure(raw_cfg: dict[str, Any] | str | Path) -> StatementStructure:
    """Parse *raw_cfg* (dict or YAML/JSON path) into a ``StatementStructure``.

    Args:
        raw_cfg: Either an *in-memory* dictionary **or** a filesystem path
            (``str`` or :class:`~pathlib.Path`) pointing to a ``.yaml``/``.yml``
            or ``.json`` file.

    Returns:
        A fully-validated, immutable :class:`~StatementStructure` instance.
    """
    if isinstance(raw_cfg, dict):
        data: dict[str, Any] = raw_cfg
    else:
        path = Path(raw_cfg).expanduser() if not isinstance(raw_cfg, Path) else raw_cfg.expanduser()
        if not path.exists():
            raise FileNotFoundError(path)
        if path.suffix.lower() in {".yaml", ".yml"}:
            data = yaml.safe_load(path.read_text())
        elif path.suffix.lower() == ".json":
            import json

            data = json.loads(path.read_text())
        else:
            raise ValueError(
                f"Unsupported file type for statement structure: {path.suffix} (expected .yaml/.yml/.json)"
            )

    # Validate & return immutable model
    return StatementStructure.model_validate(data)


# ---------------------------------------------------------------------------
# TypeAdapter helper (makes external validation easier without having to import
# ``TypeAdapter`` in user code).  Not part of the public API but retained so we
# can write concise tests in *test_models_v2.py*.
# ---------------------------------------------------------------------------

_adapter_statement_item: TypeAdapter[StatementItem] = TypeAdapter(StatementItem)


def _validate_item(data: Any) -> StatementItem:
    """Validate *data* as a :pydata:`StatementItem` instance (internal helper)."""
    return _adapter_statement_item.validate_python(data)
