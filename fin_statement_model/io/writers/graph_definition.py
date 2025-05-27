"""Writer for serializing the full graph definition to a dictionary."""

import logging
from typing import Any, Optional

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import (
    Node,
    FinancialStatementItemNode,
    CalculationNode,
    FormulaCalculationNode,
    # TODO: Add ForecastNode if/when it exists in core.nodes
)
from fin_statement_model.io.base import DataWriter
from fin_statement_model.io.registry import register_writer
from fin_statement_model.io.exceptions import WriteError
from fin_statement_model.core.node_factory import NodeFactory
from fin_statement_model.io.config.models import (
    BaseWriterConfig,
)  # Use base config for now

logger = logging.getLogger(__name__)

# Define a type for the serialized node dictionary for clarity
SerializedNode = dict[str, Any]


@register_writer("graph_definition_dict")
class GraphDefinitionWriter(DataWriter):
    """Writes the full graph definition (nodes, periods, adjustments) to a dictionary.

    This writer serializes the structure and configuration of the graph, suitable
    for saving and reloading the entire model state.
    """

    def __init__(self, cfg: Optional[BaseWriterConfig] = None) -> None:
        """Initialize the GraphDefinitionWriter."""
        self.cfg = cfg

    def _serialize_node(self, node: Node) -> Optional[SerializedNode]:
        """Serialize a single node into a dictionary definition."""
        node_def: SerializedNode = {"name": node.name}

        if isinstance(node, FinancialStatementItemNode):
            node_def["type"] = "financial_statement_item"
            # Store values directly, assuming they are serializable (float)
            node_def["values"] = node.values.copy()
            # Add other relevant attributes if needed (e.g., sign_convention)
        elif isinstance(node, FormulaCalculationNode):
            node_def["type"] = "formula_calculation"
            # Store the *actual* dependency node names
            node_def["inputs"] = node.get_dependencies()  # Store actual dependency names
            # Store the variable names used in the formula
            node_def["formula_variable_names"] = list(
                node.inputs.keys()  # These are the variable names used in the formula
            )  # Store input names (which are keys in formula node)
            node_def["formula"] = node.formula
            # Include metric info if it's a metric node
            if getattr(node, "metric_name", None):
                node_def["metric_name"] = node.metric_name
                node_def["metric_description"] = getattr(node, "metric_description", None)
            # Explicitly set the calculation type key for formula nodes
            node_def["calculation_type"] = "formula"
        elif isinstance(
            node, CalculationNode
        ):  # Catch general CalculationNodes after specific ones
            node_def["type"] = "calculation"
            # Assuming inputs are stored as a list of Nodes:
            node_def["inputs"] = node.get_dependencies()
            calc_instance = getattr(node, "calculation", None)
            if calc_instance:
                node_def["calculation_type_class"] = type(calc_instance).__name__
                # Find and save the type key
                inv_map = {v: k for k, v in NodeFactory._calculation_methods.items()}
                type_key = inv_map.get(type(calc_instance).__name__)
                if type_key:
                    node_def["calculation_type"] = type_key  # Save the type key
                else:
                    logger.warning(
                        f"Could not find type key in NodeFactory._calculation_methods for calculation class {type(calc_instance).__name__}"
                    )
            else:
                logger.warning(
                    f"CalculationNode '{node.name}' has no internal calculation instance to serialize type."
                )
        # TODO: Add elif for ForecastNode when defined
        # elif isinstance(node, ForecastNode):
        #     node_def["type"] = "forecast"
        #     node_def["inputs"] = [n.name for n in node.inputs]
        #     # Serialize forecast method key and config
        #     node_def["forecast_method"] = ...
        #     node_def["forecast_config"] = ...
        else:
            logger.warning(
                f"Node type '{type(node).__name__}' for node '{node.name}' is not explicitly handled by GraphDefinitionWriter. Skipping."
            )
            return None  # Skip nodes we don't know how to serialize

        return node_def

    def write(self, graph: Graph, target: Any = None, **kwargs: dict[str, Any]) -> dict[str, Any]:
        """Export the full graph definition to a dictionary.

        Args:
            graph (Graph): The Graph instance to serialize.
            target (Any): Ignored by this writer; the dictionary is returned directly.
            **kwargs: Currently unused.

        Returns:
            Dict[str, Any]: Dictionary representing the graph definition, including
                            periods, node definitions, and adjustments.

        Raises:
            WriteError: If an unexpected error occurs during export.
        """
        logger.info(f"Starting export of graph definition for: {graph!r}")
        graph_definition: dict[str, Any] = {
            "periods": [],
            "nodes": {},
            "adjustments": [],
        }

        try:
            # 1. Serialize Periods
            graph_definition["periods"] = list(graph.periods)

            # 2. Serialize Nodes
            serialized_nodes: dict[str, SerializedNode] = {}
            for node_name, node in graph.nodes.items():
                node_dict = self._serialize_node(node)
                if node_dict:
                    serialized_nodes[node_name] = node_dict
            graph_definition["nodes"] = serialized_nodes

            # 3. Serialize Adjustments
            adjustments = graph.list_all_adjustments()
            serialized_adjustments = []
            for adj in adjustments:
                try:
                    # Use model_dump for Pydantic V2, ensure mode='json' for types like UUID/datetime
                    serialized_adjustments.append(adj.model_dump(mode="json"))
                except Exception as e:
                    logger.warning(f"Failed to serialize adjustment {adj.id}: {e}. Skipping.")
            graph_definition["adjustments"] = serialized_adjustments

            logger.info(
                f"Successfully created graph definition dictionary with {len(serialized_nodes)} nodes and {len(serialized_adjustments)} adjustments."
            )
            return graph_definition

        except Exception as e:
            logger.error(f"Failed to create graph definition dictionary: {e}", exc_info=True)
            raise WriteError(
                message=f"Failed to create graph definition dictionary: {e}",
                target="graph_definition_dict",
                writer_type="GraphDefinitionWriter",
                original_error=e,
            ) from e
