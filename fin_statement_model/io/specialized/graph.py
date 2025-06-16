"""Graph definition serialization and deserialization.

This module provides functionality to save and load complete graph definitions,
including all nodes, periods, and adjustments.
"""

import logging
from typing import Any, Optional, cast

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.graph.domain.adjustment import Adjustment
from fin_statement_model.core.node_factory import NodeFactory
from fin_statement_model.core.nodes import (
    Node,
)
from fin_statement_model.io.config.models import BaseReaderConfig, BaseWriterConfig
from fin_statement_model.io.core import (
    DataReader,
    DataWriter,
    register_reader,
    register_writer,
)
from fin_statement_model.io.exceptions import ReadError, WriteError

logger = logging.getLogger(__name__)

# Define a type for the serialized node dictionary for clarity
SerializedNode = dict[str, Any]


# ===== Reader Implementation =====


@register_reader("graph_definition_dict", schema=BaseReaderConfig)
class GraphDefinitionReader(DataReader):
    """Reads a graph definition dictionary to reconstruct a Graph object.

    Handles reconstructing nodes based on their serialized type and configuration,
    and loads adjustments.
    """

    def __init__(self, cfg: Optional[Any] = None) -> None:
        """Initialize the GraphDefinitionReader. Config currently unused."""
        self.cfg = cfg

    # --- Internal helper ---------------------------------------------------------------
    class _TempNode(Node):
        """Lightweight stand-in used only for dependency analysis during deserialization."""

        def __init__(self, name: str) -> None:
            super().__init__(name)
            # GraphTraverser expects a list[Node] attribute named ``inputs``
            self.inputs: list[Node] = []

        # Stub implementations required by the Node ABC ---------------------------------
        def calculate(self, period: str) -> float:
            return 0.0

        def to_dict(self) -> dict[str, Any]:
            # Serialization is irrelevant for the temp node – return minimal payload.
            return {}

    def _get_node_dependencies(self, node_def: dict[str, Any]) -> list[str]:
        """Extract dependency names from a node definition.

        Args:
            node_def: Dictionary containing node definition.

        Returns:
            List of dependency node names.
        """
        node_type = node_def.get("type")

        if node_type == "financial_statement_item":
            return []  # No dependencies
        elif node_type in ["calculation", "formula_calculation"]:
            return cast(list[str], node_def.get("inputs", []))
        elif node_type == "forecast":
            base_node_name = cast(Optional[str], node_def.get("base_node_name"))
            return [base_node_name] if base_node_name is not None else []
        elif node_type == "custom_calculation":
            return cast(list[str], node_def.get("inputs", []))
        else:
            # Default: inputs should be list[str]
            return cast(list[str], node_def.get("inputs", []))

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

        if (
            not isinstance(source, dict)
            or "periods" not in source
            or "nodes" not in source
        ):
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

            # 2. Reconstruct Nodes using topological sort of definitions -----------------
            nodes_dict = source.get("nodes", {})
            if not isinstance(nodes_dict, dict):
                raise ReadError("Invalid format: 'nodes' must be a dictionary.")

            # Build *temporary* graph comprised of minimal stub nodes so we can delegate
            # the topological ordering to `GraphTraverser`, the single source of truth
            # for graph algorithms in the core layer.
            from_nodes: dict[str, GraphDefinitionReader._TempNode] = {}
            temp_graph = Graph(periods=[])  # periods are irrelevant for dependency sort

            # First pass – create all stub nodes so dependencies can be resolved regardless of order
            for node_name in nodes_dict:
                temp_node = GraphDefinitionReader._TempNode(node_name)
                temp_graph.add_node(temp_node)
                from_nodes[node_name] = temp_node

            # Second pass – wire up the inputs attribute based on serialized dependencies
            for node_name, node_def in nodes_dict.items():
                dep_names = self._get_node_dependencies(node_def)
                try:
                    from_nodes[node_name].inputs = [from_nodes[d] for d in dep_names]
                except KeyError as missing:
                    raise ReadError(
                        message=f"Dependency '{missing.args[0]}' for node '{node_name}' not found in definitions.",
                        source="graph_definition_dict",
                    ) from None

            # Delegate ordering to GraphTraverser ----------------------------------------
            try:
                sorted_names: list[str] = temp_graph.traverser.topological_sort()
            except ValueError as e:
                raise ReadError(
                    message=str(e),
                    source="graph_definition_dict",
                ) from e

            # Create and add real nodes in topological order -----------------------------
            for node_name in sorted_names:
                node_def = nodes_dict[node_name]
                # mypy: graph.get_node() returns object – cast to Node mapping for factory
                existing_nodes_obj = {
                    name: graph.get_node(name) for name in graph.nodes
                }
                from typing import cast as _cast

                existing_nodes_cast = _cast(dict[str, Node], existing_nodes_obj)
                node = NodeFactory.create_from_dict(
                    node_def, context=existing_nodes_cast
                )
                graph.add_node(node)

            # 3. Load Adjustments --------------------------------------------------------
            adjustments_list = source.get("adjustments")  # Optional
            if adjustments_list is not None:
                if not isinstance(adjustments_list, list):
                    raise ReadError(
                        "Invalid format: 'adjustments' must be a list if present."
                    )

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
                    # Replace existing adjustments with deserialized list ----
                    graph.adjustment_manager.clear()
                    graph.adjustment_manager.add_many(deserialized_adjustments)
                    logger.info(
                        f"Loaded {len(deserialized_adjustments)} adjustments into the graph."
                    )

            logger.info(
                f"Successfully reconstructed graph with {len(graph.nodes)} nodes."
            )
            return graph

        except ReadError:  # Re-raise ReadErrors directly
            raise
        except Exception as e:
            logger.error(
                f"Failed to reconstruct graph from definition: {e}", exc_info=True
            )
            raise ReadError(
                message=f"Failed to reconstruct graph from definition: {e}",
                source="graph_definition_dict",
                reader_type="GraphDefinitionReader",
                original_error=e,
            ) from e


