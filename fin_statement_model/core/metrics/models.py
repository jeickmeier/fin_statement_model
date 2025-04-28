"""Models for metric definitions."""

from typing import Optional, Any
from pydantic import BaseModel, Field, model_validator
from pydantic import ConfigDict


class MetricDefinition(BaseModel):
    """Schema for one metric definition loaded from YAML."""

    name: str = Field(..., min_length=1, description="The name of the metric")
    description: str = Field(
        ..., min_length=1, max_length=300, description="The description of the metric"
    )
    inputs: list[str] = Field(..., min_length=1, description="The inputs of the metric")
    formula: str = Field(..., min_length=1, description="The formula of the metric")
    tags: list[str] = Field(default_factory=list, description="The tags of the metric")
    units: Optional[str] = Field(None, description="The units of the metric")

    model_config = ConfigDict(extra="forbid", frozen=False)

    @model_validator(mode="before")
    def _strip_whitespace(cls, values: dict[str, Any]) -> dict[str, Any]:
        # tiny quality-of-life clean-up
        for k, v in values.items():
            if isinstance(v, str):
                values[k] = v.strip()
        return values
