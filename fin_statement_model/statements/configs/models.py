"""Define Pydantic models for statement configuration.

This module defines Pydantic models for validating statement configuration data,
including statements, sections, line items, calculations, and subtotals.
"""

from __future__ import annotations

from typing import Any, Optional, Union, Literal

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


class CalculationSpec(BaseModel):
    """Define a calculation specification.

    Args:
        type: Type identifier for the calculation (e.g., 'addition', 'subtraction').
        inputs: List of input node or line item IDs referenced by this calculation.
    """

    type: str = Field(
        ...,
        description="Type identifier for the calculation (e.g., 'addition', 'subtraction').",
    )
    inputs: list[str] = Field(
        ...,
        description="List of input node or line item IDs referenced by this calculation.",
    )

    model_config = ConfigDict(extra="forbid", frozen=True)


class AdjustmentFilterSpec(BaseModel):
    """Define an adjustment filter specification for configuration.

    This model represents the adjustment filter options that can be specified
    in configuration files. It maps to the core AdjustmentFilter model but
    uses serializable types suitable for YAML/JSON.

    Args:
        include_scenarios: Only include adjustments from these scenarios.
        exclude_scenarios: Exclude adjustments from these scenarios.
        include_tags: Include adjustments matching any of these tag prefixes.
        exclude_tags: Exclude adjustments matching any of these tag prefixes.
        require_all_tags: Include only adjustments having all these exact tags.
        include_types: Only include adjustments of these types.
        exclude_types: Exclude adjustments of these types.
        period: The specific period context for effective window checks.
    """

    include_scenarios: Optional[list[str]] = Field(
        None, description="Only include adjustments from these scenarios."
    )
    exclude_scenarios: Optional[list[str]] = Field(
        None, description="Exclude adjustments from these scenarios."
    )
    include_tags: Optional[list[str]] = Field(
        None, description="Include adjustments matching any of these tag prefixes."
    )
    exclude_tags: Optional[list[str]] = Field(
        None, description="Exclude adjustments matching any of these tag prefixes."
    )
    require_all_tags: Optional[list[str]] = Field(
        None, description="Include only adjustments having all these exact tags."
    )
    include_types: Optional[list[str]] = Field(
        None,
        description="Only include adjustments of these types (additive, multiplicative, replacement).",
    )
    exclude_types: Optional[list[str]] = Field(
        None,
        description="Exclude adjustments of these types (additive, multiplicative, replacement).",
    )
    period: Optional[str] = Field(
        None, description="The specific period context for effective window checks."
    )

    @field_validator("include_types", "exclude_types", mode="before")
    def validate_adjustment_types(cls, value: list[str] | None) -> list[str] | None:
        """Validate adjustment types are valid."""
        if value is not None:
            valid_types = {"additive", "multiplicative", "replacement"}
            for adj_type in value:
                if adj_type not in valid_types:
                    raise ValueError(
                        f"Invalid adjustment type '{adj_type}'. Must be one of: {valid_types}"
                    )
        return value

    model_config = ConfigDict(extra="forbid", frozen=True)


