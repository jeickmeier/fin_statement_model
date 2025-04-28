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


class BaseItemModel(BaseModel):
    """Define common fields for all statement items.

    Args:
        id: Unique identifier for the item. Must not contain spaces.
        name: Human-readable name of the item.
        description: Optional description for the item.
        metadata: Optional metadata dictionary for the item.
        sign_convention: Sign convention for the item (1 or -1).
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

    @field_validator("id", mode="before")
    def id_must_not_contain_spaces(cls, value: str) -> str:
        """Ensure that 'id' does not contain spaces."""
        if " " in value:
            raise ValueError("must not contain spaces")
        return value

    model_config = ConfigDict(extra="forbid", frozen=True)


class LineItemModel(BaseItemModel):
    """Define a basic line item configuration model.

    Args:
        type: Must be 'line_item' for this model.
        node_id: ID of the core node this line item maps to.
    """

    type: Literal["line_item"] = Field(
        "line_item", description="Discriminator for basic line items."
    )
    node_id: str = Field(..., description="ID of the core node this line item maps to.")

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

    @field_validator("id", mode="before")
    def id_must_not_contain_spaces(cls, value: str) -> str:
        """Ensure that statement 'id' does not contain spaces."""
        if " " in value:
            raise ValueError("must not contain spaces")
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
