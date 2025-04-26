"""Data writer for Python dictionaries."""

import logging
from typing import Any

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import (
    FinancialStatementItemNode,
)  # Import specific node if needed
from fin_statement_model.io.base import DataWriter
from fin_statement_model.io.registry import register_writer
from fin_statement_model.io.exceptions import WriteError

logger = logging.getLogger(__name__)


@register_writer("dict")
class DictWriter(DataWriter):
    """Writes graph data to a Python dictionary.

    Specifically extracts data from FinancialStatementItemNode instances.

    Note:
        When using the `write_data` facade, writer initialization has no specific kwargs,
        and no writer-specific options are supported for DictWriter. Direct instantiation
        of `DictWriter` is also supported.
    """

    def write(
        self, graph: Graph, target: object = None, **kwargs: dict[str, Any]
    ) -> dict[str, dict[str, float]]:
        """Export data from graph nodes with values to a dictionary.

        Args:
            graph (Graph): The Graph instance to export data from.
            target (object): Ignored for DictWriter; returns the dictionary directly.
            **kwargs: Writer-specific keyword arguments (none supported by DictWriter).

        Returns:
            Dict[str, Dict[str, float]]: Mapping node names to period-value dicts.
                                         Only includes FinancialStatementItemNode instances
                                         with a 'values' attribute.

        Raises:
            WriteError: If an unexpected error occurs during export.
        """
        logger.info(f"Starting export of graph '{graph}' to dictionary format.")
        result: dict[str, dict[str, float]] = {}
        try:
            for node_id, node in graph.nodes.items():
                # Check if the node is a FinancialStatementItemNode and has 'values'
                # This makes the export specific to data-holding nodes.
                if (
                    isinstance(node, FinancialStatementItemNode)
                    and hasattr(node, "values")
                    and isinstance(node.values, dict)
                ):
                    # Validate and copy values
                    # Ensure values are {str: float | int}
                    validated_values = {
                        str(k): float(v)
                        for k, v in node.values.items()
                        if isinstance(k, str) and isinstance(v, (int, float))
                    }
                    if validated_values:
                        result[node_id] = validated_values
                    else:
                        logger.debug(
                            f"Node '{node_id}' has no valid period-value data to export. Skipping."
                        )
                # else: Not an FSI node or no valid values, skip

            logger.info(f"Successfully exported {len(result)} nodes to dictionary.")
        except Exception as e:
            logger.error(f"Failed to export graph to dictionary: {e}", exc_info=True)
            raise WriteError(
                message="Failed to export graph to dictionary",
                target="dict",
                writer_type="DictWriter",
                original_error=e,
            ) from e
        else:
            return result
