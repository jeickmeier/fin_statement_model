"""Data writer for exporting graph data to a pandas DataFrame.

This module provides the `DataFrameWriter`, a `DataWriter` implementation that
serializes a `Graph` object into an in-memory `pandas.DataFrame`. The resulting
DataFrame has node names as its index and periods as its columns.
"""

import logging
from typing import Any

import pandas as pd

from fin_statement_model.core.graph import Graph
from fin_statement_model.io.config.models import DataFrameWriterConfig
from fin_statement_model.io.core.base_table_writer import BaseTableWriter
from fin_statement_model.io.core.mixins import (
    ConfigurationMixin,
    handle_write_errors,
)
from fin_statement_model.io.core.registry import register_writer

logger = logging.getLogger(__name__)


@register_writer("dataframe", schema=DataFrameWriterConfig)
class DataFrameWriter(BaseTableWriter, ConfigurationMixin):
    """Writes graph data to a pandas DataFrame.

    This writer converts a `Graph` object into a `pandas.DataFrame`, which is a
    common format for data analysis in Python. The resulting DataFrame has node
    names as its index and periods as its columns.

    The writer's behavior, such as whether to recalculate the graph before export,
    can be controlled via a `DataFrameWriterConfig` object.
    """

    def __init__(self, cfg: DataFrameWriterConfig) -> None:
        """Initialize the DataFrameWriter.

        Args:
            cfg: A validated `DataFrameWriterConfig` instance.
        """
        super().__init__()
        self.cfg = cfg

    @handle_write_errors()
    def write(self, graph: Graph, target: Any = None, **kwargs: Any) -> pd.DataFrame:
        """Convert a `Graph` object into a pandas DataFrame.

        This method orchestrates the conversion of the graph data into a DataFrame.
        It relies on the `to_dataframe` method inherited from `BaseTableWriter` to
        perform the actual data extraction and DataFrame creation.

        Runtime options like `recalculate` and `include_nodes` can be passed as
        keyword arguments to override the writer's initial configuration.

        Args:
            graph: The `Graph` object to be written.
            target: This argument is ignored by the `DataFrameWriter`.
            **kwargs: Optional runtime overrides for configuration settings.

        Returns:
            A pandas DataFrame representing the graph's data.
        """
        _ = target  # Parameter intentionally unused
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
