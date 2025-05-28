"""Graph definition serialization and deserialization.

This module provides functionality to save and load complete graph definitions,
including all nodes, periods, and adjustments.
"""

import logging
from typing import Any, Optional

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.adjustments.models import Adjustment
from fin_statement_model.core.nodes import (
    Node,
    FinancialStatementItemNode,
    CalculationNode,
    FormulaCalculationNode,
)
from fin_statement_model.core.nodes.forecast_nodes import (
    ForecastNode,
    FixedGrowthForecastNode,
    CurveGrowthForecastNode,
    StatisticalGrowthForecastNode,
    AverageValueForecastNode,
    AverageHistoricalGrowthForecastNode,
    CustomGrowthForecastNode,
)
from fin_statement_model.core.errors import NodeError, ConfigurationError
from fin_statement_model.core.node_factory import NodeFactory
from fin_statement_model.io.core import DataReader, DataWriter, register_reader, register_writer
from fin_statement_model.io.exceptions import ReadError, WriteError
from fin_statement_model.io.config.models import BaseWriterConfig

logger = logging.getLogger(__name__)

# Define a type for the serialized node dictionary for clarity
SerializedNode = dict[str, Any]


# ===== Reader Implementation =====


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

                # For forecast nodes, the dependency is the base node
                if node_type == "forecast":
                    base_node_name = node_def.get("base_node_name")
                    if base_node_name:
                        dependency_names = [base_node_name]

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
                                metric_description=node_def.get("metric_description"),
                            )
                        elif node_type == "calculation":
                            # Reconstruct generic CalculationNode using the saved type key
                            calc_type_key = node_def.get("calculation_type")
                            if not calc_type_key:
                                logger.error(
                                    f"Missing 'calculation_type' key for node '{node_name}'. Skipping."
                                )
                                continue

                            # Retrieve calculation_args if they were saved
                            calculation_args = node_def.get("calculation_args", {})

                            # Special handling for formula type to ensure formula_variable_names is passed correctly
                            if calc_type_key == "formula" and "formula_variable_names" in node_def:
                                # Pass formula_variable_names as a separate parameter, not in calculation_args
                                formula_variable_names = node_def.get("formula_variable_names")
                                logger.debug(
                                    f"Reconstructing CalculationNode '{node_name}' with type '{calc_type_key}', "
                                    f"formula_variable_names: {formula_variable_names}, and args: {calculation_args}"
                                )
                                graph.add_calculation(
                                    name=node_name,
                                    input_names=dependency_names,
                                    operation_type=calc_type_key,
                                    formula_variable_names=formula_variable_names,
                                    **calculation_args,
                                )
                            else:
                                logger.debug(
                                    f"Reconstructing CalculationNode '{node_name}' with type '{calc_type_key}' and args: {calculation_args}"
                                )
                                graph.add_calculation(
                                    name=node_name,
                                    input_names=dependency_names,
                                    operation_type=calc_type_key,
                                    **calculation_args,
                                )
                        elif node_type == "forecast":
                            # Reconstruct ForecastNode
                            base_node_name = node_def.get("base_node_name")
                            base_period = node_def.get("base_period")
                            forecast_periods = node_def.get("forecast_periods")
                            forecast_type = node_def.get("forecast_type")
                            growth_params = node_def.get(
                                "growth_params", 0.0
                            )  # Default to 0.0 if not provided

                            if not all(
                                [
                                    base_node_name,
                                    base_period,
                                    forecast_periods,
                                    forecast_type,
                                ]
                            ):
                                logger.error(
                                    f"Missing required fields for forecast node '{node_name}'. Skipping."
                                )
                                continue

                            # Get the base node from the graph
                            base_node = graph.nodes.get(base_node_name) if base_node_name else None
                            if not base_node:
                                logger.error(
                                    f"Base node '{base_node_name}' not found for forecast node '{node_name}'. Skipping."
                                )
                                continue

                            # Handle special cases where growth_params might not be serializable
                            if forecast_type in ["statistical", "custom"]:
                                logger.warning(
                                    f"Forecast node '{node_name}' of type '{forecast_type}' uses non-serializable "
                                    f"parameters. Using default values. Manual reconstruction may be needed."
                                )
                                if forecast_type == "statistical":
                                    # Use a default function that returns 0 growth
                                    def default_statistical_growth() -> float:
                                        return 0.0

                                    growth_params = default_statistical_growth
                                elif forecast_type == "custom":
                                    # Use a default function that returns 0 growth
                                    def default_custom_growth(
                                        period: str, prev_period: str, prev_value: float
                                    ) -> float:
                                        return 0.0

                                    growth_params = default_custom_growth
                            elif forecast_type in ["average", "historical_growth"]:
                                # These types don't need growth_params
                                growth_params = None

                            # Create the forecast node
                            try:
                                # Ensure all required parameters are not None
                                if (
                                    not isinstance(base_period, str)
                                    or not isinstance(forecast_periods, list)
                                    or not isinstance(forecast_type, str)
                                ):
                                    logger.error(
                                        f"Invalid types for forecast node '{node_name}' parameters. Skipping."
                                    )
                                    continue

                                forecast_node = NodeFactory.create_forecast_node(
                                    name=node_name,
                                    base_node=base_node,
                                    base_period=base_period,
                                    forecast_periods=forecast_periods,
                                    forecast_type=forecast_type,
                                    growth_params=growth_params,
                                )
                                graph.add_node(forecast_node)
                                logger.debug(
                                    f"Added forecast node '{node_name}' of type '{forecast_type}'."
                                )
                            except Exception:
                                logger.exception(
                                    f"Failed to create forecast node '{node_name}'. Skipping."
                                )
                                continue
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
                    deps = node_def.get("inputs", [])
                    if node_def.get("type") == "forecast":
                        deps = [node_def.get("base_node_name", "")]
                    for dep in deps:
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