# ===== Writer Implementation =====


@register_writer("graph_definition_dict", schema=BaseWriterConfig)
class GraphDefinitionWriter(DataWriter):
    """Writes the full graph definition (nodes, periods, adjustments) to a dictionary.

    This writer serializes the structure and configuration of the graph, suitable
    for saving and reloading the entire model state.
    """

    def __init__(self, cfg: Optional[BaseWriterConfig] = None) -> None:
        """Initialize the GraphDefinitionWriter."""
        self.cfg = cfg

    def _serialize_node(self, node: Node) -> Optional[SerializedNode]:
        """Serialize a single node using its to_dict() method.

        Args:
            node: The node to serialize.

        Returns:
            Dictionary representation of the node, or None if serialization fails.
        """
        try:
            return node.to_dict()
        except Exception:
            logger.exception(f"Failed to serialize node '{node.name}'")
            logger.warning(f"Skipping node '{node.name}' due to serialization error.")
            return None

    def write(
        self, graph: Graph, target: Any = None, **kwargs: dict[str, Any]
    ) -> dict[str, Any]:
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

            # 2. Serialize Nodes using their to_dict() methods
            serialized_nodes: dict[str, SerializedNode] = {}
            for node_name in graph.nodes:
                node_obj_any = graph.get_node(node_name)
                if node_obj_any is None:
                    logger.warning(
                        "Node '%s' not found during serialization.", node_name
                    )
                    continue

                from typing import cast as _cast

                node_obj = _cast(Node, node_obj_any)
                node_dict = self._serialize_node(node_obj)
                if node_dict:
                    serialized_nodes[node_name] = node_dict
                else:
                    logger.warning(
                        f"Node '{node_name}' was not serialized due to errors."
                    )
            graph_definition["nodes"] = serialized_nodes

            # 3. Serialize Adjustments
            adjustments = graph.list_all_adjustments()
            serialized_adjustments = []
            for adj in adjustments:
                try:
                    # Use model_dump for Pydantic V2, ensure mode='json' for types like UUID/datetime
                    serialized_adjustments.append(adj.model_dump(mode="json"))
                except Exception as e:
                    logger.warning(
                        f"Failed to serialize adjustment {adj.id}: {e}. Skipping."
                    )
            graph_definition["adjustments"] = serialized_adjustments

            logger.info(
                f"Successfully created graph definition dictionary with {len(serialized_nodes)} nodes and {len(serialized_adjustments)} adjustments."
            )
            return graph_definition

        except Exception as e:
            logger.error(
                f"Failed to create graph definition dictionary: {e}", exc_info=True
            )
            raise WriteError(
                message=f"Failed to create graph definition dictionary: {e}",
                target="graph_definition_dict",
                writer_type="GraphDefinitionWriter",
                original_error=e,
            ) from e


# ===== Convenience Functions =====


def save_graph_definition(graph: Graph, filepath: str) -> None:
    """Save a graph definition to a JSON file.

    Args:
        graph: The graph to save.
        filepath: Path to the output JSON file.
    """
    import json

    writer = GraphDefinitionWriter()
    definition = writer.write(graph)

    with open(filepath, "w") as f:
        json.dump(definition, f, indent=2)

    logger.info(f"Saved graph definition to {filepath}")


def load_graph_definition(filepath: str) -> Graph:
    """Load a graph definition from a JSON file.

    Args:
        filepath: Path to the JSON file containing the graph definition.

    Returns:
        The reconstructed Graph object.
    """
    import json

    with open(filepath) as f:
        definition = json.load(f)

    reader = GraphDefinitionReader()
    graph = reader.read(definition)

    logger.info(f"Loaded graph definition from {filepath}")
    return graph


__all__ = [
    "GraphDefinitionReader",
    "GraphDefinitionWriter",
    "load_graph_definition",
    "save_graph_definition",
]