class BaseItemModel(BaseModel):
    """Define common fields for all statement items.

    Args:
        id: Unique identifier for the item. Must not contain spaces.
        name: Human-readable name of the item.
        description: Optional description for the item.
        metadata: Optional metadata dictionary for the item.
        sign_convention: Sign convention for the item (1 or -1).
        default_adjustment_filter: Optional default adjustment filter for this item.
        display_format: Optional specific number format string (e.g., ",.2f", ",.0f").
        hide_if_all_zero: Whether to hide this item if all values are zero.
        css_class: Optional CSS class name for HTML/web outputs.
        notes_references: List of footnote/note IDs referenced by this item.
        units: Optional unit description (e.g., "USD Thousands", "Percentage").
        display_scale_factor: Factor to scale values for display (e.g., 0.001 for thousands).
    """

    id: str = Field(
        ...,
        description="Unique identifier for the item. Must not contain spaces.",
    )
    name: str = Field(..., description="Human-readable name of the item.")
    description: Optional[str] = Field("", description="Optional description for the item.")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Optional metadata for the item."
    )
    sign_convention: int = Field(1, description="Sign convention for the item (1 or -1).")
    default_adjustment_filter: Optional[Union[AdjustmentFilterSpec, list[str]]] = Field(
        None,
        description="Optional default adjustment filter for this item. Can be a filter specification or list of tags.",
    )

    # Enhanced Display Control Fields
    display_format: Optional[str] = Field(
        None,
        description="Specific number format string for this item (e.g., ',.2f', ',.0f', '.1%').",
    )
    hide_if_all_zero: bool = Field(
        False,
        description="Whether to hide this item from display if all values are zero or null.",
    )
    css_class: Optional[str] = Field(
        None,
        description="CSS class name to apply to this item in HTML/web outputs.",
    )
    notes_references: list[str] = Field(
        default_factory=list,
        description="List of footnote or note IDs that reference this item.",
    )

    # Contra Item Support
    is_contra: bool = Field(
        False,
        description="Whether this is a contra item (e.g., Accumulated Depreciation, Treasury Stock, Sales Returns) that naturally reduces the balance of its category for display purposes.",
    )

    # Units and Scaling Fields
    units: Optional[str] = Field(
        None,
        description="Unit description for this item (e.g., 'USD Thousands', 'Percentage', 'Days').",
    )
    display_scale_factor: float = Field(
        1.0,
        description="Factor to scale values for display purposes (e.g., 0.001 to show in thousands).",
    )

    @field_validator("id", mode="before")
    def id_must_not_contain_spaces(cls, value: str) -> str:
        """Ensure that 'id' does not contain spaces."""
        if " " in value:
            raise ValueError("must not contain spaces")
        return value

    @field_validator("display_scale_factor", mode="before")
    def validate_display_scale_factor(cls, value: float) -> float:
        """Ensure display_scale_factor is positive and non-zero."""
        if value <= 0:
            raise ValueError("display_scale_factor must be positive and non-zero")
        return value

    @field_validator("display_format", mode="before")
    def validate_display_format(cls, value: Optional[str]) -> Optional[str]:
        """Validate that display_format is a reasonable format string."""
        if value is not None:
            # Basic validation - try to format a test number
            try:
                test_format = f"{12345.67:{value}}"
                # Basic sanity check that it produced something reasonable
                if not test_format or len(test_format) > 50:
                    raise ValueError("Invalid or problematic format string")
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid display_format '{value}': {e}") from e
        return value

    model_config = ConfigDict(extra="forbid", frozen=True)


