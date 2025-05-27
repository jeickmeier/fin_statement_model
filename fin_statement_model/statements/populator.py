"""Populates a `fin_statement_model.core.graph.Graph` with calculation nodes.

This module provides the function `populate_graph_from_statement`, which is
responsible for translating the calculation logic defined within a
`StatementStructure` (specifically `CalculatedLineItem`, `SubtotalLineItem`,
and `MetricLineItem`) into actual calculation nodes within a `Graph` instance.

Key Concepts:
- **ID Resolution**: Statement configurations use item IDs that must be resolved
  to graph node IDs. This is handled by `_resolve_statement_input_to_graph_node_id`.
- **Dependency Ordering**: Items may depend on other items. The populator handles
  this by retrying failed items after successful ones, allowing dependencies to
  be satisfied.
- **Idempotency**: If a node already exists in the graph, it will be skipped.
"""

import logging
from typing import Union, Optional

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.errors import (
    NodeError,
    CircularDependencyError,
    CalculationError,
    ConfigurationError,
    MetricError,
)

# Import the MetricRegistry CLASS, not an instance
from fin_statement_model.core.metrics import (
    metric_registry,
)  # Import the global instance
from fin_statement_model.statements.structure import (
    StatementStructure,
    CalculatedLineItem,
    SubtotalLineItem,
    MetricLineItem,
    LineItem,
)

logger = logging.getLogger(__name__)

__all__ = ["populate_graph_from_statement"]


def _resolve_statement_input_to_graph_node_id(
    item_id_from_config: str, statement: StatementStructure, graph: Graph
) -> Optional[str]:
    """Resolve a statement item ID to its corresponding graph node ID.

    This helper function centralizes the logic for mapping item IDs from statement
    configurations (as found in calculation inputs or metric input mappings) to
    actual graph node IDs. This is necessary because:

    1. **LineItems** have a separate `node_id` property that differs from their `id`
    2. **Calculated/Subtotal/MetricLineItems** use their `id` as the node ID
    3. Some nodes may exist directly in the graph without being statement items

    Resolution Process:
    1. First, search for the item in the statement structure
    2. If found as a LineItem, return its `node_id` property
    3. If found as a CalculatedLineItem/SubtotalLineItem/MetricLineItem, return its `id`
    4. If not found in statement, check if it exists directly in the graph
    5. Return None if not found anywhere

    Args:
        item_id_from_config: The item ID as specified in the statement configuration.
                            This is typically what appears in YAML/JSON configs.
        statement: The StatementStructure containing the item definitions.
        graph: The Graph instance to check for existing nodes.

    Returns:
        The resolved graph node ID if found, None otherwise.

    Example:
        >>> # Given a LineItem with id='revenue_item' and node_id='revenue_node'
        >>> # And a CalculatedLineItem with id='gross_profit'
        >>> _resolve_statement_input_to_graph_node_id('revenue_item', statement, graph)
        'revenue_node'  # Returns the node_id property
        >>> _resolve_statement_input_to_graph_node_id('gross_profit', statement, graph)
        'gross_profit'  # Returns the id itself
    """
    # First, try to find the item in the statement structure
    found_item = statement.find_item_by_id(item_id_from_config)

    if found_item:
        if isinstance(found_item, LineItem):
            # For basic LineItems, use the node_id property
            return found_item.node_id
        elif isinstance(found_item, CalculatedLineItem | SubtotalLineItem | MetricLineItem):
            # For calculated/subtotal/metric items, the item ID itself is the node ID
            return found_item.id

    # If not found as a statement item, check if it exists directly in the graph
    elif graph.has_node(item_id_from_config):
        return item_id_from_config

    # Not found in statement or graph
    return None


