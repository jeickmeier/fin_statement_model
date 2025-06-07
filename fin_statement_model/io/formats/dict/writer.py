"""Data writer for Python dictionaries."""

import logging
from typing import Any, Optional

from fin_statement_model.core.graph import Graph
from fin_statement_model.io.core.mixins import (
    DataFrameBasedWriter,
    ConfigurableReaderMixin,
    handle_write_errors,
)
from fin_statement_model.io.core.registry import register_writer
from fin_statement_model.io.config.models import DictWriterConfig

logger = logging.getLogger(__name__)


@register_writer("dict")
class DictWriter(DataFrameBasedWriter, ConfigurableReaderMixin):
    """Writes graph data to a Python dictionary.

    Extracts values for each node and period in the graph, attempting to
    calculate values where possible.

    Initialized via `DictWriterConfig` (typically by the `write_data` facade),
    although the config currently has no options.
    """

    def __init__(self, cfg: Optional[DictWriterConfig] = None) -> None:
        """Initialize the DictWriter.

        Args:
            cfg: Optional validated `DictWriterConfig` instance.
                 Currently unused but kept for registry symmetry.
        """
        super().__init__()
        self.cfg = cfg

    @handle_write_errors()
    def write(
        self, graph: Graph, target: Any = None, **kwargs: dict[str, Any]
    ) -> dict[str, dict[str, float]]:
        """Export calculated data from all graph nodes to a dictionary.

        Args:
            graph (Graph): The Graph instance to export data from.
            target (Any): Ignored by this writer; the dictionary is returned directly.
            **kwargs: Currently unused.

        Returns:
            Dict[str, Dict[str, float]]: Mapping node names to period-value dicts.
                                         Includes values for all nodes in the graph
                                         for all defined periods. NaN represents
                                         uncalculable values.

        Raises:
            WriteError: If an unexpected error occurs during export.
        """
        logger.info(f"Starting export of graph '{graph}' to dictionary format.")

        if not graph.periods:
            logger.warning(
                "Graph has no periods defined. Exported dictionary will be empty."
            )
            return {}

        # Use base class method to extract all data
        # This handles calculation attempts and error handling consistently
        result = self.extract_graph_data(graph, include_nodes=None, calculate=True)

        logger.info(f"Successfully exported {len(result)} nodes to dictionary.")
        return result