# ===== Writer Implementation =====


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
                node.inputs_dict.keys()  # Use inputs_dict instead of inputs for FormulaCalculationNode
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

                    # Extract calculation arguments based on the calculation type
                    calculation_args = {}

                    # WeightedAverageCalculation has weights attribute
                    if type_key == "weighted_average" and hasattr(calc_instance, "weights"):
                        calculation_args["weights"] = calc_instance.weights

                    # FormulaCalculation has formula and input_variable_names
                    elif type_key == "formula" and hasattr(calc_instance, "formula"):
                        calculation_args["formula"] = calc_instance.formula
                        if hasattr(calc_instance, "input_variable_names"):
                            # Store input_variable_names at the node level for proper deserialization
                            node_def["formula_variable_names"] = calc_instance.input_variable_names

                    # CustomFormulaCalculation has formula_function (not easily serializable)
                    elif type_key == "custom_formula":
                        logger.warning(
                            f"CustomFormulaCalculation for node '{node.name}' uses a Python function "
                            "which cannot be serialized. This node will need manual reconstruction."
                        )

                    # Store calculation args if any were extracted
                    if calculation_args:
                        node_def["calculation_args"] = calculation_args
                else:
                    logger.warning(
                        f"Could not find type key in NodeFactory._calculation_methods for calculation class {type(calc_instance).__name__}"
                    )
            else:
                logger.warning(
                    f"CalculationNode '{node.name}' has no internal calculation instance to serialize type."
                )
        elif isinstance(node, ForecastNode):
            node_def["type"] = "forecast"
            node_def["base_node_name"] = node.input_node.name
            node_def["base_period"] = node.base_period
            node_def["forecast_periods"] = node.forecast_periods

            # Determine the forecast type based on the node class
            if isinstance(node, FixedGrowthForecastNode):
                node_def["forecast_type"] = "fixed"
                node_def["growth_params"] = node.growth_rate
            elif isinstance(node, CurveGrowthForecastNode):
                node_def["forecast_type"] = "curve"
                node_def["growth_params"] = node.growth_rates
            elif isinstance(node, StatisticalGrowthForecastNode):
                node_def["forecast_type"] = "statistical"
                logger.warning(
                    f"StatisticalGrowthForecastNode '{node.name}' uses a distribution callable "
                    "which cannot be serialized. This node will need manual reconstruction."
                )
                # We can't serialize the callable, so we'll skip growth_params
            elif isinstance(node, AverageValueForecastNode):
                node_def["forecast_type"] = "average"
                # No growth_params needed for average value
            elif isinstance(node, AverageHistoricalGrowthForecastNode):
                node_def["forecast_type"] = "historical_growth"
                # No growth_params needed for historical growth
            elif isinstance(node, CustomGrowthForecastNode):
                node_def["forecast_type"] = "custom"
                logger.warning(
                    f"CustomGrowthForecastNode '{node.name}' uses a growth function "
                    "which cannot be serialized. This node will need manual reconstruction."
                )
                # We can't serialize the callable, so we'll skip growth_params
            else:
                logger.warning(
                    f"Unknown ForecastNode subclass '{type(node).__name__}' for node '{node.name}'. "
                    "Using generic forecast serialization."
                )
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
