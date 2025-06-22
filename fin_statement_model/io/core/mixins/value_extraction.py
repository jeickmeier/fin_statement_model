"""Value extraction helpers for writers (split from legacy mixins)."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

import numpy as np

from fin_statement_model.core.graph import Graph
from fin_statement_model.io.core.base import DataWriter

logger = logging.getLogger(__name__)


class ValueExtractionMixin:
    """Shared helper to pull numeric values from graph nodes consistently."""

    def extract_node_value(
        self, node: Any, period: str, *, calculate: bool = True
    ) -> Optional[float]:
        """Extract a numeric value from a graph node for a specific period."""
        try:
            if hasattr(node, "values") and isinstance(node.values, dict):
                val = node.values.get(period)
                if isinstance(val, (int, float)):
                    return float(val)

            # Fall back to expensive calculation only if requested
            if calculate and hasattr(node, "calculate") and callable(node.calculate):
                val = node.calculate(period)
                if isinstance(val, (int, float)):
                    return float(val)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "Failed to extract value from node '%s' period '%s': %s",
                getattr(node, "name", "?"),
                period,
                exc,
            )
            return None


class DataFrameBasedWriter(ValueExtractionMixin, DataWriter, ABC):
    """Base writer that turns graph data into a pandas.DataFrame."""

    def extract_graph_data(
        self,
        graph: Graph,
        *,
        include_nodes: Optional[list[str]] = None,
        calculate: bool = True,
    ) -> dict[str, dict[str, float]]:
        """Extract all node data from a graph into a nested dictionary."""
        periods = sorted(graph.periods) if graph.periods else []
        data: dict[str, dict[str, float]] = {}
        nodes = include_nodes if include_nodes else list(graph.nodes.keys())
        if include_nodes:
            missing = [n for n in include_nodes if n not in graph.nodes]
            if missing:
                logger.warning("Requested nodes not found in graph: %s", missing)
                nodes = [n for n in include_nodes if n in graph.nodes]
        for node_id in nodes:
            node = graph.nodes[node_id]
            row: dict[str, float] = {}
            for period in periods:
                val = self.extract_node_value(node, period, calculate=calculate)
                if val is None or not np.isfinite(val):
                    val = np.nan
                row[period] = float(val)
            data[node_id] = row
        return data

    # concrete writers override --------------------------------------------------
    @abstractmethod
    def write(self, graph: Graph, target: Any = None, **kwargs: Any) -> Any:
        """Write graph data to a target.

        Subclasses must implement the logic to write the graph data to the
        specified target, which could be a file path or an in-memory object.

        Args:
            graph: The `Graph` object to write.
            target: The destination for the write operation.
            **kwargs: Additional format-specific options.

        Returns:
            The result of the write operation, which could be None for file-based
            writers or an object (e.g., a DataFrame) for in-memory writers.
        """
        raise NotImplementedError
