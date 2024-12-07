from .metrics import METRIC_DEFINITIONS
from .nodes import MetricCalculationNode

def add_metric(graph, metric_name: str, node_name: str = None, _processing=None):
    """
    Add a metric calculation node to the graph based on predefined metric definitions.

    This function adds a new metric node to the financial statement graph, handling all dependencies
    and ensuring proper calculation order. It will recursively add any required metric nodes that
    don't yet exist in the graph.

    Args:
        graph: The financial statement graph to add the metric to
        metric_name: The name of the metric to add (must exist in METRIC_DEFINITIONS)
        node_name: Optional custom name for the node (defaults to metric_name)
        _processing: Internal set to detect cyclic dependencies (do not set manually)

    Raises:
        ValueError: If the metric is not found in METRIC_DEFINITIONS
        ValueError: If a required input node is missing from the graph
        ValueError: If a cyclic dependency is detected between metrics

    Example:
        # Add gross profit metric
        add_metric(graph, "gross_profit")

        # Add net profit margin (will automatically add gross_profit if needed)
        add_metric(graph, "net_profit_margin")

        # Add metric with custom node name
        add_metric(graph, "gross_profit", node_name="adjusted_gross_profit")
    """
    if metric_name not in METRIC_DEFINITIONS:
        raise ValueError(f"Metric '{metric_name}' not found in METRIC_DEFINITIONS.")

    if _processing is None:
        _processing = set()

    if metric_name in _processing:
        raise ValueError(f"Cyclic dependency detected for metric '{metric_name}'.")
    _processing.add(metric_name)

    definition = METRIC_DEFINITIONS[metric_name]
    required_inputs = definition['inputs']

    for inp in required_inputs:
        node = graph.get_node(inp)
        if node is None:
            if inp in METRIC_DEFINITIONS:
                # It's another metric, add it first
                add_metric(graph, inp, inp, _processing=_processing)
            else:
                # It's a raw data node - must be present before adding metric
                if graph.get_node(inp) is None:
                    raise ValueError(
                        f"Required input '{inp}' for metric '{metric_name}' not found. "
                        f"Please ensure '{inp}' is added as a financial statement item node."
                    )

    metric_node_name = node_name or metric_name
    if graph.get_node(metric_node_name) is not None:
        _processing.remove(metric_name)
        return

    metric_node = MetricCalculationNode(metric_node_name, metric_name, graph)
    graph.add_node(metric_node)

    _processing.remove(metric_name)
