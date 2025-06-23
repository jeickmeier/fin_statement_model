"""Provide models for metric definitions loaded from YAML files.

This module defines Pydantic models for metric definitions and their interpretation guidelines.

Example:
    >>> from fin_statement_model.core.metrics.models import MetricDefinition, MetricInterpretation
    >>> interp = MetricInterpretation(good_range=[1.0, 2.0], warning_below=0.8, notes="Test")
    >>> metric = MetricDefinition(
    ...     name="Test Metric",
    ...     description="A test metric.",
    ...     inputs=["a", "b"],
    ...     formula="a / b",
    ...     tags=["test"],
    ...     units="ratio",
    ...     category="test_category",
    ...     interpretation=interp,
    ...     related_metrics=["other_metric"],
    ... )
    >>> metric.name
    'Test Metric'
    >>> metric.interpretation.good_range
    [1.0, 2.0]
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MetricInterpretation(BaseModel):
    """Provide interpretation guidelines for a metric.

    Attributes:
        good_range: Optional[list[float]]. Range of values considered good [min, max].
        warning_below: Optional[float]. Value below which a warning should be issued.
        warning_above: Optional[float]. Value above which a warning should be issued.
        excellent_above: Optional[float]. Value above which the metric is considered excellent.
        poor_below: Optional[float]. Value below which the metric is considered poor.
        notes: Optional[str]. Additional interpretation notes and context.

    Example:
        >>> interp = MetricInterpretation(good_range=[1.0, 2.0], warning_below=0.8, notes="Test")
        >>> interp.good_range
        [1.0, 2.0]
        >>> interp.warning_below
        0.8
    """

    good_range: list[float] | None = Field(None, description="Range of values considered good [min, max]")
    warning_below: float | None = Field(None, description="Value below which a warning should be issued")
    warning_above: float | None = Field(None, description="Value above which a warning should be issued")
    excellent_above: float | None = Field(None, description="Value above which the metric is considered excellent")
    poor_below: float | None = Field(None, description="Value below which the metric is considered poor")
    notes: str | None = Field(None, description="Additional interpretation notes and context")


class MetricDefinition(BaseModel):
    """Define schema for a single metric definition loaded from a YAML file.

    Attributes:
        name: str. The name of the metric.
        description: str. The description of the metric.
        inputs: list[str]. List of input identifiers for the metric.
        formula: str. The formula used to calculate the metric.
        tags: list[str]. List of tags classifying the metric.
        units: Optional[str]. Unit of the metric (e.g., percentage, ratio).
        category: Optional[str]. Category of the metric.
        interpretation: Optional[MetricInterpretation]. Guidelines for interpreting metric values.
        related_metrics: Optional[list[str]]. Names of related metrics to consider together.

    Example:
        >>> interp = MetricInterpretation(good_range=[1.0, 2.0], warning_below=0.8)
        >>> metric = MetricDefinition(
        ...     name="Test Metric",
        ...     description="A test metric.",
        ...     inputs=["a", "b"],
        ...     formula="a / b",
        ...     tags=["test"],
        ...     units="ratio",
        ...     category="test_category",
        ...     interpretation=interp,
        ...     related_metrics=["other_metric"],
        ... )
        >>> metric.name
        'Test Metric'
        >>> metric.interpretation.good_range
        [1.0, 2.0]
    """

    name: str = Field(..., min_length=1, description="The name of the metric")
    description: str = Field(..., min_length=1, max_length=500, description="The description of the metric")
    inputs: list[str] = Field(..., min_length=1, description="The inputs of the metric")
    formula: str = Field(..., min_length=1, description="The formula of the metric")
    tags: list[str] = Field(default_factory=list, description="The tags of the metric")
    units: str | None = Field(None, description="The units of the metric")
    category: str | None = Field(None, description="Category of the metric (e.g., liquidity, profitability)")
    interpretation: MetricInterpretation | None = Field(
        None, description="Guidelines for interpreting the metric values"
    )
    related_metrics: list[str] | None = Field(
        None, description="Names of related metrics that should be considered together"
    )

    model_config = ConfigDict(extra="forbid", frozen=False)

    @model_validator(mode="before")
    @classmethod
    def _strip_whitespace(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Strip whitespace from all string fields in the metric definition.

        Args:
            values: Dictionary of field values.

        Returns:
            Dictionary with whitespace-stripped string values.

        Example:
            >>> MetricDefinition._strip_whitespace({"name": " Test ", "description": " Desc "})
            {'name': 'Test', 'description': 'Desc'}
        """
        # tiny quality-of-life clean-up
        for k, v in values.items():
            if isinstance(v, str):
                values[k] = v.strip()
        return values
