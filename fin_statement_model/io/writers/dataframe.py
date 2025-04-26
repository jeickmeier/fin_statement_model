"""Data writer for pandas DataFrames."""

import logging
from typing import Optional, Any

import pandas as pd
import numpy as np

from fin_statement_model.core.graph import Graph
from fin_statement_model.io.base import DataWriter
from fin_statement_model.io.registry import register_writer
from fin_statement_model.io.exceptions import WriteError
from fin_statement_model.io.config.models import DataFrameWriterConfig

logger = logging.getLogger(__name__)


@register_writer("dataframe")
class DataFrameWriter(DataWriter):
    """Writes graph data to a pandas DataFrame.

    Converts the graph to a DataFrame with node names as index and periods as columns.

    Configuration options `recalculate` and `include_nodes` are controlled *exclusively*
    by the `DataFrameWriterConfig` object passed during initialization (typically
    via the `write_data` facade). The `.write()` method does not accept keyword
    arguments to override these settings.
    """

    def __init__(self, cfg: Optional[DataFrameWriterConfig] = None) -> None:
        """Initialize the DataFrameWriter.

        Args:
            cfg: Optional validated `DataFrameWriterConfig` instance.
        """
        self.cfg = cfg

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
            AssertionError: If the writer was not initialized with a configuration.
        """
        assert self.cfg is not None, "DataFrameWriter must be initialized with a valid configuration."
        # Use configuration directly from self.cfg
        recalculate = self.cfg.recalculate
        include_nodes = self.cfg.include_nodes

        logger.info("Exporting graph to DataFrame format.")

        try:
            if recalculate:
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

            periods = sorted(graph.periods) if graph.periods else []
            data: dict[str, dict[str, float]] = {}

            nodes_to_process = include_nodes if include_nodes else graph.nodes.keys()
            if include_nodes:
                missing_nodes = [n for n in include_nodes if n not in graph.nodes]
                if missing_nodes:
                    logger.warning(
                        f"Nodes specified in include_nodes not found in graph: {missing_nodes}"
                    )
                nodes_to_process = [n for n in include_nodes if n in graph.nodes]

            for node_id in nodes_to_process:
                node = graph.nodes[node_id]
                row: dict[str, float] = {}
                for period in periods:
                    value = np.nan
                    try:
                        if hasattr(node, "calculate") and callable(node.calculate):
                            value = node.calculate(period)
                        elif (
                            hasattr(node, "values")
                            and isinstance(node.values, dict)
                            and period in node.values
                        ):
                            value = node.values.get(period, np.nan)

                        if not isinstance(value, (int, float, np.number)) or not np.isfinite(value):
                            value = np.nan
                    except Exception as e:
                        logger.debug(
                            f"Could not get value for node '{node_id}' period '{period}' for DataFrame export: {e}"
                        )
                        value = np.nan
                    row[period] = float(value)
                data[node_id] = row

            df = pd.DataFrame.from_dict(data, orient="index", columns=periods)
            df.index.name = "node_name"

            logger.info(f"Successfully exported {len(df)} nodes to DataFrame.")
        except Exception as e:
            logger.error(f"Failed to export graph to DataFrame: {e}", exc_info=True)
            raise WriteError(
                message=f"Failed to export graph to DataFrame: {e}",
                target="DataFrame",
                writer_type="DataFrameWriter",
                original_error=e,
            ) from e
        else:
            return df
