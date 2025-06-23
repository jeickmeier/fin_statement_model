"""Graph definition serialization and deserialization.

This module provides functionality to save and load complete graph definitions,
including all nodes, periods, and adjustments. The serialized format is a
JSON-compatible dictionary, making it easy to store and transfer model states.
"""

import logging
from pathlib import Path
from typing import Any, cast

from fin_statement_model.core.adjustments.models import Adjustment
from fin_statement_model.core.graph import Graph
from fin_statement_model.core.node_factory import NodeFactory
from fin_statement_model.core.nodes import (
    Node,
)
from fin_statement_model.io.config.models import (
    GraphDefinitionReaderConfig,
    GraphDefinitionWriterConfig,
)
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


@register_reader("graph_definition_dict", schema=GraphDefinitionReaderConfig)
class GraphDefinitionReader(DataReader):
    """Reads a graph definition dictionary to reconstruct a Graph object.

    Handles reconstructing nodes based on their serialized type and configuration,
    and loads adjustments.
    """

    def __init__(self, cfg: GraphDefinitionReaderConfig | None = None) -> None:
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
            _ = period  # Parameter intentionally unused
            return 0.0

        def to_dict(self) -> dict[str, Any]:
            # Serialization is irrelevant for the temp node - return minimal payload.
            return {}

        @classmethod
        def from_dict(
            cls, data: dict[str, Any], context: dict[str, Node] | None = None
        ) -> "GraphDefinitionReader._TempNode":
            """Construct a _TempNode from a dictionary payload.

            This is only to satisfy the Node ABC for mypy/static type checkers; the
            deserialiser never actually needs to recreate temporary nodes from a
            serialized form, so the method raises *NotImplementedError* at
            runtime.
            """
            raise NotImplementedError("_TempNode is an internal stub; it cannot be deserialized.")

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
            return cast("list[str]", node_def.get("inputs", []))
        elif node_type == "forecast":
            base_node_name = cast("str | None", node_def.get("base_node_name"))
            return [base_node_name] if base_node_name is not None else []
        elif node_type == "custom_calculation":
            return cast("list[str]", node_def.get("inputs", []))
        else:
            # Default: inputs should be list[str]
            return cast("list[str]", node_def.get("inputs", []))

    # --- Private helpers -------------------------------------------------------------
    def _load_adjustments(
        self,
        graph: Graph,
        adjustments_list: Any,
    ) -> None:
        """Validate, deserialize, and load adjustments onto *graph*.

        Args:
            graph: The target ``Graph`` instance.
            adjustments_list: Raw adjustments payload extracted from the source
                definition. *None* indicates that the key was absent.

        Raises:
            ReadError: If *adjustments_list* is not ``None`` or ``list``.
        """
        if adjustments_list is None:
            # Nothing to do - early exit to avoid counting extra statements in the
            # caller and keep ``read`` lean.
            return

        if not isinstance(adjustments_list, list):
            raise ReadError("Invalid format: 'adjustments' must be a list if present.")

        deserialized_adjustments: list[Adjustment] = []
        for i, adj_dict in enumerate(adjustments_list):
            try:
                # Use model_validate for Pydantic V2
                deserialized_adjustments.append(Adjustment.model_validate(adj_dict))
            except Exception:
                # Log error but continue processing remaining adjustments
                logger.exception(
                    "Failed to deserialize adjustment at index %s: %s. Skipping.",
                    i,
                    adj_dict,
                )

        if deserialized_adjustments:
            graph.adjustment_manager.load_adjustments(deserialized_adjustments)
            logger.info(
                "Loaded %s adjustments into the graph.",
                len(deserialized_adjustments),
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
        _ = kwargs  # Parameters intentionally unused
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

            # 2. Reconstruct Nodes using topological sort of definitions -----------------
            nodes_dict = source.get("nodes", {})
            if not isinstance(nodes_dict, dict):
                raise ReadError("Invalid format: 'nodes' must be a dictionary.")

            # Build *temporary* graph comprised of minimal stub nodes so we can delegate
            # the topological ordering to `GraphTraverser`, the single source of truth
            # for graph algorithms in the core layer.
            from_nodes: dict[str, GraphDefinitionReader._TempNode] = {}
            temp_graph = Graph(periods=[])  # periods are irrelevant for dependency sort

            # First pass - create all stub nodes so dependencies can be resolved regardless of order
            for node_name in nodes_dict:
                temp_node = GraphDefinitionReader._TempNode(node_name)
                temp_graph.add_node(temp_node)
                from_nodes[node_name] = temp_node

            # Second pass - wire up the inputs attribute based on serialized dependencies
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
                existing_nodes = {name: graph.nodes[name] for name in graph.nodes}
                node = NodeFactory.create_from_dict(node_def, context=existing_nodes)
                graph.add_node(node)

            # 3. Load Adjustments --------------------------------------------------------
            self._load_adjustments(graph, source.get("adjustments"))

            logger.info("Successfully reconstructed graph with %s nodes.", len(graph.nodes))
        except ReadError:  # Re-raise ReadErrors directly
            raise
        except Exception as e:
            logger.exception("Failed to reconstruct graph from definition")
            raise ReadError(
                message=f"Failed to reconstruct graph from definition: {e}",
                source="graph_definition_dict",
                reader_type="GraphDefinitionReader",
                original_error=e,
            ) from e
        else:
            return graph


# ===== Writer Implementation =====


@register_writer("graph_definition_dict", schema=GraphDefinitionWriterConfig)
class GraphDefinitionWriter(DataWriter):
    """Writes the full graph definition (nodes, periods, adjustments) to a dictionary.

    This writer serializes the structure and configuration of the graph, suitable
    for saving and reloading the entire model state.
    """

    def __init__(self, cfg: GraphDefinitionWriterConfig | None = None) -> None:
        """Initialize the GraphDefinitionWriter."""
        self.cfg = cfg

    def _serialize_node(self, node: Node) -> SerializedNode | None:
        """Serialize a single node using its to_dict() method.

        Args:
            node: The node to serialize.

        Returns:
            Dictionary representation of the node, or None if serialization fails.
        """
        try:
            return node.to_dict()
        except Exception:
            logger.exception("Failed to serialize node '%s'", node.name)
            logger.warning("Skipping node '%s' due to serialization error.", node.name)
            return None

    def write(self, graph: Graph, target: Any = None, **kwargs: dict[str, Any]) -> dict[str, Any]:
        """Export the full graph definition to a dictionary.

        Args:
            graph: The Graph instance to serialize.
            target: Ignored by this writer; the dictionary is returned directly.
            **kwargs: Currently unused.

        Returns:
            Dictionary representing the graph definition, including periods,
            node definitions, and adjustments.

        Raises:
            WriteError: If an unexpected error occurs during export.
        """
        _ = (target, kwargs)  # Parameters intentionally unused
        logger.info("Starting export of graph definition for: %r", graph)
        graph_definition: dict[str, Any] = {
            "periods": [],
            "nodes": {},
            "adjustments": [],
        }

        # Determine strictness: runtime kwarg overrides config default
        strict_cfg = True
        if isinstance(self.cfg, GraphDefinitionWriterConfig):
            strict_cfg = self.cfg.strict
        strict = kwargs.get("strict", strict_cfg)

        try:
            # 1. Serialize Periods
            graph_definition["periods"] = list(graph.periods)

            # 2. Serialize Nodes using their to_dict() methods
            serialized_nodes: dict[str, SerializedNode] = {}
            for node_name, node in graph.nodes.items():
                node_dict = self._serialize_node(node)
                if node_dict is None:
                    if strict:
                        raise WriteError(
                            message=f"Failed to serialize node '{node_name}'. Aborting export (strict mode).",
                            target="graph_definition_dict",
                            writer_type="GraphDefinitionWriter",
                        )
                    logger.warning(
                        "Skipping node '%s' due to serialization error (strict=%s).",
                        node_name,
                        strict,
                    )
                else:
                    serialized_nodes[node_name] = node_dict

            # Persist nodes into graph_definition
            graph_definition["nodes"] = serialized_nodes

            # 3. Serialize Adjustments
            adjustments = graph.list_all_adjustments()
            serialized_adjustments = []
            for adj in adjustments:
                try:
                    # Use model_dump for Pydantic V2, ensure mode='json' for types like UUID/datetime
                    serialized_adjustments.append(adj.model_dump(mode="json"))
                except (ValueError, TypeError) as exc:
                    logger.warning(
                        "Failed to serialize adjustment %s: %s. Skipping.",
                        adj.id,
                        exc,
                    )
            graph_definition["adjustments"] = serialized_adjustments

            logger.info(
                "Successfully created graph definition dictionary with %s nodes and %s adjustments.",
                len(serialized_nodes),
                len(serialized_adjustments),
            )
        except Exception as e:
            logger.exception("Failed to create graph definition dictionary")
            raise WriteError(
                message=f"Failed to create graph definition dictionary: {e}",
                target="graph_definition_dict",
                writer_type="GraphDefinitionWriter",
                original_error=e,
            ) from e
        else:
            return graph_definition


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

    path = Path(filepath)
    with path.open("w", encoding="utf-8") as f:
        json.dump(definition, f, indent=2)

    logger.info("Saved graph definition to %s", filepath)


def load_graph_definition(filepath: str) -> Graph:
    """Load a graph definition from a JSON file.

    Args:
        filepath: Path to the JSON file containing the graph definition.

    Returns:
        The reconstructed Graph object.
    """
    import json

    path = Path(filepath)
    with path.open(encoding="utf-8") as f:
        definition = json.load(f)

    reader = GraphDefinitionReader()
    graph = reader.read(definition)

    logger.info("Loaded graph definition from %s", filepath)
    return graph


__all__ = [
    "GraphDefinitionReader",
    "GraphDefinitionWriter",
    "load_graph_definition",
    "save_graph_definition",
]
