"""Data writer for pandas DataFrames."""

import logging
from typing import Optional, Any

import pandas as pd

from fin_statement_model.core.graph import Graph
from fin_statement_model.io.core.mixins import (
    DataFrameBasedWriter,
    ConfigurableReaderMixin,
    handle_write_errors,
)
from fin_statement_model.io.core.registry import register_writer
from fin_statement_model.io.config.models import DataFrameWriterConfig

logger = logging.getLogger(__name__)


@register_writer("dataframe")
class DataFrameWriter(DataFrameBasedWriter, ConfigurableReaderMixin):
    """Writes graph data to a pandas DataFrame.

    Converts the graph to a DataFrame with node names as index and periods as columns.

    Configuration options `recalculate` and `include_nodes` are controlled by
    the `DataFrameWriterConfig` object passed during initialization.
    """

    def __init__(self, cfg: Optional[DataFrameWriterConfig] = None) -> None:
        """Initialize the DataFrameWriter.

        Args:
            cfg: Optional validated `DataFrameWriterConfig` instance.
        """
        self.cfg = cfg

    @handle_write_errors()
    def write(
        self, graph: Graph, target: Any = None, **kwargs: dict[str, object]
    ) -> pd.DataFrame:
        """Convert the graph data to a pandas DataFrame based on instance configuration.

        Args:
            graph (Graph): The Graph instance to export.
            target (Any): Ignored by this writer; the DataFrame is returned directly.
            **kwargs: Currently unused by this method.

        Returns:
            pd.DataFrame: DataFrame with node names as index and periods as columns.

        Raises:
            WriteError: If an error occurs during conversion.
        """
        # Get configuration values using the mixin
        recalculate = self.get_config_value("recalculate", True)
        include_nodes = self.get_config_value("include_nodes")

        logger.info("Exporting graph to DataFrame format.")

        # Handle recalculation if requested
        if recalculate:
            self._recalculate_graph(graph)

        # Extract data using base class method
        data = self.extract_graph_data(
            graph, include_nodes=include_nodes, calculate=True
        )

        # Convert to DataFrame
        periods = sorted(graph.periods) if graph.periods else []
        df = pd.DataFrame.from_dict(data, orient="index", columns=periods)
        df.index.name = "node_name"

        logger.info(f"Successfully exported {len(df)} nodes to DataFrame.")
        return df

    def _recalculate_graph(self, graph: Graph) -> None:
        """Recalculate the graph if it has periods defined.

        Args:
            graph: The graph to recalculate.
        """
        try:
            if graph.periods:
                graph.recalculate_all(periods=graph.periods)
                logger.info("Recalculated graph before exporting to DataFrame.")
            else:
                logger.warning("Graph has no periods defined, skipping recalculation.")
        except Exception as e:
            logger.error(
                f"Error during recalculation for DataFrame export: {e}",
                exc_info=True,
            )
            logger.warning(
                "Proceeding to export DataFrame without successful recalculation."
            )
