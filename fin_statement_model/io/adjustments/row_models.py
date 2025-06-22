"""Pydantic model for validating and parsing a single row from an adjustments Excel file.

This module defines the `AdjustmentRowModel`, which is used by the Excel IO
functionality to validate the structure and data types of each row read from
an adjustments file. It uses Pydantic validators to handle type coercion and
enforce constraints, converting raw input into a validated object that can then
be transformed into the core `Adjustment` model.
"""

from __future__ import annotations

from uuid import UUID
from typing import Any, Optional, Set

from pydantic import BaseModel, ConfigDict, Field, field_validator

from fin_statement_model.core.adjustments.models import (
    Adjustment,
    AdjustmentType,
    AdjustmentTag,
    DEFAULT_SCENARIO,
)


class AdjustmentRowModel(BaseModel):
    """A Pydantic model for validating a single row from an adjustments spreadsheet.

    This class defines the expected structure of a row when importing adjustments.
    It includes fields for all required and optional `Adjustment` attributes,
    and uses validators to parse and clean the raw input data (e.g., converting
    a comma-separated string of tags into a set).

    Attributes:
        node_name: The name of the target node for the adjustment.
        period: The target period for the adjustment.
        value: The numeric value of the adjustment.
        reason: A textual description of the reason for the adjustment.
        type: The type of adjustment (e.g., 'additive', 'multiplicative').
        tags: A set of tags for categorizing the adjustment.
        scale: A scaling factor for the adjustment (0.0 to 1.0).
        scenario: The scenario this adjustment belongs to.
        start_period: The first period the adjustment is active.
        end_period: The last period the adjustment is active.
        priority: The priority level of the adjustment.
        user: The user who created the adjustment.
        id: A unique identifier for the adjustment.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    # Required fields
    node_name: str
    period: str
    value: float
    reason: str

    # Optional or derived fields
    type: AdjustmentType = AdjustmentType.ADDITIVE
    tags: Set[AdjustmentTag] = Field(default_factory=set)
    scale: float = 1.0
    scenario: str = DEFAULT_SCENARIO
    start_period: Optional[str] = None
    end_period: Optional[str] = None
    priority: int = 0
    user: Optional[str] = None
    id: Optional[UUID] = None

    @field_validator("type", mode="before")
    @classmethod
    def _validate_type(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return AdjustmentType(v.lower())
            except ValueError:
                raise ValueError(f"Invalid AdjustmentType: {v}")
        return v

    @field_validator("tags", mode="before")
    @classmethod
    def _parse_tags(cls, v: Any) -> Set[AdjustmentTag]:
        if not v:
            return set()
        if isinstance(v, str):
            return {tag.strip() for tag in v.split(",") if tag.strip()}
        if isinstance(v, (list, set)):
            return set(v)
        raise ValueError(f"Invalid tags format: {v}")

    @field_validator("scale")
    @classmethod
    def _validate_scale(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("Scale must be between 0.0 and 1.0")
        return v

    @field_validator("id", mode="before")
    @classmethod
    def _parse_id(cls, v: Any) -> Optional[UUID]:
        if v is None or v == "":
            return None
        if isinstance(v, UUID):
            return v
        try:
            return UUID(str(v))
        except Exception:
            raise ValueError(f"Invalid UUID for id: {v}")

    def to_adjustment(self) -> Adjustment:
        """Convert this row model into the core `Adjustment` model.

        This method transforms the validated row data into an `Adjustment` object,
        which is the canonical representation used throughout the financial model.
        It handles the conversion by dumping the model's data and instantiating
        an `Adjustment` with it. Fields with `None` values are excluded to allow
        the `Adjustment` model's default values to be applied.

        Returns:
            An `Adjustment` instance corresponding to the data in this row model.
        """
        data = self.model_dump()
        # Remove None values to allow core model defaults
        filtered = {k: v for k, v in data.items() if v is not None}
        return Adjustment(**filtered)
