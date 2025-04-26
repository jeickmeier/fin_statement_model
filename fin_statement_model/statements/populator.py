"""Populates a `fin_statement_model.core.graph.Graph` with calculation nodes.

This module provides the function `populate_graph_from_statement`, which is
responsible for translating the calculation logic defined within a
`StatementStructure` (specifically `CalculatedLineItem` and `SubtotalLineItem`)
into actual calculation nodes within a `Graph` instance. It bridges the gap
between the static definition of a statement and the dynamic calculation graph.
"""

import logging

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.errors import (
    NodeError,
    CircularDependencyError,
    CalculationError,
    ConfigurationError,
)
from fin_statement_model.statements.structure import (
    StatementStructure,
    CalculatedLineItem,
    SubtotalLineItem,
)

logger = logging.getLogger(__name__)

__all__ = ["populate_graph_from_statement"]


def populate_graph_from_statement(statement: StatementStructure, graph: Graph) -> list[tuple[str, str]]:
    """Add calculation nodes defined in a StatementStructure to a Graph.

    Iterates through `CalculatedLineItem` and `SubtotalLineItem` instances
    found within the provided `statement` structure. For each item, it attempts
    to add a corresponding calculation node to the `graph` using the
    `graph.add_calculation` method. This method implicitly handles dependency
    checking and cycle detection within the graph.

    This function is designed to be idempotent: if a node corresponding to a
    statement item already exists in the graph, it will be skipped.

    Args:
        statement: The `StatementStructure` object containing the definitions
            of calculated items and subtotals (e.g., built by
            `StatementStructureBuilder`).
        graph: The `core.graph.Graph` instance that will be populated with
            the calculation nodes.

    Returns:
        A list of tuples, where each tuple contains `(item_id, error_message)`
        for any items that could not be successfully added to the graph. An
        empty list indicates that all applicable items were added (or already
        existed) without critical errors.

    Raises:
        TypeError: If `statement` is not a `StatementStructure` or `graph` is
            not a `Graph` instance.

    Example:
        >>> from fin_statement_model.core.graph import Graph
        >>> from fin_statement_model.statements.structure import StatementStructure # and items
        >>> # Assume 'my_statement' is a valid StatementStructure instance
        >>> # Assume 'my_graph' is a Graph, potentially with data nodes
        >>> my_graph = Graph()
        >>> my_statement = StatementStructure(id="IS", name="Income Statement")
        >>> # ... add sections and items to my_statement ...
        >>> # Example item: CalculatedLineItem(id="gross_profit", ..., calculation=...)
        >>>
        >>> errors = populate_graph_from_statement(my_statement, my_graph)
        >>> if errors:
        ...     # Example of handling errors - use logging in real code
        ...     logger.warning(f"Errors encountered during population: {errors}")
        ... else:
        ...     logger.info("Graph populated successfully.")
        >>> # 'my_graph' now contains a calculation node for 'gross_profit' (if defined)
    """
    if not isinstance(statement, StatementStructure):
        raise TypeError("statement must be a StatementStructure instance")
    if not isinstance(graph, Graph):
        raise TypeError("graph must be a Graph instance")

    items_to_process = statement.get_calculation_items() # Gets CalculatedLineItem and SubtotalLineItem
    errors_encountered: list[tuple[str, str]] = []
    nodes_added_count = 0

    logger.info(f"Starting graph population for statement '{statement.id}'. Processing {len(items_to_process)} calculation items.")

    for item in items_to_process:
        item_id = item.id
        try:
            # Check if node already exists (idempotency)
            if graph.has_node(item_id):
                logger.debug(f"Node '{item_id}' already exists in graph. Skipping addition.")
                continue

            if isinstance(item, CalculatedLineItem):
                # calculation is stored as dict in CalculatedLineItem after builder
                calc_info = item.calculation
                op_type = calc_info.get("type")
                input_ids = calc_info.get("inputs")
                params = calc_info.get("parameters", {})

                if not op_type or not input_ids:
                    raise ConfigurationError( # Or StatementError?
                        f"Calculation item '{item_id}' is missing type or inputs in its definition."
                    )

                graph.add_calculation(
                    name=item_id,
                    input_names=input_ids,
                    operation_type=op_type,
                    **params
                )
                nodes_added_count += 1
                logger.debug(f"Successfully added calculation node '{item_id}' from CalculatedLineItem.")

            elif isinstance(item, SubtotalLineItem):
                # Subtotals are simple additions of their specified item_ids
                input_ids = item.item_ids
                if not input_ids:
                    logger.warning(f"Subtotal item '{item_id}' has no input item IDs. Skipping graph node creation.")
                    continue

                graph.add_calculation(
                    name=item_id,
                    input_names=input_ids,
                    operation_type="addition", # Subtotals are always additions
                )
                nodes_added_count += 1
                logger.debug(f"Successfully added calculation node '{item_id}' from SubtotalLineItem.")

            else:
                # Should not happen if get_calculation_items works correctly
                logger.warning(f"Skipping unexpected item type during population: {type(item).__name__} for ID '{item_id}'")
                continue

        except (NodeError, CircularDependencyError, CalculationError, ConfigurationError) as e:
            # Catch errors from graph.add_calculation or item definition issues
            error_msg = f"Failed to add node '{item_id}': {e!s}"
            logger.exception(error_msg)
            errors_encountered.append((item_id, str(e))) # Store ID and error message
            # Continue processing other items
        except Exception as e:
            # Catch any other unexpected errors during processing of this item
            error_msg = f"Unexpected error processing item '{item_id}': {e!s}"
            logger.exception(error_msg) # Log with stack trace
            errors_encountered.append((item_id, f"Unexpected error: {e!s}"))
            # Continue processing other items

    if errors_encountered:
        logger.warning(f"Graph population for statement '{statement.id}' completed with {len(errors_encountered)} errors.")
    else:
        logger.info(f"Graph population for statement '{statement.id}' completed successfully. Added {nodes_added_count} new nodes.")

    return errors_encountered
