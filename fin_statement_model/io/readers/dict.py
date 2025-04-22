"""Data reader for Python dictionaries."""

import logging
from typing import Any

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import FinancialStatementItemNode
from fin_statement_model.io.base import DataReader
from fin_statement_model.io.registry import register_reader
from fin_statement_model.io.exceptions import ReadError  # Removed DataValidationError

logger = logging.getLogger(__name__)


@register_reader("dict")
class DictReader(DataReader):
    """Reads data from a Python dictionary to create a new Graph.

    Expects a dictionary format: {node_name: {period: value, ...}, ...}
    Creates FinancialStatementItemNode instances for each entry.
    """

    def read(self, source: dict[str, dict[str, float]], **kwargs: dict[str, Any]) -> Graph:
        """Create a new Graph from a dictionary.

        Args:
            source: Dictionary mapping node names to period-value dictionaries.
                    Format: {node_name: {period: value, ...}, ...}
            **kwargs: Optional arguments:
                periods (list[str]): Explicit list of periods for the new graph.
                                     If None, inferred from data keys.

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
        validation_errors = []
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
                    if not isinstance(value, (int, float)):
                        validation_errors.append(
                            f"Node '{node_name}' period '{period}': Invalid value type {type(value).__name__} - expected number."
                        )
                    all_periods.add(str(period))

            if validation_errors:
                # Use core DataValidationError if it exists and is suitable
                # Otherwise, stick to ReadError or a specific IOValidationError
                # raise DataValidationError(
                #     message="Input dictionary failed validation",
                #     validation_errors=validation_errors
                # )
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

        # Determine graph periods
        graph_periods = kwargs.get("periods")
        if graph_periods is None:
            graph_periods = sorted(list(all_periods))
            logger.debug(f"Inferred graph periods from data: {graph_periods}")
        # Optional: Validate if all data periods are within the provided list
        elif not all_periods.issubset(set(graph_periods)):
            missing = all_periods - set(graph_periods)
            logger.warning(f"Data contains periods not in specified graph periods: {missing}")
            # Decide whether to error or just ignore extra data

        # Create graph and add nodes
        try:
            graph = Graph(periods=graph_periods)
            for node_name, period_values in source.items():
                # Filter values to only include those matching graph_periods
                filtered_values = {p: v for p, v in period_values.items() if p in graph_periods}
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
