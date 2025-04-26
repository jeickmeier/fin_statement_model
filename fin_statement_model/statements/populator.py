"""Populates a `fin_statement_model.core.graph.Graph` with calculation nodes.

This module provides the function `populate_graph_from_statement`, which is
responsible for translating the calculation logic defined within a
`StatementStructure` (specifically `CalculatedLineItem` and `SubtotalLineItem`)
into actual calculation nodes within a `Graph` instance. It bridges the gap
between the static definition of a statement and the dynamic calculation graph.
"""

import logging
from typing import Union

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
    LineItem,
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
    items_to_retry: list[Union[CalculatedLineItem, SubtotalLineItem]] = []

    logger.info(f"Starting graph population for statement '{statement.id}'. Processing {len(items_to_process)} calculation items.")

    def _process_item(item: Union[CalculatedLineItem, SubtotalLineItem], is_retry: bool = False) -> bool:
        """Process a single calculation/subtotal item. Return True if successful, False otherwise."""
        nonlocal nodes_added_count # Allow modification of outer scope variable
        item_id = item.id
        try:
            # Check if node already exists (idempotency)
            if graph.has_node(item_id):
                # logger.debug(f"Node '{item_id}' already exists in graph. Skipping addition.") # Reduced logging
                return True # Consider existing node as success

            if isinstance(item, CalculatedLineItem):
                # Get calculation details from the item properties
                calc_type = item.calculation_type
                input_item_ids = item.input_ids # These are ITEM IDs from the config
                params = item.parameters
                
                resolved_node_ids = []
                missing_input_details = [] # Store tuples of (item_id, node_id)

                for input_item_id in input_item_ids:
                    found_item = statement.find_item_by_id(input_item_id)
                    target_node_id = None
                    if found_item:
                        if isinstance(found_item, CalculatedLineItem): # Includes SubtotalLineItem
                            target_node_id = found_item.id
                        elif isinstance(found_item, LineItem):
                            target_node_id = found_item.node_id
                        
                    if target_node_id:
                        if graph.has_node(target_node_id):
                            resolved_node_ids.append(target_node_id)
                        else:
                            # Input node is missing
                            missing_input_details.append((input_item_id, target_node_id))
                    else:
                        logger.error(
                            f"Input item ID '{input_item_id}' required by calculation '{item.id}' not found "
                            f"or does not correspond to a graph node in statement '{statement.id}'."
                        )
                        missing_input_details.append((input_item_id, None))

                if missing_input_details:
                    missing_summary = [
                        f"item '{i_id}' needs node '{n_id}'"
                        if n_id else f"item '{i_id}' not found/mappable"
                        for i_id, n_id in missing_input_details
                    ]
                    # Don't log error immediately on first pass, just fail processing
                    # Log only if it fails on retry
                    if is_retry:
                        logger.error(
                            f"Retry failed for calculated item '{item.id}' for statement '{statement.id}': "
                            f"missing required inputs: {'; '.join(missing_summary)}"
                        )
                        errors_encountered.append((item_id, f"Missing inputs on retry: {missing_summary}"))
                    return False # Failed due to missing inputs
                
                # Add the calculation node
                graph.add_calculation(
                    name=item_id, # Use the calculated item's ID as the node name
                    input_names=resolved_node_ids, # Pass the list of actual node IDs
                    operation_type=calc_type,
                    **params
                )
                nodes_added_count += 1
                # logger.debug(f"Successfully added calculation node '{item_id}' from CalculatedLineItem.")
            
            elif isinstance(item, SubtotalLineItem):
                input_item_ids = item.item_ids # These are ITEM IDs from the config
                if not input_item_ids:
                    # logger.warning(f"Subtotal item '{item_id}' has no input item IDs. Skipping node creation.")
                    return True # Empty subtotal is not an error
                
                resolved_node_ids_sub = []
                missing_input_details_sub = []

                for input_item_id_sub in input_item_ids:
                    found_item_sub = statement.find_item_by_id(input_item_id_sub)
                    target_node_id_sub = None
                    if found_item_sub:
                        if isinstance(found_item_sub, CalculatedLineItem): # Includes SubtotalLineItem
                            target_node_id_sub = found_item_sub.id
                        elif isinstance(found_item_sub, LineItem):
                            target_node_id_sub = found_item_sub.node_id

                    if target_node_id_sub:
                        if graph.has_node(target_node_id_sub):
                            resolved_node_ids_sub.append(target_node_id_sub)
                        else:
                            missing_input_details_sub.append((input_item_id_sub, target_node_id_sub))
                    else:
                        logger.error(
                            f"Input item ID '{input_item_id_sub}' required by subtotal '{item.id}' not found "
                            f"or does not correspond to a graph node in statement '{statement.id}'."
                        )
                        missing_input_details_sub.append((input_item_id_sub, None))

                if missing_input_details_sub:
                    missing_summary_sub = [
                        f"item '{i_id}' needs node '{n_id}'"
                        if n_id else f"item '{i_id}' not found/mappable"
                        for i_id, n_id in missing_input_details_sub
                    ]
                    # Log only if it fails on retry
                    if is_retry:
                        logger.error(
                            f"Retry failed for subtotal item '{item.id}' for statement '{statement.id}': "
                            f"missing required inputs: {'; '.join(missing_summary_sub)}"
                        )
                        errors_encountered.append((item_id, f"Missing inputs for subtotal on retry: {missing_summary_sub}"))
                    return False # Failed due to missing inputs
                
                # Add the calculation node for subtotal
                graph.add_calculation(
                    name=item_id, # Use the subtotal item's ID as the node name
                    input_names=resolved_node_ids_sub, # Pass the RESOLVED node IDs
                    operation_type="addition", # Subtotals are always additions
                )
                nodes_added_count += 1
                # logger.debug(f"Successfully added calculation node '{item_id}' from SubtotalLineItem.")

            else:
                # Should not happen
                logger.warning(f"Skipping unexpected item type during population: {type(item).__name__} for ID '{item_id}'")
                return True # Don't treat as error, but skip
            
            return True # Item processed successfully

        except (NodeError, CircularDependencyError, CalculationError, ConfigurationError) as e:
            # Catch errors from graph.add_calculation or item definition issues
            error_msg = f"Failed to add node '{item_id}': {e!s}"
            if not is_retry: # Only log full exception on first pass if it's not a missing input NodeError
                if not (isinstance(e, NodeError) and "missing input nodes" in str(e).lower()):
                     logger.exception(error_msg)
            else: # Log exception if it fails on retry
                 logger.exception(error_msg)
                 errors_encountered.append((item_id, str(e))) # Store ID and error message
            return False # Failed processing
        except Exception as e:
            # Catch any other unexpected errors during processing of this item
            error_msg = f"Unexpected error processing item '{item_id}': {e!s}"
            logger.exception(error_msg) # Log with stack trace
            errors_encountered.append((item_id, f"Unexpected error: {e!s}"))
            return False # Failed processing

    for item in items_to_process:
        success = _process_item(item, is_retry=False)
        if not success:
            items_to_retry.append(item)

    if items_to_retry:
        logger.info(f"Retrying {len(items_to_retry)} items that failed initial population...")
        remaining_retries = []
        for item in items_to_retry:
            success = _process_item(item, is_retry=True)
            if not success:
                remaining_retries.append(item.id)
                # Error already logged in _process_item if is_retry=True
        
        if remaining_retries:
             logger.warning(f"Failed to populate {len(remaining_retries)} items even after retry: {remaining_retries}")

    if errors_encountered:
        logger.warning(f"Graph population for statement '{statement.id}' completed with {len(errors_encountered)} persistent errors.")
    else:
        logger.info(f"Graph population for statement '{statement.id}' completed successfully. Added {nodes_added_count} new nodes.")

    return errors_encountered
