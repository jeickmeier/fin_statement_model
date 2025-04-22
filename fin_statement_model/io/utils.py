"""Utility functions for the IO package."""

# Currently no generic utility functions remain after refactoring.
# Retain file for potential future additions.

# Removed functions:
# - export_graph_to_dict (moved to writers.dict.DictWriter)
# - import_data_from_dict (logic adapted into readers.dict.DictReader)

# Use absolute import instead of relative
from fin_statement_model.core.graph import Graph

# Import Node type if needed for type checking or instanceof checks
# from ...core.nodes import Node


def export_graph_to_dict(graph: Graph) -> dict[str, dict[str, float]]:
    """Export data from the graph nodes that have values.

    Args:
        graph: The Graph instance to export data from.

    Returns:
        Dict[str, Dict[str, float]]: Mapping node names to period-value dicts.
                                     Only includes nodes with a 'values' attribute.
    """
    result: dict[str, dict[str, float]] = {}
    for node_id, node in graph.nodes.items():
        # Check if the node has a 'values' attribute containing the data
        if hasattr(node, "values") and isinstance(node.values, dict):
            # Ensure values are appropriate type (e.g., filter out non-numeric if necessary)
            # For now, assume node.values contains the {period: value} mapping directly
            result[node_id] = node.values.copy()
            # Note: Original mixin didn't explicitly filter node types (like FinancialStatementItemNode)
            # It just checked for 'values'. Keep this behavior for now.
    return result


def import_data_from_dict(
    graph: Graph, data: dict[str, dict[str, float]], create_nodes: bool = True
) -> None:
    """Import data from a dictionary into the graph.

    Updates existing FinancialStatementItemNodes or creates new ones.

    Args:
        graph: The Graph instance to import data into.
        data: Dictionary mapping node names to period-value dictionaries.
              Format: {node_name: {period: value, ...}, ...}
        create_nodes: If True, create FinancialStatementItemNode if a node_name
                      from the data dict doesn't exist in the graph.
                      Defaults to True.

    Raises:
        ValueError: If the data format is invalid or periods mismatch.
        TypeError: If a node exists but is not a FinancialStatementItemNode
                 and create_nodes is False (or if modification is not supported).
    """
    # Validate data structure first
    all_periods = set()
    for node_name, period_values in data.items():
        if not isinstance(period_values, dict):
            raise TypeError(
                f"Invalid data format for node '{node_name}': expected dict, got {type(period_values)}"
            )
        for period, value in period_values.items():
            if not isinstance(value, (int, float)):
                raise TypeError(
                    f"Invalid value for node '{node_name}' period '{period}': expected number, got {type(value)}"
                )
            all_periods.add(period)

    # Add any new periods to the graph
    # Note: The original mixin checked if graph periods were empty or if data periods
    # were a subset. Here, we'll just add any missing periods found in the data.
    new_periods = sorted(list(all_periods - set(graph.periods)))
    if new_periods:
        graph.add_periods(new_periods)

    # Import data into nodes
    # Import FinancialStatementItemNode locally to avoid potential circular imports
    # and keep this specific to this function's purpose.
    from fin_statement_model.core.nodes import FinancialStatementItemNode

    for node_name, period_values in data.items():
        node = graph.get_node(node_name)

        if node is None:
            if create_nodes:
                # Create and add a new FinancialStatementItemNode
                new_node = FinancialStatementItemNode(name=node_name, values=period_values.copy())
                graph.add_node(new_node)
            else:
                # Node doesn't exist, and we shouldn't create it
                # Log a warning or raise an error, depending on desired behavior.
                # For now, let's just skip it.
                pass  # Or raise ValueError(f"Node '{node_name}' not found and create_nodes is False")
        elif isinstance(node, FinancialStatementItemNode):
            # Node exists and is the expected type, update its values
            if hasattr(node, "values") and isinstance(node.values, dict):
                node.values.update(period_values)
                # Optionally, clear cache for this node if values change
                if hasattr(node, "clear_cache"):
                    node.clear_cache()
            else:
                # This case should theoretically not happen if it's an FSItemNode
                # but handle defensively
                raise TypeError(
                    f"Node '{node_name}' is a FinancialStatementItemNode but lacks a 'values' dict."
                )
        else:
            # Node exists but is not a FinancialStatementItemNode
            # Decide how to handle this - raise error? log warning? skip?
            # Raising an error seems safest to avoid incorrect data overwrites.
            raise TypeError(
                f"Node '{node_name}' exists but is not a FinancialStatementItemNode. Cannot import dictionary data."
            )
