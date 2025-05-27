"""Models for metric definitions."""

from typing import Optional, Any
from pydantic import BaseModel, Field, model_validator
from pydantic import ConfigDict


class MetricInterpretation(BaseModel):
    """Interpretation guidelines for a metric."""

    good_range: Optional[list[float]] = Field(
        None, description="Range of values considered good [min, max]"
    )
    warning_below: Optional[float] = Field(
        None, description="Value below which a warning should be issued"
    )
    warning_above: Optional[float] = Field(
        None, description="Value above which a warning should be issued"
    )
    excellent_above: Optional[float] = Field(
        None, description="Value above which the metric is considered excellent"
    )
    poor_below: Optional[float] = Field(
        None, description="Value below which the metric is considered poor"
    )
    notes: Optional[str] = Field(None, description="Additional interpretation notes and context")


class MetricDefinition(BaseModel):
    """Schema for one metric definition loaded from YAML."""

    name: str = Field(..., min_length=1, description="The name of the metric")
    description: str = Field(
        ..., min_length=1, max_length=500, description="The description of the metric"
    )
    inputs: list[str] = Field(..., min_length=1, description="The inputs of the metric")
    formula: str = Field(..., min_length=1, description="The formula of the metric")
    tags: list[str] = Field(default_factory=list, description="The tags of the metric")
    units: Optional[str] = Field(None, description="The units of the metric")
    category: Optional[str] = Field(
        None, description="Category of the metric (e.g., liquidity, profitability)"
    )
    interpretation: Optional[MetricInterpretation] = Field(
        None, description="Guidelines for interpreting the metric values"
    )
    related_metrics: Optional[list[str]] = Field(
        None, description="Names of related metrics that should be considered together"
    )

    model_config = ConfigDict(extra="forbid", frozen=False)

    @model_validator(mode="before")
    def _strip_whitespace(cls, values: dict[str, Any]) -> dict[str, Any]:
        # tiny quality-of-life clean-up
        for k, v in values.items():
            if isinstance(v, str):
                values[k] = v.strip()
        return values
