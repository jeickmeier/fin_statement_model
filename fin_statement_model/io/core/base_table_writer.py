"""Common helpers for writers that export Graphs as tables.

BaseTableWriter builds on DataFrameBasedWriter and provides utility methods
`to_dataframe` and `to_dict`, removing duplicate logic from concrete writer
implementations (ExcelWriter, DictWriter, etc.).
"""

from __future__ import annotations

from typing import Optional
import pandas as pd

from fin_statement_model.io.core.mixins import DataFrameBasedWriter, handle_write_errors
from fin_statement_model.core.graph import Graph


class BaseTableWriter(DataFrameBasedWriter):
    """Utility mixin supplying Graph→DataFrame / dict conversions."""

    # ------------------------------------------------------------------
    # Reusable helpers used by concrete writers
    # ------------------------------------------------------------------
    @handle_write_errors()
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

    @handle_write_errors()
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


__all__ = ["BaseTableWriter"]