class LineItemModel(BaseItemModel):
    """Define a basic line item configuration model.

    Args:
        type: Must be 'line_item' for this model.
        node_id: ID of the core node this line item maps to.
        standard_node_ref: Optional reference to a standard node name from the registry.
    """

    type: Literal["line_item"] = Field(
        "line_item", description="Discriminator for basic line items."
    )
    node_id: Optional[str] = Field(None, description="ID of the core node this line item maps to.")
    standard_node_ref: Optional[str] = Field(
        None, description="Reference to a standard node name from the standard_node_registry."
    )

    @model_validator(mode="before")
    def exactly_one_node_reference(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Ensure exactly one of 'node_id' or 'standard_node_ref' is provided."""
        node_id = values.get("node_id")
        standard_ref = values.get("standard_node_ref")

        if not node_id and not standard_ref:
            raise ValueError("must provide either 'node_id' or 'standard_node_ref'")
        if node_id and standard_ref:
            raise ValueError("cannot provide both 'node_id' and 'standard_node_ref' - use only one")
        return values

    model_config = ConfigDict(extra="forbid", frozen=True)


class MetricItemModel(BaseItemModel):
    """Define a metric-based line item configuration model.

    Args:
        type: Must be 'metric' for this model.
        metric_id: ID of the metric in the core registry.
        inputs: Mapping of metric input names to statement item IDs.
    """

    type: Literal["metric"] = Field("metric", description="Discriminator for metric-based items.")
    metric_id: str = Field(..., description="ID of the metric in the core.metrics.registry.")
    inputs: dict[str, str] = Field(
        ..., description="Mapping of metric input names to statement item IDs."
    )

    model_config = ConfigDict(extra="forbid", frozen=True)


class CalculatedItemModel(BaseItemModel):
    """Define a calculated line item configuration model.

    Args:
        type: Must be 'calculated' for this model.
        calculation: Calculation specification for the calculated item.
    """

    type: Literal["calculated"] = Field(
        "calculated", description="Discriminator for calculated items."
    )
    calculation: CalculationSpec = Field(
        ..., description="Calculation specification for the calculated item."
    )

    model_config = ConfigDict(extra="forbid", frozen=True)


class SubtotalModel(BaseItemModel):
    """Define a subtotal configuration model.

    Args:
        type: Must be 'subtotal' for this model.
        calculation: Optional calculation specification for the subtotal.
        items_to_sum: Optional list of item IDs to sum for the subtotal.
    """

    type: Literal["subtotal"] = Field("subtotal", description="Discriminator for subtotal items.")
    calculation: Optional[CalculationSpec] = Field(
        None, description="Calculation specification for the subtotal."
    )
    items_to_sum: Optional[list[str]] = Field(
        None, description="List of item IDs to sum for the subtotal."
    )

    @model_validator(mode="before")
    def exactly_one_of_calculation_or_items(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Ensure exactly one of 'calculation' or 'items_to_sum' is provided."""
        calc, items = values.get("calculation"), values.get("items_to_sum")
        if bool(calc) == bool(items):
            raise ValueError("must provide exactly one of 'calculation' or 'items_to_sum'")
        return values

    model_config = ConfigDict(extra="forbid", frozen=True)


class SectionModel(BaseItemModel):
    """Define a nested section within the statement configuration.

    Args:
        type: Must be 'section' for this model.
        items: List of line items, calculated items, subtotals, or nested sections.
        subsections: List of nested sections.
        subtotal: Optional subtotal configuration for this section.
        default_adjustment_filter: Optional default adjustment filter for this section.
    """

    type: Literal["section"] = Field("section", description="Discriminator for nested sections.")
    items: list[
        Union[
            LineItemModel,
            CalculatedItemModel,
            MetricItemModel,
            SubtotalModel,
            SectionModel,
        ]
    ] = Field(
        default_factory=list,
        description=("List of line items, calculated items, subtotals, or nested sections."),
    )
    subsections: list[SectionModel] = Field(
        default_factory=list,
        description="List of nested sections.",
    )
    subtotal: Optional[SubtotalModel] = Field(
        None, description="Optional subtotal configuration for this section."
    )

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def check_unique_item_ids(cls, section: SectionModel) -> SectionModel:
        """Ensure that item and subsection IDs within a section are unique and subtotal refs valid."""
        ids = [item.id for item in section.items] + [sub.id for sub in section.subsections]
        duplicates = {item_id for item_id in ids if ids.count(item_id) > 1}
        if duplicates:
            raise ValueError(
                f"Duplicate item id(s) in section '{section.id}': {', '.join(duplicates)}"
            )
        if section.subtotal and section.subtotal.items_to_sum is not None:
            valid_ids = [item.id for item in section.items]
            missing = [i for i in section.subtotal.items_to_sum if i not in valid_ids]
            if missing:
                raise ValueError(
                    f"Section '{section.id}' subtotal references undefined ids: {', '.join(missing)}"
                )
        return section


SectionModel.model_rebuild(force=True)


class StatementModel(BaseModel):
    """Define the top-level statement configuration model.

    Args:
        id: Unique identifier for the statement. Must not contain spaces.
        name: Human-readable name of the statement.
        description: Optional description of the statement.
        metadata: Optional metadata dictionary.
        sections: List of top-level sections in the statement.
        units: Optional default unit description for the entire statement.
        display_scale_factor: Optional default scale factor for the entire statement.
    """

    id: str = Field(..., description="Unique statement identifier. Must not contain spaces.")
    name: str = Field(..., description="Human-readable statement name.")
    description: Optional[str] = Field("", description="Optional statement description.")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Optional metadata dictionary."
    )
    sections: list[SectionModel] = Field(
        ..., description="List of top-level sections in the statement."
    )

    # Statement-level units and scaling
    units: Optional[str] = Field(
        None,
        description="Default unit description for the statement (e.g., 'USD Thousands').",
    )
    display_scale_factor: float = Field(
        1.0,
        description="Default scale factor for displaying values in this statement.",
    )

    @field_validator("id", mode="before")
    def id_must_not_contain_spaces(cls, value: str) -> str:
        """Ensure that statement 'id' does not contain spaces."""
        if " " in value:
            raise ValueError("must not contain spaces")
        return value

    @field_validator("display_scale_factor", mode="before")
    def validate_display_scale_factor(cls, value: float) -> float:
        """Ensure display_scale_factor is positive and non-zero."""
        if value <= 0:
            raise ValueError("display_scale_factor must be positive and non-zero")
        return value

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def check_unique_section_ids(cls, model: StatementModel) -> StatementModel:
        """Ensure that top-level section IDs are unique."""
        ids = [section.id for section in model.sections]
        duplicates = {sec_id for sec_id in ids if ids.count(sec_id) > 1}
        if duplicates:
            raise ValueError(f"Duplicate section id(s): {', '.join(duplicates)}")
        return model
