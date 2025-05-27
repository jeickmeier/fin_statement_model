"""Utilities for interpreting metric values based on defined guidelines."""

from enum import Enum
from typing import Any
from fin_statement_model.core.metrics.models import (
    MetricDefinition,
)


class MetricRating(Enum):
    """Rating levels for metric values."""

    EXCELLENT = "excellent"
    GOOD = "good"
    ADEQUATE = "adequate"
    WARNING = "warning"
    POOR = "poor"
    UNKNOWN = "unknown"


class MetricInterpreter:
    """Interprets metric values based on defined guidelines."""

    def __init__(self, metric_definition: MetricDefinition):
        """Initialize with a metric definition.

        Args:
            metric_definition: The metric definition containing interpretation guidelines.
        """
        self.metric_definition = metric_definition
        self.interpretation = metric_definition.interpretation

    def rate_value(self, value: float) -> MetricRating:
        """Rate a metric value based on interpretation guidelines.

        Args:
            value: The metric value to rate.

        Returns:
            MetricRating indicating the quality of the value.
        """
        if not self.interpretation:
            return MetricRating.UNKNOWN

        # Check for excellent rating
        if (
            self.interpretation.excellent_above is not None
            and value >= self.interpretation.excellent_above
        ):
            return MetricRating.EXCELLENT

        # Check for poor rating
        if self.interpretation.poor_below is not None and value < self.interpretation.poor_below:
            return MetricRating.POOR

        # Check for warning conditions
        warning_conditions = []
        if (
            self.interpretation.warning_below is not None
            and value < self.interpretation.warning_below
        ):
            warning_conditions.append("below_threshold")

        if (
            self.interpretation.warning_above is not None
            and value > self.interpretation.warning_above
        ):
            warning_conditions.append("above_threshold")

        if warning_conditions:
            return MetricRating.WARNING

        # Check if in good range
        if self.interpretation.good_range is not None and len(self.interpretation.good_range) == 2:
            min_good, max_good = self.interpretation.good_range
            if min_good <= value <= max_good:
                return MetricRating.GOOD

        # Default to adequate if no specific conditions met
        return MetricRating.ADEQUATE

    def get_interpretation_message(self, value: float) -> str:
        """Get a human-readable interpretation message for a metric value.

        Args:
            value: The metric value to interpret.

        Returns:
            A descriptive message about the metric value.
        """
        rating = self.rate_value(value)

        # Base message based on rating
        rating_messages = {
            MetricRating.EXCELLENT: f"Excellent performance: {value:.2f}",
            MetricRating.GOOD: f"Good performance: {value:.2f}",
            MetricRating.ADEQUATE: f"Adequate performance: {value:.2f}",
            MetricRating.WARNING: f"Warning level: {value:.2f}",
            MetricRating.POOR: f"Poor performance: {value:.2f}",
            MetricRating.UNKNOWN: f"Value: {value:.2f} (no interpretation guidelines available)",
        }

        return rating_messages[rating]

    def get_detailed_analysis(self, value: float) -> dict[str, Any]:
        """Get a detailed analysis of a metric value.

        Args:
            value: The metric value to analyze.

        Returns:
            Dictionary containing detailed analysis information.
        """
        rating = self.rate_value(value)

        analysis: dict[str, Any] = {
            "value": value,
            "rating": rating.value,
            "metric_name": self.metric_definition.name,
            "units": self.metric_definition.units,
            "category": self.metric_definition.category,
            "interpretation_message": self.get_interpretation_message(value),
        }

        # Add interpretation details if available
        if self.interpretation:
            analysis["guidelines"] = {
                "good_range": self.interpretation.good_range,
                "warning_below": self.interpretation.warning_below,
                "warning_above": self.interpretation.warning_above,
                "excellent_above": self.interpretation.excellent_above,
                "poor_below": self.interpretation.poor_below,
            }

            if self.interpretation.notes:
                analysis["notes"] = self.interpretation.notes

        # Add related metrics for context
        if self.metric_definition.related_metrics:
            analysis["related_metrics"] = self.metric_definition.related_metrics

        return analysis


def interpret_metric(metric_definition: MetricDefinition, value: float) -> dict[str, Any]:
    """Convenience function to interpret a metric value.

    Args:
        metric_definition: The metric definition.
        value: The value to interpret.

    Returns:
        Detailed interpretation analysis.
    """
    interpreter = MetricInterpreter(metric_definition)
    return interpreter.get_detailed_analysis(value)
