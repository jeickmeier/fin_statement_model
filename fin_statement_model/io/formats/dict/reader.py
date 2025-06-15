"""Data reader for Python dictionaries."""

import logging
from typing import Any, Optional

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import FinancialStatementItemNode
from fin_statement_model.io.config.models import DictReaderConfig
from fin_statement_model.io.core.base import DataReader
from fin_statement_model.io.core.registry import register_reader
from fin_statement_model.io.exceptions import ReadError

logger = logging.getLogger(__name__)


@register_reader("dict", schema=DictReaderConfig)
class DictReader(DataReader):
    """Reads data from a Python dictionary to create a new Graph.

    Expects a dictionary format: {node_name: {period: value, ...}, ...}
    Creates FinancialStatementItemNode instances for each entry.

    Note:
        Configuration is handled via `DictReaderConfig` during initialization.
        The `read()` method takes the source dictionary directly and an optional
        `periods` keyword argument.
    """

    def __init__(self, cfg: Optional[DictReaderConfig] = None) -> None:
        """Initialize the DictReader.

        Args:
            cfg: Optional validated `DictReaderConfig` instance.
                 Currently unused but kept for registry symmetry and future options.
        """
        self.cfg = cfg

    def read(self, source: dict[str, dict[str, float]], **kwargs: Any) -> Graph:
        """Create a new Graph from a dictionary.

        Args:
            source: Dictionary mapping node names to period-value dictionaries.
                    Format: {node_name: {period: value, ...}, ...}
            **kwargs: Optional runtime argument overriding config defaults:
                periods (list[str], optional): List of periods to include. Overrides `cfg.periods`.

        Returns:
            A new Graph instance populated with FinancialStatementItemNodes.

        Raises:
            ReadError: If the source data format is invalid or processing fails.
            # DataValidationError: If data values are not numeric.
        """
        logger.info("Starting import from dictionary to create a new graph.")

        if not isinstance(source, dict):
            raise ReadError(
                message="Invalid source type for DictReader. Expected dict.",
                source="dict_input",
                reader_type="DictReader",
            )

        # Validate data structure and collect all periods
        all_periods = set()
        validation_errors: list[str] = []
        try:
            for node_name, period_values in source.items():
                if not isinstance(period_values, dict):
                    validation_errors.append(
                        f"Node '{node_name}': Invalid format - expected dict, got {type(period_values).__name__}"
                    )
                    continue  # Skip further checks for this node
                for period, value in period_values.items():
                    # Basic type checks - can be expanded
                    if not isinstance(period, str):
                        validation_errors.append(
                            f"Node '{node_name}': Invalid period format '{period}' - expected string."
                        )
                    if not isinstance(value, int | float):
                        validation_errors.append(
                            f"Node '{node_name}' period '{period}': Invalid value type {type(value).__name__} - expected number."
                        )
                    all_periods.add(str(period))

            if validation_errors:
                # For now, raise a ReadError; replace with DataValidationError once implemented.
                raise ReadError(
                    f"Input dictionary failed validation: {'; '.join(validation_errors)}",
                    source="dict_input",
                    reader_type="DictReader",
                )

        except Exception as e:
            # Catch unexpected validation errors
            raise ReadError(
                message=f"Error validating input dictionary: {e}",
                source="dict_input",
                reader_type="DictReader",
                original_error=e,
            ) from e

        # Determine graph periods: runtime kwargs override config defaults
        graph_periods = kwargs.get("periods", self.cfg.periods if self.cfg else None)
        if graph_periods is None:
            graph_periods = sorted(list(all_periods))
            logger.debug(f"Inferred graph periods from data: {graph_periods}")
        # Optional: Validate if all data periods are within the provided list
        elif not all_periods.issubset(set(graph_periods)):
            missing = all_periods - set(graph_periods)
            logger.warning(
                f"Data contains periods not in specified graph periods: {missing}"
            )
            # Decide whether to error or just ignore extra data

        # Create graph and add nodes
        try:
            graph = Graph(periods=graph_periods)
            for node_name, period_values in source.items():
                # Filter values to only include those matching graph_periods
                filtered_values = {
                    p: v for p, v in period_values.items() if p in graph_periods
                }
                if filtered_values:
                    # Create FinancialStatementItemNode directly
                    # Assumes FinancialStatementItemNode takes name and values dict
                    new_node = FinancialStatementItemNode(
                        name=node_name, values=filtered_values.copy()
                    )
                    graph.add_node(new_node)
                else:
                    logger.debug(
                        f"Node '{node_name}' has no data for specified graph periods. Skipping."
                    )

            logger.info(
                f"Successfully created graph with {len(graph.nodes)} nodes from dictionary."
            )
            return graph

        except Exception as e:
            # Catch errors during graph/node creation
            logger.error(f"Failed to create graph from dictionary: {e}", exc_info=True)
            raise ReadError(
                message="Failed to build graph from dictionary data",
                source="dict_input",
                reader_type="DictReader",
                original_error=e,
            ) from e
