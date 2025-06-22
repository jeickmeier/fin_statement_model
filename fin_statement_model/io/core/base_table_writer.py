"""Common helpers for writers that export Graphs as tables.

BaseTableWriter builds on DataFrameBasedWriter and provides utility methods
`to_dataframe` and `to_dict`, removing duplicate logic from concrete writer
implementations (ExcelWriter, DictWriter, etc.).
"""

from __future__ import annotations

from typing import Optional, Any
import pandas as pd

from fin_statement_model.io.core.mixins import DataFrameBasedWriter
from fin_statement_model.core.graph import Graph


class BaseTableWriter(DataFrameBasedWriter):
    """Utility mixin supplying Graph→DataFrame / dict conversions."""

    # ------------------------------------------------------------------
    # Reusable helpers used by concrete writers
    # ------------------------------------------------------------------
    def to_dataframe(
        self,
        graph: Graph,
        *,
        include_nodes: Optional[list[str]] = None,
        recalc: bool = False,
    ) -> pd.DataFrame:
        """Return a pandas DataFrame representation of *graph*."""
        if recalc and graph.periods:
            graph.recalculate_all(periods=graph.periods)
        data = self.extract_graph_data(
            graph, include_nodes=include_nodes, calculate=True
        )
        periods_sorted = sorted(graph.periods) if graph.periods else []
        return pd.DataFrame.from_dict(data, orient="index", columns=periods_sorted)

    def to_dict(
        self,
        graph: Graph,
        *,
        include_nodes: Optional[list[str]] = None,
        recalc: bool = False,
    ) -> dict[str, dict[str, float]]:
        """Return a nested dict representation of *graph*."""
        if recalc and graph.periods:
            graph.recalculate_all(periods=graph.periods)
        return self.extract_graph_data(
            graph, include_nodes=include_nodes, calculate=True
        )

    # ------------------------------------------------------------------
    # Param-resolution helper shared by all writers
    # ------------------------------------------------------------------
    @staticmethod
    def _param(
        name: str,
        overrides: dict[str, Any],
        cfg: Any | None,
        *,
        default: Any = None,
    ) -> Any:  # noqa: D401
        """Return effective value for *name* with precedence: overrides → cfg → default."""
        if name in overrides:
            return overrides[name]
        if cfg is not None and hasattr(cfg, name):
            return getattr(cfg, name)
        return default


__all__ = ["BaseTableWriter"]
