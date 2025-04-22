"""Merge operations mixin module for FinancialStatementGraph.

Provides methods to merge graphs and add metric nodes to the statement graph.
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from fin_statement_model.statements.graph.financial_graph import (
        FinancialStatementGraph,
    )

"""Merge mixin module for FinancialStatementGraph operations."""


class MergeOperationsMixin:
    """Mixin providing merge methods for FinancialStatementGraph.

    - _merge_graph
    - add_metric.
    """

    def _merge_graph(self, other_graph: "FinancialStatementGraph"):
        """Merge another FinancialStatementGraph into this one.

        Args:
            other_graph: Graph to merge into this one
        """
        # Update periods
        for period in other_graph.graph.periods:
            if period not in self.graph.periods:
                self.graph.periods.append(period)
        self.graph.periods.sort()

        # Merge nodes
        for node_name, node in other_graph.graph.nodes.items():
            existing_node = self.graph.get_node(node_name)
            if existing_node is not None:
                # Update existing node with new values
                if hasattr(node, "values"):
                    for period, value in node.values.items():
                        existing_node.values[period] = value  # type: ignore
                self.graph.add_node(existing_node)  # Re-add to update
            else:
                # Add new node
                self.graph.add_node(node)

    def add_metric(self, metric_name: str, node_name: Optional[str] = None):
        """Add a financial metric calculation node to the graph.

        Args:
            metric_name: The name of the metric from METRIC_DEFINITIONS
            node_name: Optional custom name for the node (defaults to metric_name)
        """
        target_node_name = node_name if node_name is not None else metric_name
        self._calculation_engine.add_metric(metric_name, target_node_name)
