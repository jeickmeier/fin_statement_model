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
    MetricError,
)

# Import the MetricRegistry CLASS, not an instance
from fin_statement_model.core.metrics.registry import MetricRegistry
from fin_statement_model.statements.structure import (
    StatementStructure,
    CalculatedLineItem,
    SubtotalLineItem,
    MetricLineItem,
    LineItem,
)

logger = logging.getLogger(__name__)

__all__ = ["populate_graph_from_statement"]


def populate_graph_from_statement(
    statement: StatementStructure, graph: Graph
) -> list[tuple[str, str]]:
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

    items_to_process = (
        statement.get_calculation_items()
    )  # Gets CalculatedLineItem and SubtotalLineItem
    metric_items_to_process = statement.get_metric_items()  # Assume this method exists or add it
    all_items_to_process = items_to_process + metric_items_to_process

    errors_encountered: list[tuple[str, str]] = []
    nodes_added_count = 0

    # Instantiate the registry here
    try:
        metric_registry = MetricRegistry()  # Instantiate the class
        # TODO: Consider where/how to load metric definitions into this instance.
        # For now, it assumes metrics are loaded elsewhere or not needed immediately.
        # A better approach might be to pass a pre-loaded registry instance
        # into populate_graph_from_statement.
    except Exception as e:
        logger.exception("Failed to initialize MetricRegistry.")
        raise ConfigurationError(f"MetricRegistry initialization failed: {e}") from e

    logger.info(
        f"Starting graph population for statement '{statement.id}'. Processing {len(all_items_to_process)} calculation/metric items."
    )

    def _process_item(
        item: Union[CalculatedLineItem, SubtotalLineItem, MetricLineItem], is_retry: bool = False
    ) -> bool:  # Update Union
        """Process a single calculation/subtotal/metric item. Return True if successful, False otherwise."""
        nonlocal nodes_added_count  # Allow modification of outer scope variable
        item_id = item.id
        success = False  # Initialize success flag
        processed_item = False  # Flag to track if an item type was handled
        action_taken = (
            False  # Flag to track if a node was potentially added or skipped intentionally
        )

        try:
            # Check if node already exists (idempotency)
            if graph.has_node(item_id):
                # logger.debug(f"Node '{item_id}' already exists in graph. Skipping addition.") # Reduced logging
                success = True  # Consider existing node as success
                action_taken = True  # We intentionally skipped adding it

            # --- Handle MetricLineItem --- #
            elif isinstance(item, MetricLineItem):
                processed_item = True
                try:
                    # Use the instantiated registry object
                    metric = metric_registry.get(item.metric_id)
                except MetricError as e:
                    logger.exception(
                        f"Cannot populate item '{item_id}': Metric '{item.metric_id}' not found in registry"
                    )
                    errors_encountered.append(
                        (item_id, f"Metric '{item.metric_id}' not found: {e}")
                    )
                    # Keep success = False

                else:  # Only proceed if metric was found
                    # Metric found, now resolve its inputs based on the item's mapping
                    metric_input_names = metric.inputs  # Expected input names by the metric
                    item_input_map = item.inputs  # Mapping: metric_input_name -> statement_item_id

                    resolved_node_ids_map: dict[str, str] = {}
                    missing_metric_input_details = []

                    # Verify item_input_map provides all required metric inputs
                    provided_metric_inputs = set(item_input_map.keys())
                    required_metric_inputs = set(metric_input_names)
                    if provided_metric_inputs != required_metric_inputs:
                        missing_req = required_metric_inputs - provided_metric_inputs
                        extra_prov = provided_metric_inputs - required_metric_inputs
                        error_msg = f"Input mapping mismatch for metric '{item.metric_id}' in item '{item_id}'."
                        if missing_req:
                            error_msg += f" Missing required metric inputs: {missing_req}."
                        if extra_prov:
                            error_msg += f" Unexpected inputs provided: {extra_prov}."
                        logger.error(error_msg)
                        errors_encountered.append((item_id, error_msg))
                        # Keep success = False
                    else:
                        # Resolve statement item IDs to graph node IDs
                        for metric_input_name in metric.inputs:
                            input_map_value = item_input_map[
                                metric_input_name
                            ]  # ID from the YAML mapping value
                            target_node_id = None

                            # 1. Check if the mapping value refers to another statement item ID
                            found_item = statement.find_item_by_id(input_map_value)
                            if found_item:
                                if isinstance(
                                    found_item, CalculatedLineItem | MetricLineItem
                                ):  # Includes Subtotal
                                    target_node_id = (
                                        found_item.id
                                    )  # The item ID itself is the node ID
                                elif isinstance(found_item, LineItem):
                                    target_node_id = (
                                        found_item.node_id
                                    )  # Map to the underlying node_id

                            # 2. If not found as a statement item, check if it's a direct graph node ID
                            elif graph.has_node(input_map_value):
                                target_node_id = input_map_value  # The mapping value IS the node ID

                            # 3. Now check if the resolved target_node_id exists and add it
                            if target_node_id:
                                if graph.has_node(target_node_id):
                                    # Map metric input name -> resolved graph node name
                                    resolved_node_ids_map[metric_input_name] = target_node_id
                                else:
                                    # The target node (either from item.node_id or direct mapping) doesn't exist in the graph
                                    missing_metric_input_details.append(
                                        (input_map_value, target_node_id)
                                    )
                            else:
                                # The input_map_value wasn't found as a statement item OR a direct graph node
                                logger.error(
                                    f"Mapped input '{input_map_value}' (for metric input '{metric_input_name}') "
                                    f"required by metric item '{item.id}' could not be resolved to a statement item or a graph node in statement '{statement.id}'."
                                )
                                missing_metric_input_details.append((input_map_value, None))

                        if missing_metric_input_details:
                            missing_summary = [
                                f"statement item '{i_id}' needs node '{n_id}'"
                                if n_id
                                else f"statement item '{i_id}' not found/mappable"
                                for i_id, n_id in missing_metric_input_details
                            ]
                            if is_retry:
                                logger.error(
                                    f"Retry failed for metric item '{item.id}' (metric '{item.metric_id}') for statement '{statement.id}': "
                                    f"missing required input nodes: {'; '.join(missing_summary)}"
                                )
                                errors_encountered.append(
                                    (
                                        item_id,
                                        f"Missing inputs for metric on retry: {missing_summary}",
                                    )
                                )
                            # Keep success = False
                        else:
                            # Add the metric node using graph.add_metric
                            graph.add_metric(
                                metric_name=item.metric_id,
                                node_name=item_id, # Use the statement item ID as the node name
                                input_node_map=resolved_node_ids_map # Pass the resolved map
                            )
                            nodes_added_count += 1
                            success = True  # Node added successfully
                            action_taken = True
                            # logger.debug(f"Successfully added calculation node '{item_id}' from MetricLineItem '{item.metric_id}'.")

            # --- Handle CalculatedLineItem (existing logic) --- #
            elif isinstance(item, CalculatedLineItem):
                processed_item = True
                # Get calculation details from the item properties
                calc_type = item.calculation_type
                input_item_ids = item.input_ids  # These are ITEM IDs from the config
                params = item.parameters

                resolved_node_ids = []
                missing_input_details = []  # Store tuples of (item_id, node_id)

                for input_item_id in input_item_ids:
                    found_item = statement.find_item_by_id(input_item_id)
                    target_node_id = None
                    if found_item:
                        if isinstance(found_item, CalculatedLineItem):  # Includes SubtotalLineItem
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
                        if n_id
                        else f"item '{i_id}' not found/mappable"
                        for i_id, n_id in missing_input_details
                    ]
                    # Don't log error immediately on first pass, just fail processing
                    # Log only if it fails on retry
                    if is_retry:
                        logger.error(
                            f"Retry failed for calculated item '{item.id}' for statement '{statement.id}': "
                            f"missing required inputs: {'; '.join(missing_summary)}"
                        )
                        errors_encountered.append(
                            (item_id, f"Missing inputs on retry: {missing_summary}")
                        )
                    # Keep success = False
                else:
                    # Add the calculation node
                    graph.add_calculation(
                        name=item_id,  # Use the calculated item's ID as the node name
                        input_names=resolved_node_ids,  # Pass the list of actual node IDs
                        operation_type=calc_type,
                        **params,
                    )
                    nodes_added_count += 1
                    success = True  # Node added successfully
                    action_taken = True
                    # logger.debug(f"Successfully added calculation node '{item_id}' from CalculatedLineItem.")

            elif isinstance(item, SubtotalLineItem):
                processed_item = True
                input_item_ids = item.item_ids  # These are ITEM IDs from the config
                if not input_item_ids:
                    # logger.warning(f"Subtotal item '{item_id}' has no input item IDs. Skipping node creation.")
                    success = True  # Empty subtotal is not an error, consider it success
                    action_taken = True
                else:
                    resolved_node_ids_sub = []
                    missing_input_details_sub = []

                    for input_item_id_sub in input_item_ids:
                        found_item_sub = statement.find_item_by_id(input_item_id_sub)
                        target_node_id_sub = None
                        if found_item_sub:
                            if isinstance(
                                found_item_sub, CalculatedLineItem
                            ):  # Includes SubtotalLineItem
                                target_node_id_sub = found_item_sub.id
                            elif isinstance(found_item_sub, LineItem):
                                target_node_id_sub = found_item_sub.node_id

                        if target_node_id_sub:
                            if graph.has_node(target_node_id_sub):
                                resolved_node_ids_sub.append(target_node_id_sub)
                            else:
                                missing_input_details_sub.append(
                                    (input_item_id_sub, target_node_id_sub)
                                )
                        else:
                            logger.error(
                                f"Input item ID '{input_item_id_sub}' required by subtotal '{item.id}' not found "
                                f"or does not correspond to a graph node in statement '{statement.id}'."
                            )
                            missing_input_details_sub.append((input_item_id_sub, None))

                    if missing_input_details_sub:
                        missing_summary_sub = [
                            f"item '{i_id}' needs node '{n_id}'"
                            if n_id
                            else f"item '{i_id}' not found/mappable"
                            for i_id, n_id in missing_input_details_sub
                        ]
                        # Log only if it fails on retry
                        if is_retry:
                            logger.error(
                                f"Retry failed for subtotal item '{item.id}' for statement '{statement.id}': "
                                f"missing required inputs: {'; '.join(missing_summary_sub)}"
                            )
                            errors_encountered.append(
                                (
                                    item_id,
                                    f"Missing inputs for subtotal on retry: {missing_summary_sub}",
                                )
                            )
                        # Keep success = False
                    else:
                        # Add the calculation node for subtotal
                        graph.add_calculation(
                            name=item_id,  # Use the subtotal item's ID as the node name
                            input_names=resolved_node_ids_sub,  # Pass the RESOLVED node IDs
                            operation_type="addition",  # Subtotals are always additions
                        )
                        nodes_added_count += 1
                        success = True  # Node added successfully
                        action_taken = True
                        # logger.debug(f"Successfully added calculation node '{item_id}' from SubtotalLineItem.")

            # Handle cases where the item type is not one we process for node creation
            # Only log if it wasn't already handled (e.g. by graph.has_node)
            if not action_taken and not processed_item:
                # Check if it's a type we *expect* to skip (like a basic LineItem without calculation)
                if not isinstance(
                    item, LineItem | CalculatedLineItem | SubtotalLineItem | MetricLineItem
                ):
                    # Log unexpected types
                    logger.warning(
                        f"Skipping unexpected item type during population: {type(item).__name__} for ID '{item.id}'"
                    )
                # If it's an expected non-calculated type or already exists, it's not an error
                success = True

        except (NodeError, CircularDependencyError, CalculationError, ConfigurationError) as e:
            # Catch errors from graph.add_calculation or item definition issues
            error_msg = f"Failed to add node '{item_id}': {e!s}"
            # Check if it's a missing input error *not* during retry phase
            is_missing_input_error = (
                isinstance(e, NodeError) and "missing input nodes" in str(e).lower()
            )

            if not is_retry and is_missing_input_error:
                # Don't log exception trace for expected missing inputs on first pass
                pass  # Keep success = False
            elif is_retry and is_missing_input_error:
                # Log exception trace if missing inputs persist on retry
                logger.exception(error_msg)
                errors_encountered.append((item_id, str(e)))  # Store ID and error message
                success = False
            else:  # Log all other errors immediately
                logger.exception(error_msg)
                errors_encountered.append((item_id, str(e)))  # Store ID and error message
                success = False  # Ensure success is False on error

        except Exception as e:
            # Catch any other unexpected errors during processing of this item
            error_msg = f"Unexpected error processing item '{item_id}': {e!s}"
            logger.exception(error_msg)  # Log with stack trace
            errors_encountered.append((item_id, f"Unexpected error: {e!s}"))
            success = False  # Ensure success is False on unexpected error

        return success  # Single return point

    # --- Initial Processing Pass ---
    items_to_process_loop = list(all_items_to_process)  # Start with all items
    processed_in_pass = -1  # Flag to check if progress is being made

    while (
        items_to_process_loop and processed_in_pass != 0
    ):  # Loop until no items left or no progress
        items_failed_this_pass = []
        processed_in_pass = 0

        logger.info(f"Population loop: Processing {len(items_to_process_loop)} items...")

        for item in items_to_process_loop:
            # Use is_retry=True only if it's not the very first pass for THIS item
            # Check if item was in the *previous* iteration's failed list if needed,
            # but for simplicity, let's treat subsequent loops as retries for logging.
            # A simple check: len(items_to_process_loop) != len(all_items_to_process) indicates a retry loop.
            is_retry_log = len(items_to_process_loop) < len(all_items_to_process)
            success = _process_item(item, is_retry=is_retry_log)

            if success:
                processed_in_pass += 1
            else:
                items_failed_this_pass.append(item)

        # Prepare for the next loop with only the failed items
        items_to_process_loop = items_failed_this_pass

        if processed_in_pass == 0 and items_to_process_loop:
            # No progress made, but items still failed - indicates persistent issue (e.g., circular dep or truly missing node)
            logger.warning(
                f"Population loop stalled. {len(items_to_process_loop)} items could not be processed: {[item.id for item in items_to_process_loop]}"
            )
            # Add these persistent failures to the main error list
            for item in items_to_process_loop:
                # Attempt to add a generic error if not already added by _process_item
                if not any(err[0] == item.id for err in errors_encountered):
                    errors_encountered.append(
                        (
                            item.id,
                            "Failed to process due to unresolved dependencies or circular reference.",
                        )
                    )
            break  # Exit the loop

    if errors_encountered:
        logger.warning(
            f"Graph population for statement '{statement.id}' completed with {len(errors_encountered)} persistent errors."
        )
    else:
        log_level = logging.INFO if nodes_added_count > 0 else logging.DEBUG
        logger.log(
            log_level,
            f"Graph population for statement '{statement.id}' completed. Added {nodes_added_count} new nodes.",
        )

    return errors_encountered