def populate_graph_from_statement(
    statement: StatementStructure, graph: Graph
) -> list[tuple[str, str]]:
    """Add calculation nodes defined in a StatementStructure to a Graph.

    This function bridges the gap between static statement definitions and the
    dynamic calculation graph. It processes three types of items:

    1. **CalculatedLineItem**: Creates calculation nodes with specified operations
    2. **SubtotalLineItem**: Creates addition nodes that sum multiple items
    3. **MetricLineItem**: Creates metric-based calculation nodes

    ID Resolution Logic:
    - Input IDs in statement configurations are resolved to graph node IDs using
      `_resolve_statement_input_to_graph_node_id`
    - This handles the mapping between statement item IDs and actual graph nodes
    - Resolution accounts for LineItem.node_id vs other items using their ID directly

    Dependency Handling:
    - Items may depend on other items that haven't been created yet
    - The function uses a retry mechanism: failed items are retried after
      successful ones, allowing dependencies to be resolved
    - Circular dependencies are detected and reported as errors

    Idempotency:
    - If a node already exists in the graph, it will be skipped
    - This allows the function to be called multiple times safely

    Args:
        statement: The `StatementStructure` object containing the definitions
            of calculated items, subtotals, and metrics.
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
        >>> from fin_statement_model.statements.structure import StatementStructure
        >>>
        >>> # Create graph with data nodes
        >>> graph = Graph()
        >>> graph.add_node('revenue_node', values={'2023': 1000})
        >>> graph.add_node('cogs_node', values={'2023': 600})
        >>>
        >>> # Create statement with calculations
        >>> statement = StatementStructure(id="IS", name="Income Statement")
        >>> # Add a LineItem that maps to 'revenue_node'
        >>> revenue_item = LineItem(id='revenue', name='Revenue', node_id='revenue_node')
        >>> # Add a CalculatedLineItem that references the LineItem
        >>> gross_profit = CalculatedLineItem(
        ...     id='gross_profit',
        ...     name='Gross Profit',
        ...     calculation_type='subtraction',
        ...     input_ids=['revenue', 'cogs']  # Uses LineItem IDs
        ... )
        >>>
        >>> errors = populate_graph_from_statement(statement, graph)
        >>> # The function will:
        >>> # 1. Resolve 'revenue' to 'revenue_node' via LineItem.node_id
        >>> # 2. Resolve 'cogs' to 'cogs_node' (if it exists in statement or graph)
        >>> # 3. Create a calculation node 'gross_profit' with the resolved inputs
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

    logger.info(
        f"Starting graph population for statement '{statement.id}'. Processing {len(all_items_to_process)} calculation/metric items."
    )

    def _process_item(
        item: Union[CalculatedLineItem, SubtotalLineItem, MetricLineItem],
        is_retry: bool = False,
    ) -> bool:  # Update Union
        """Process a single calculation/subtotal/metric item and add it to the graph.

        This internal function handles the creation of a single calculation node,
        including ID resolution and error handling. It's designed to be called
        multiple times as part of the dependency resolution mechanism.

        Processing Logic:
        1. Check if node already exists (idempotency check)
        2. Based on item type, resolve input IDs to graph node IDs
        3. Attempt to create the calculation node
        4. Handle missing dependencies gracefully (allows retry)

        ID Resolution:
        - Uses `_resolve_statement_input_to_graph_node_id` for all input IDs
        - Handles the mapping from statement item IDs to graph node IDs
        - Tracks missing inputs for detailed error reporting

        Error Handling:
        - Missing inputs on first pass: Returns False without logging errors
        - Missing inputs on retry: Logs errors and adds to error list
        - Other errors: Always logged immediately

        Args:
            item: The statement item to process (CalculatedLineItem, SubtotalLineItem,
                  or MetricLineItem)
            is_retry: Whether this is a retry attempt. Affects error logging behavior.

        Returns:
            True if the node was successfully added or already exists, False otherwise.

        Side Effects:
            - May add a node to the graph
            - May append to errors_encountered list
            - Increments nodes_added_count on success
        """
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
                    missing_metric_input_details: list[tuple[str, Optional[str]]] = []

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

                            # Use the helper function to resolve the node ID
                            target_node_id = _resolve_statement_input_to_graph_node_id(
                                input_map_value, statement, graph
                            )

                            if target_node_id and graph.has_node(target_node_id):
                                # Map metric input name -> resolved graph node name
                                resolved_node_ids_map[metric_input_name] = target_node_id
                            else:
                                # The target node doesn't exist in the graph
                                missing_metric_input_details.append(
                                    (input_map_value, target_node_id)
                                )

                        if missing_metric_input_details:
                            missing_summary = [
                                (
                                    f"statement item '{i_id}' needs node '{n_id}'"
                                    if n_id
                                    else f"statement item '{i_id}' not found/mappable"
                                )
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
                                node_name=item_id,  # Use the statement item ID as the node name
                                input_node_map=resolved_node_ids_map,  # Pass the resolved map
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
                missing_input_details: list[
                    tuple[str, Optional[str]]
                ] = []  # Store tuples of (item_id, node_id)

                for input_item_id in input_item_ids:
                    # Use the helper function to resolve the node ID
                    target_node_id = _resolve_statement_input_to_graph_node_id(
                        input_item_id, statement, graph
                    )

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
                        (
                            f"item '{i_id}' needs node '{n_id}'"
                            if n_id
                            else f"item '{i_id}' not found/mappable"
                        )
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
                    missing_input_details_sub: list[tuple[str, Optional[str]]] = []

                    for input_item_id_sub in input_item_ids:
                        # Use the helper function to resolve the node ID
                        target_node_id_sub = _resolve_statement_input_to_graph_node_id(
                            input_item_id_sub, statement, graph
                        )

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
                            (
                                f"item '{i_id}' needs node '{n_id}'"
                                if n_id
                                else f"item '{i_id}' not found/mappable"
                            )
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
                    item,
                    LineItem | CalculatedLineItem | SubtotalLineItem | MetricLineItem,
                ):
                    # Log unexpected types
                    logger.warning(
                        f"Skipping unexpected item type during population: {type(item).__name__} for ID '{item.id}'"
                    )
                # If it's an expected non-calculated type or already exists, it's not an error
                success = True

        except (
            NodeError,
            CircularDependencyError,
            CalculationError,
            ConfigurationError,
        ) as e:
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
