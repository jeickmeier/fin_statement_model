"""Reader for reconstructing a Graph from a definition dictionary."""

import logging
from typing import Any, Optional

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.adjustments.models import Adjustment
from fin_statement_model.io.base import DataReader
from fin_statement_model.io.registry import register_reader
from fin_statement_model.io.exceptions import ReadError
from fin_statement_model.core.errors import NodeError, ConfigurationError

logger = logging.getLogger(__name__)

# Define a type for the serialized node dictionary for clarity
SerializedNode = dict[str, Any]


@register_reader("graph_definition_dict")
class GraphDefinitionReader(DataReader):
    """Reads a graph definition dictionary to reconstruct a Graph object.

    Handles reconstructing nodes based on their serialized type and configuration,
    and loads adjustments.
    """

    def __init__(self, cfg: Optional[Any] = None) -> None:
        """Initialize the GraphDefinitionReader. Config currently unused."""
        self.cfg = cfg

    def _add_nodes_iteratively(self, graph: Graph, nodes_dict: dict[str, SerializedNode]) -> None:
        """Add nodes to the graph, handling potential dependency order issues."""
        nodes_to_add = nodes_dict.copy()
        added_nodes: set[str] = set()
        max_passes = len(nodes_to_add) + 1  # Failsafe against infinite loops
        passes = 0

        while nodes_to_add and passes < max_passes:
            added_in_pass = 0
            pending_nodes = nodes_to_add.copy()
            nodes_to_add = {}

            for node_name, node_def in pending_nodes.items():
                node_type = node_def.get("type")
                # Get actual dependency names (might differ from formula vars)
                dependency_names = node_def.get("inputs", [])

                # Check if all dependencies are already added
                dependencies_met = all(dep_name in added_nodes for dep_name in dependency_names)

                if dependencies_met:
                    try:
                        # Logic to add the node based on its type
                        if node_type == "financial_statement_item":
                            graph.add_financial_statement_item(
                                name=node_name, values=node_def.get("values", {})
                            )
                        elif node_type == "formula_calculation":
                            # Always reconstruct using add_calculation for formula type.
                            # The metric_name attribute will be preserved if present.
                            formula_str = node_def.get("formula")
                            if not formula_str:
                                logger.error(
                                    f"Cannot reconstruct FormulaCalculationNode '{node_name}': missing formula string."
                                )
                                continue  # Skip node

                            graph.add_calculation(
                                name=node_name,
                                input_names=dependency_names,
                                operation_type="formula",
                                formula_variable_names=node_def.get("formula_variable_names"),
                                formula=formula_str,
                                metric_name=node_def.get("metric_name"),
                                metric_description=node_def.get("metric_description")
                            )
                        elif node_type == "calculation":
                            # Reconstruct generic CalculationNode using the saved type key
                            calc_type_key = node_def.get("calculation_type")
                            if not calc_type_key:
                                logger.error(f"Missing 'calculation_type' key for node '{node_name}'. Skipping.")
                                continue

                            # TODO: Deserialize calculation_args if they were saved
                            calculation_args = node_def.get("calculation_args", {})

                            logger.warning(
                                f"Reconstructing generic CalculationNode '{node_name}' with type '{calc_type_key}'. Argument handling TBD."
                            )
                            graph.add_calculation(
                                name=node_name,
                                input_names=dependency_names,
                                operation_type=calc_type_key,
                                **calculation_args
                            )
                        # TODO: Add elif for "forecast" type
                        else:
                            logger.warning(
                                f"Unknown node type '{node_type}' for node '{node_name}' during deserialization. Skipping."
                            )
                            # Don't add to added_nodes if skipped
                            continue

                        added_nodes.add(node_name)
                        added_in_pass += 1
                        logger.debug(f"Added node '{node_name}' in pass {passes + 1}.")

                    except (NodeError, ConfigurationError, ValueError, TypeError):
                        # Log error but try to continue with other nodes
                        logger.exception(f"Failed to add node '{node_name}' during iterative build")
                        # Keep it in nodes_to_add to potentially retry if it was a temporary dependency issue
                        # or if error handling allows partial graph load.
                        # For now, let's keep it for retry, but could decide to fail hard.
                        nodes_to_add[node_name] = node_def
                else:
                    # Dependencies not met, keep for next pass
                    nodes_to_add[node_name] = node_def

            if added_in_pass == 0 and nodes_to_add:
                # No progress made in this pass, indicates missing nodes or cycle
                missing_deps = set()
                for node_name, node_def in nodes_to_add.items():
                    for dep in node_def.get("inputs", []):
                        if (
                            dep not in added_nodes and dep not in nodes_to_add
                        ):  # Check if dep itself is missing entirely
                            missing_deps.add(dep)
                error_msg = f"Failed to add all nodes. Possible missing dependencies ({missing_deps}) or circular dependency in definition for nodes: {list(nodes_to_add.keys())}"
                logger.error(error_msg)
                raise ReadError(error_msg, source="graph_definition_dict")

            passes += 1

        if nodes_to_add:
            logger.error(
                f"Failed to add the following nodes after {max_passes} passes: {list(nodes_to_add.keys())}"
            )
            raise ReadError(
                f"Failed to reconstruct graph, could not add nodes: {list(nodes_to_add.keys())}",
                source="graph_definition_dict",
            )

    def read(self, source: dict[str, Any], **kwargs: Any) -> Graph:
        """Reconstruct a Graph instance from its definition dictionary.

        Args:
            source: Dictionary containing the graph definition (periods, nodes, adjustments).
            **kwargs: Currently unused.

        Returns:
            A new Graph instance populated from the definition.

        Raises:
            ReadError: If the source format is invalid or graph reconstruction fails.
        """
        logger.info("Starting graph reconstruction from definition dictionary.")

        if not isinstance(source, dict) or "periods" not in source or "nodes" not in source:
            raise ReadError(
                message="Invalid source format for GraphDefinitionReader. Expected dict with 'periods' and 'nodes' keys.",
                source="graph_definition_dict",
                reader_type="GraphDefinitionReader",
            )

        try:
            # 1. Initialize Graph with Periods
            periods = source.get("periods", [])
            if not isinstance(periods, list):
                raise ReadError("Invalid format: 'periods' must be a list.")
            graph = Graph(periods=periods)

            # 2. Reconstruct Nodes iteratively
            nodes_dict = source.get("nodes", {})
            if not isinstance(nodes_dict, dict):
                raise ReadError("Invalid format: 'nodes' must be a dictionary.")
            self._add_nodes_iteratively(graph, nodes_dict)

            # 3. Load Adjustments
            adjustments_list = source.get("adjustments")  # Optional
            if adjustments_list is not None:
                if not isinstance(adjustments_list, list):
                    raise ReadError("Invalid format: 'adjustments' must be a list if present.")

                deserialized_adjustments = []
                for i, adj_dict in enumerate(adjustments_list):
                    try:
                        # Use model_validate for Pydantic V2
                        adj = Adjustment.model_validate(adj_dict)
                        deserialized_adjustments.append(adj)
                    except Exception:
                        # Log error but try to continue with other nodes
                        logger.exception(
                            f"Failed to deserialize adjustment at index {i}: {adj_dict}. Skipping."
                        )
                        # Optionally raise ReadError here to fail fast

                if deserialized_adjustments:
                    graph.adjustment_manager.load_adjustments(deserialized_adjustments)
                    logger.info(
                        f"Loaded {len(deserialized_adjustments)} adjustments into the graph."
                    )

            logger.info(f"Successfully reconstructed graph with {len(graph.nodes)} nodes.")
            return graph

        except ReadError:  # Re-raise ReadErrors directly
            raise
        except Exception as e:
            logger.error(f"Failed to reconstruct graph from definition: {e}", exc_info=True)
            raise ReadError(
                message=f"Failed to reconstruct graph from definition: {e}",
                source="graph_definition_dict",
                reader_type="GraphDefinitionReader",
                original_error=e,
            ) from e
