"""Metrics mixin module for FinancialStatementGraph operations."""

from typing import Optional


class MetricsOperationsMixin:
    """Mixin providing metric operations for FinancialStatementGraph.

    - add_metric.
    """

    def add_metric(self, metric_name: str, node_name: Optional[str] = None):
        """Add a financial metric calculation node to the graph.

        Args:
            metric_name: The name of the metric from METRIC_DEFINITIONS
            node_name: Optional custom name for the node (defaults to metric_name)
        """
        self._calculation_engine.add_metric(metric_name, node_name)
