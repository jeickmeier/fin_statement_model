"""Populates a `fin_statement_model.core.graph.Graph` with calculation nodes.

This module provides the function `populate_graph_from_statement`, which is
responsible for translating the calculation logic defined within a
`StatementStructure` (specifically `CalculatedLineItem`, `SubtotalLineItem`,
and `MetricLineItem`) into actual calculation nodes within a `Graph` instance.

Key Concepts:
- **ID Resolution**: Statement configurations use item IDs that must be resolved
  to graph node IDs. This is handled by the `IDResolver` class.
- **Dependency Ordering**: Items may depend on other items. The populator handles
  this by retrying failed items after successful ones, allowing dependencies to
  be satisfied.
- **Idempotency**: If a node already exists in the graph, it will be skipped.
"""

import logging

from fin_statement_model.core.graph import Graph
from fin_statement_model.statements.structure import StatementStructure
from fin_statement_model.statements.population.id_resolver import IDResolver
from fin_statement_model.statements.population.item_processors import (
    ItemProcessorManager,
)

logger = logging.getLogger(__name__)

__all__ = ["populate_graph_from_statement"]


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
      the `IDResolver` class
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
        >>> graph.add_financial_statement_item('revenue_node', {'2023': 1000})
        >>> graph.add_financial_statement_item('cogs_node', {'2023': 600})
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
    # Validate inputs
    if not isinstance(statement, StatementStructure):
        raise TypeError("statement must be a StatementStructure instance")
    if not isinstance(graph, Graph):
        raise TypeError("graph must be a Graph instance")

    # Initialize components
    id_resolver = IDResolver(statement)
    processor_manager = ItemProcessorManager(id_resolver, graph, statement)

    # Get all items to process
    calculation_items = statement.get_calculation_items()
    metric_items = statement.get_metric_items()
    all_items_to_process = calculation_items + metric_items

    # Track results
    errors_encountered: list[tuple[str, str]] = []
    nodes_added_count = 0

    logger.info(
        f"Starting graph population for statement '{statement.id}'. "
        f"Processing {len(all_items_to_process)} calculation/metric items."
    )

    # Process items with retry mechanism
    items_to_process = list(all_items_to_process)
    processed_in_pass = -1  # Initialize to enter loop

    while items_to_process and processed_in_pass != 0:
        items_failed_this_pass = []
        processed_in_pass = 0

        logger.debug(f"Population loop: Processing {len(items_to_process)} items...")

        for item in items_to_process:
            # Determine if this is a retry (not the first overall pass)
            is_retry = len(items_to_process) < len(all_items_to_process)

            # Process the item
            result = processor_manager.process_item(item, is_retry)

            if result.success:
                processed_in_pass += 1
                if result.node_added:
                    nodes_added_count += 1
            else:
                items_failed_this_pass.append(item)
                # Only record errors on retry or for non-dependency errors
                if is_retry and result.error_message:
                    errors_encountered.append((item.id, result.error_message))

        # Prepare for next iteration
        items_to_process = items_failed_this_pass

        # Check for stalled progress
        if processed_in_pass == 0 and items_to_process:
            logger.warning(
                f"Population loop stalled. {len(items_to_process)} items could not be processed: "
                f"{[item.id for item in items_to_process]}"
            )
            # Add errors for items that couldn't be processed
            for item in items_to_process:
                if not any(err[0] == item.id for err in errors_encountered):
                    errors_encountered.append(
                        (
                            item.id,
                            "Failed to process due to unresolved dependencies or circular reference.",
                        )
                    )
            break

    # Log results
    if errors_encountered:
        logger.warning(
            f"Graph population for statement '{statement.id}' completed with "
            f"{len(errors_encountered)} persistent errors."
        )
    else:
        log_level = logging.INFO if nodes_added_count > 0 else logging.DEBUG
        logger.log(
            log_level,
            f"Graph population for statement '{statement.id}' completed. "
            f"Added {nodes_added_count} new nodes.",
        )

    return errors_encountered
