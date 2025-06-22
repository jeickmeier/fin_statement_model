"""Data writer for pandas DataFrames."""

import logging
from typing import Any

import pandas as pd

from fin_statement_model.core.graph import Graph
from fin_statement_model.io.core.mixins import (
    ConfigurationMixin,
    handle_write_errors,
)
from fin_statement_model.io.core.base_table_writer import BaseTableWriter
from fin_statement_model.io.core.registry import register_writer
from fin_statement_model.io.config.models import DataFrameWriterConfig

logger = logging.getLogger(__name__)


@register_writer("dataframe", schema=DataFrameWriterConfig)
class DataFrameWriter(BaseTableWriter, ConfigurationMixin):
    """Writes graph data to a pandas DataFrame.

    Converts the graph to a DataFrame with node names as index and periods as columns.

    Configuration options `recalculate` and `include_nodes` are controlled by
    the `DataFrameWriterConfig` object passed during initialization.
    """

    def __init__(self, cfg: DataFrameWriterConfig) -> None:
        """Initialize the DataFrameWriter.

        Args:
            cfg: Optional validated `DataFrameWriterConfig` instance.
        """
        super().__init__()
        self.cfg = cfg

    @handle_write_errors()
    def write(self, graph: Graph, target: Any = None, **kwargs: Any) -> pd.DataFrame:
        """Return a pandas DataFrame representing *graph*.

        The heavy lifting is performed by :py:meth:`BaseTableWriter.to_dataframe`.
        This wrapper only resolves runtime overrides and logs summary statistics.
        """
        recalculate = self._param("recalculate", kwargs, self.cfg, default=True)
        include_nodes = self._param("include_nodes", kwargs, self.cfg)

        logger.info("Exporting graph to DataFrame format.")

        df = self.to_dataframe(
            graph,
            include_nodes=include_nodes,
            recalc=recalculate,
        )

        logger.info("Successfully exported %s nodes to DataFrame.", len(df))
        return df
