"""Data writer for exporting graph data to a Python dictionary.

This module provides the `DictWriter`, a `DataWriter` implementation that
serializes a `Graph` object into an in-memory Python dictionary. The resulting
dictionary follows the format: `{node_name: {period: value, ...}, ...}`.
"""

import logging
from typing import Any

from fin_statement_model.core.graph import Graph
from fin_statement_model.io.config.models import DictWriterConfig
from fin_statement_model.io.core.base_table_writer import BaseTableWriter
from fin_statement_model.io.core.mixins import ConfigurationMixin
from fin_statement_model.io.core.registry import register_writer

logger = logging.getLogger(__name__)


@register_writer("dict", schema=DictWriterConfig)
class DictWriter(BaseTableWriter, ConfigurationMixin):
    """Writes graph data to a Python dictionary.

    This writer converts a `Graph` object into a nested Python dictionary.
    The top-level keys are the node names, and the values are dictionaries
    mapping period names to numeric values.

    This format is useful for simple, in-memory serialization of the graph's data.
    The writer's behavior can be influenced by a `DictWriterConfig` object.
    """

    def __init__(self, cfg: DictWriterConfig) -> None:
        """Initialize the DictWriter.

        Args:
            cfg: Validated `DictWriterConfig` instance.
        """
        super().__init__()
        self.cfg = cfg

    def write(self, graph: Graph, target: Any = None, **kwargs: Any) -> dict[str, dict[str, float]]:
        """Convert a `Graph` object into a nested dictionary.

        This method orchestrates the conversion of the graph data into a dictionary.
        It uses the `to_dict` method inherited from `BaseTableWriter` to perform
        the data extraction.

        Runtime options like `recalculate` and `include_nodes` can be passed as
        keyword arguments to override the writer's initial configuration.

        Args:
            graph: The `Graph` object to be written.
            target: This argument is ignored by the `DictWriter`.
            **kwargs: Optional runtime overrides for configuration settings.

        Returns:
            A nested dictionary representing the graph's data.
        """
        _ = target  # Parameter intentionally unused
        recalc = kwargs.get("recalculate", True)
        include_nodes = kwargs.get("include_nodes")
        logger.info("Exporting graph to dict format.")
        return self.to_dict(graph, include_nodes=include_nodes, recalc=recalc)
