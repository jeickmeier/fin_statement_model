"""Provide models for metric definitions loaded from YAML files.

This module defines Pydantic models for metric definitions and their interpretation guidelines.
"""

from typing import Optional, Any
from pydantic import BaseModel, Field, model_validator
from pydantic import ConfigDict


class MetricInterpretation(BaseModel):
    """Provide interpretation guidelines for a metric.

    Attributes:
        good_range: Range of values considered good [min, max].
        warning_below: Value below which a warning should be issued.
        warning_above: Value above which a warning should be issued.
        excellent_above: Value above which the metric is considered excellent.
        poor_below: Value below which the metric is considered poor.
        notes: Additional interpretation notes and context.
    """

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
    notes: Optional[str] = Field(
        None, description="Additional interpretation notes and context"
    )


class MetricDefinition(BaseModel):
    """Define schema for a single metric definition loaded from a YAML file.

    Attributes:
        name: The name of the metric.
        description: The description of the metric.
        inputs: List of input identifiers for the metric.
        formula: The formula used to calculate the metric.
        tags: List of tags classifying the metric.
        units: Unit of the metric (e.g., percentage, ratio).
        category: Category of the metric.
        interpretation: Guidelines for interpreting metric values.
        related_metrics: Names of related metrics to consider together.
    """

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
