"""Data writer for Python dictionaries."""

import logging
from typing import Any

from fin_statement_model.core.graph import Graph
from fin_statement_model.io.core.mixins import ConfigurationMixin
from fin_statement_model.io.core.base_table_writer import BaseTableWriter
from fin_statement_model.io.core.registry import register_writer
from fin_statement_model.io.config.models import DictWriterConfig

logger = logging.getLogger(__name__)


@register_writer("dict", schema=DictWriterConfig)  # type: ignore[arg-type]
class DictWriter(BaseTableWriter, ConfigurationMixin):
    """Writes graph data to a Python dictionary.

    Extracts values for each node and period in the graph, attempting to
    calculate values where possible.

    Initialized via `DictWriterConfig` (typically by the `write_data` facade),
    although the config currently has no options.
    """

    def __init__(self, cfg: DictWriterConfig) -> None:
        """Initialize the DictWriter.

        Args:
            cfg: Validated `DictWriterConfig` instance.
        """
        super().__init__()
        self.cfg = cfg

    def write(
        self, graph: Graph, target: Any = None, **kwargs: Any
    ) -> dict[str, dict[str, float]]:  # noqa: D401
        """Return dict representation of *graph* (target ignored)."""
        recalc = kwargs.get("recalculate", True)
        include_nodes = kwargs.get("include_nodes")
        logger.info("Exporting graph to dict format.")
        return self.to_dict(graph, include_nodes=include_nodes, recalc=recalc)
