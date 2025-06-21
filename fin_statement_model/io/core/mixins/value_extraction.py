"""Value extraction helpers for writers (split from legacy mixins)."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

import numpy as np

from fin_statement_model.core.graph import Graph

logger = logging.getLogger(__name__)


class ValueExtractionMixin:
    """Shared helper to pull numeric values from graph nodes consistently."""

    def extract_node_value(
        self, node: Any, period: str, *, calculate: bool = True
    ) -> Optional[float]:  # noqa: D401
        try:
            if calculate and hasattr(node, "calculate") and callable(node.calculate):
                val = node.calculate(period)
                if isinstance(val, (int, float)):
                    return float(val)
            if hasattr(node, "values") and isinstance(node.values, dict):
                val = node.values.get(period)
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


class DataFrameBasedWriter(ValueExtractionMixin, ABC):
    """Base writer that turns graph data into a pandas.DataFrame."""

    def extract_graph_data(
        self,
        graph: Graph,
        *,
        include_nodes: Optional[list[str]] = None,
        calculate: bool = True,
    ) -> dict[str, dict[str, float]]:  # noqa: D401
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
    def write(
        self, graph: Graph, target: Any = None, **kwargs: Any
    ) -> Any:  # noqa: D401
        """Write graph data to *target* – must be implemented by subclasses."""
