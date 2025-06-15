from __future__ import annotations

from typing import Any, Optional, Set
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from fin_statement_model.core.adjustments.models import (
    DEFAULT_SCENARIO,
    Adjustment,
    AdjustmentTag,
    AdjustmentType,
)


class AdjustmentRowModel(BaseModel):
    """Model for validating a single adjustment row from Excel."""

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
                raise ValueError(f"Invalid AdjustmentType: {v}")  # noqa: B904
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
            raise ValueError(f"Invalid UUID for id: {v}")  # noqa: B904

    def to_adjustment(self) -> Adjustment:
        """
        Convert this row model into the core Adjustment model.
        """
        data = self.model_dump()
        # Remove None values to allow core model defaults
        filtered = {k: v for k, v in data.items() if v is not None}
        return Adjustment(**filtered)
