"""Data writer for Python dictionaries."""

import logging
from typing import Any, Optional
import numpy as np

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.errors import CalculationError

# Remove specific node import, we handle all nodes now
# from fin_statement_model.core.nodes import FinancialStatementItemNode
from fin_statement_model.io.base import DataWriter
from fin_statement_model.io.registry import register_writer
from fin_statement_model.io.exceptions import WriteError
from fin_statement_model.io.config.models import DictWriterConfig

logger = logging.getLogger(__name__)


@register_writer("dict")
class DictWriter(DataWriter):
    """Writes graph data to a Python dictionary.

    Calculates the value for each node and period in the graph using
    `graph.calculate()` before exporting.

    Initialized via `DictWriterConfig` (typically by the `write_data` facade),
    although the config currently has no options. The `.write()` method takes no
    specific keyword arguments.
    """

    def __init__(self, cfg: Optional[DictWriterConfig] = None) -> None:
        """Initialize the DictWriter.

        Args:
            cfg: Optional validated `DictWriterConfig` instance.
                 Currently unused but kept for registry symmetry.
        """
        self.cfg = cfg

    def write(
        self, graph: Graph, target: Any = None, **kwargs: dict[str, Any]
    ) -> dict[str, dict[str, float]]:
        """Export calculated data from all graph nodes to a dictionary.

        Args:
            graph (Graph): The Graph instance to export data from. It's recommended
                           to ensure the graph is calculated beforehand if needed,
                           as this writer calculates values per node/period.
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
        result: dict[str, dict[str, float]] = {}
        periods = sorted(graph.periods) if graph.periods else []
        if not periods:
            logger.warning("Graph has no periods defined. Exported dictionary will be empty.")
            return {}

        try:
            for node_id in graph.nodes:
                node_values: dict[str, float] = {}
                for period in periods:
                    value = np.nan
                    try:
                        # Use graph.calculate to get the value for the specific node and period
                        calculated_value = graph.calculate(node_id, period=period)
                        if isinstance(calculated_value, int | float | np.number) and np.isfinite(
                            calculated_value
                        ):
                            value = float(calculated_value)
                        else:
                            # Handle cases where calculation returns non-numeric or infinite results
                            logger.debug(
                                f"Calculation for node '{node_id}' period '{period}' "
                                f"yielded non-finite/non-numeric result: {calculated_value}. Using NaN."
                            )
                    except CalculationError as calc_err:
                        logger.debug(
                            f"Calculation failed for node '{node_id}' period '{period}': {calc_err}. Using NaN."
                        )
                    except Exception as e:
                        # Catch unexpected errors during calculation for a specific period
                        logger.warning(
                            f"Unexpected error calculating node '{node_id}' period '{period}': {e}. Using NaN.",
                            exc_info=True,
                        )
                    node_values[period] = value
                result[node_id] = node_values

            logger.info(f"Successfully exported {len(result)} nodes to dictionary.")
        except Exception as e:
            # Catch errors during the overall export process (e.g., iterating nodes)
            logger.error(f"Failed to export graph to dictionary: {e}", exc_info=True)
            raise WriteError(
                message=f"Failed to export graph to dictionary: {e}",
                target="dict",
                writer_type="DictWriter",
                original_error=e,
            ) from e
        else:
            return result
