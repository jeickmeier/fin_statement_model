"""Core graph implementation for `fin_statement_model`.

The `Graph` class orchestrates the construction and evaluation of directed
graphs representing financial statements. It provides methods for:

* Adding data (`FinancialStatementItemNode`) and calculation nodes
* Managing time periods and ensuring uniqueness/sorting
* Performing calculations, forecasting, and applying adjustments
* Inspecting and mutating graph structure via the `manipulator` and
  `traverser` sub-APIs

Example:
    >>> from fin_statement_model.core.graph.graph import Graph
    >>> g = Graph(periods=["2023"])
    >>> g.add_financial_statement_item("Revenue", {"2023": 100.0})
    >>> g.calculate("Revenue", "2023")
    100.0
"""

import logging
from typing import Any, Optional, overload, Literal
from collections.abc import Callable
from uuid import UUID

from fin_statement_model.core.node_factory import NodeFactory
from fin_statement_model.core.nodes import (
    Node,
    FinancialStatementItemNode,
    CalculationNode,
    is_calculation_node,
)
from fin_statement_model.core.errors import (
    NodeError,
    ConfigurationError,
    CalculationError,
    CircularDependencyError,
)
from fin_statement_model.core.metrics import metric_registry
from fin_statement_model.core.calculations import Registry
from fin_statement_model.core.graph.manipulator import GraphManipulator
from fin_statement_model.core.graph.traverser import GraphTraverser
from fin_statement_model.core.adjustments.models import (
    Adjustment,
    AdjustmentType,
    AdjustmentTag,
    DEFAULT_SCENARIO,
    AdjustmentFilterInput,
)
from fin_statement_model.core.adjustments.manager import AdjustmentManager


# Configure logging
logger = logging.getLogger(__name__)

__all__ = ["Graph"]


class Graph:
    """Core directed-graph abstraction for financial statement modeling.

    The `Graph` class orchestrates construction, mutation, traversal,
    calculation, and forecasting of nodes representing financial statement
    items and metrics. It exposes high-level convenience methods for
    building and evaluating the model, while delegating structural
    mutations and read-only inspections to its sub-APIs.

    Attributes:
        _nodes: Mapping of node names (str) to Node instances registered in the graph.
        _periods: Sorted list of unique period identifiers (str) managed by the graph.
        _cache: Nested dict caching calculated float values per node per period.
        _node_factory: `NodeFactory` instance for creating new nodes.
        manipulator: `GraphManipulator` for structural mutations (add/remove/replace nodes, set values).
        traverser: `GraphTraverser` for read-only traversal, validation, and cycle detection.
        adjustment_manager: `AdjustmentManager` handling discretionary adjustments.
    """

    def __init__(self, periods: Optional[list[str]] = None):
        """Initialize a new `Graph` instance.

        Sets up core components: node registry, period list, calculation cache,
        node factory, and sub-API instances (`manipulator`, `traverser`,
        `adjustment_manager`).

        Args:
            periods: Optional list of period identifiers (str) to initialize.
                     Periods are automatically deduplicated and sorted.

        Raises:
            TypeError: If `periods` is not a list of strings.

        Examples:
            >>> from fin_statement_model.core.graph.graph import Graph
            >>> g = Graph()
            >>> g.periods
            []
            >>> g = Graph(periods=["2024", "2023"])
            >>> g.periods
            ["2023", "2024"]
            >>> Graph(periods="2023")  # raises TypeError
        """
        # No super().__init__() needed as mixins don't have __init__
        # and GraphCore is removed.

        self._nodes: dict[str, Node] = {}

        # Initialize core attributes for periods, cache, and node factory
        self._periods: list[str] = []
        self._cache: dict[str, dict[str, float]] = {}
        self._node_factory: NodeFactory = NodeFactory()

        # Handle initial periods directly
        if periods:
            if not isinstance(periods, list):
                raise TypeError("Initial periods must be a list")
            self.add_periods(periods)

        self.manipulator = GraphManipulator(self)
        self.traverser = GraphTraverser(self)

        # --- Adjustment Manager Integration ---
        self.adjustment_manager = AdjustmentManager()
        # --- End Adjustment Manager Integration ---

    @property
    def nodes(self) -> dict[str, Node]:
        """Provide access to the dictionary of all nodes in the graph.

        Returns:
            A dictionary where keys are node names (str) and values are
            `Node` objects. This dictionary represents the shared node registry.

        Examples:
            >>> graph = Graph()
            >>> item_node = graph.add_financial_statement_item("Revenue", {"2023": 100})
            >>> logger.info(list(graph.nodes.keys()))
            >>> logger.info(graph.nodes["Revenue"] == item_node)
        """
        return self._nodes

    @property
    def periods(self) -> list[str]:
        """Retrieve the list of time periods currently managed by the graph.

        Returns:
            A sorted list of unique time period strings managed by the graph.

        Examples:
            >>> graph = Graph(periods=["2024", "2023"])
            >>> logger.info(graph.periods)
            >>> graph.add_periods(["2025"])
            >>> logger.info(graph.periods)
        """
        return self._periods

    def add_periods(self, periods: list[str]) -> None:
        """Add new time periods to the graph.

        Update the internal period list, ensuring uniqueness and sorting.

        Args:
            periods: A list of strings representing the time periods to add.

        Raises:
            TypeError: If `periods` is not a list.
        """
        if not isinstance(periods, list):
            raise TypeError("Periods must be provided as a list.")
        # Ensure unique and sorted periods
        combined = set(self._periods).union(periods)
        self._periods = sorted(combined)
        logger.debug(f"Added periods {periods}; current periods: {self._periods}")

    def add_calculation(
        self,
        name: str,
        input_names: list[str],
        operation_type: str,
        formula_variable_names: Optional[list[str]] = None,
        **calculation_kwargs: Any,
    ) -> Node:
        """Add a new calculation node to the graph using the node factory.

        Resolve input node names to Node objects, create a CalculationNode,
        register it in the graph, and return it.

        Args:
            name: Unique name for the calculation node.
            input_names: List of node names to use as inputs.
            operation_type: Calculation type key (e.g., 'addition').
            formula_variable_names: Optional list of variable names used in the formula
                string, required if creating a FormulaCalculationNode via this method.
            **calculation_kwargs: Additional parameters for the calculation constructor.

        Returns:
            The created calculation node.

        Raises:
            NodeError: If any input node name does not exist.
            ValueError: If the name is invalid or creation fails.
            TypeError: If inputs are invalid.
            CircularDependencyError: If adding the node would create a cycle.
        """
        # Validate inputs
        if not isinstance(input_names, list):
            raise TypeError("input_names must be a list of node names.")

        # Resolve input node names to Node objects
        resolved_inputs = self._resolve_input_nodes(input_names)

        # Create the node via factory
        try:
            node = self._node_factory.create_calculation_node(
                name=name,
                inputs=resolved_inputs,
                calculation_type=operation_type,
                formula_variable_names=formula_variable_names,
                **calculation_kwargs,
            )
        except (ValueError, TypeError):
            logger.exception(
                f"Failed to create calculation node '{name}' with type '{operation_type}'"
            )
            raise

        # Add with validation (includes cycle detection)
        added_node = self._add_node_with_validation(node)

        logger.info(
            f"Added calculation node '{name}' of type '{operation_type}' with inputs {input_names}"
        )
        return added_node

    def add_metric(
        self,
        metric_name: str,
        node_name: Optional[str] = None,
        *,
        input_node_map: Optional[dict[str, str]] = None,
    ) -> Node:
        """Add a metric calculation node based on a metric definition.

        If `node_name` is None, uses `metric_name` as the node name.

        Uses the metric registry to load inputs and formula, creates a
        calculation node using the formula strategy, registers it, and stores metric
        metadata on the node itself.

        Args:
            metric_name: Key of the metric definition to add.
            node_name: Optional name for the metric node; defaults to metric_name.
            input_node_map: Optional dictionary mapping metric input variable names
                (from metric definition) to the actual node names present in the graph.
                If None, assumes graph node names match metric input variable names.

        Returns:
            The created calculation node.

        Raises:
            TypeError: If node_name is invalid.
            ValueError: If node_name already exists.
            ConfigurationError: If metric definition is missing or invalid.
            NodeError: If required input nodes (after mapping) are missing.
        """
        # Default node_name to metric_name if not provided
        if node_name is None:
            node_name = metric_name
        if not node_name or not isinstance(node_name, str):
            raise TypeError("Metric node name must be a non-empty string.")
        # Check for name conflict
        if node_name in self._nodes:
            raise ValueError(
                f"A node with name '{node_name}' already exists in the graph."
            )

        # Load metric definition (Pydantic model)
        try:
            metric_def = metric_registry.get(metric_name)
        except KeyError as e:
            raise ConfigurationError(
                f"Unknown metric definition: '{metric_name}'"
            ) from e

        # Extract required fields from definition
        required_inputs = metric_def.inputs
        formula = metric_def.formula
        description = metric_def.description

        # Build list of input node names and formula variable names
        input_node_names: list[str] = []
        formula_variable_names: list[str] = []
        missing = []

        for req_input_name in required_inputs:
            # Determine the actual graph node name to look for
            target_node_name = req_input_name  # Default case
            if input_node_map and req_input_name in input_node_map:
                target_node_name = input_node_map[req_input_name]
            elif input_node_map:
                # If map provided but doesn't contain the required input, it's an error in the map
                missing.append(f"{req_input_name} (mapping missing in input_node_map)")
                continue  # Skip trying to find the node

            # Check if the node exists in the graph
            if target_node_name not in self._nodes:
                missing.append(target_node_name)  # Report the name we looked for
            else:
                input_node_names.append(target_node_name)
                formula_variable_names.append(
                    req_input_name
                )  # Use the metric's variable name

        if missing:
            raise NodeError(
                f"Cannot create metric '{metric_name}': missing required nodes {missing}",
                node_id=node_name,
            )

        # Create calculation node using add_calculation
        try:
            new_node = self.add_calculation(
                name=node_name,
                input_names=input_node_names,
                operation_type="formula",
                formula_variable_names=formula_variable_names,
                formula=formula,
                metric_name=metric_name,  # Pass metric metadata
                metric_description=description,  # Pass metric description
            )
        except Exception as e:
            logger.exception(
                f"Failed to create calculation node for metric '{metric_name}' as node '{node_name}'"
            )
            # Re-raise as ConfigurationError or keep original, depending on desired error reporting
            raise ConfigurationError(
                f"Error creating node for metric '{metric_name}': {e}"
            ) from e

        logger.info(
            f"Added metric '{metric_name}' as calculation node '{node_name}' with inputs {input_node_names}"
        )
        return new_node

    def add_custom_calculation(
        self,
        name: str,
        calculation_func: Callable[..., float],
        inputs: Optional[list[str]] = None,
        description: str = "",
    ) -> Node:
        """Add a custom calculation node using a Python callable.

        Args:
            name: Unique name for the custom calculation node.
            calculation_func: A callable that accepts (period, **inputs) and returns float.
            inputs: Optional list of node names to use as inputs.
            description: Optional description of the calculation.

        Returns:
            The created custom calculation node.

        Raises:
            NodeError: If any specified input nodes are missing.
            TypeError: If calculation_func is not callable.
            CircularDependencyError: If adding the node would create a cycle.
        """
        # Validate callable
        if not callable(calculation_func):
            raise TypeError("calculation_func must be callable.")

        # Resolve inputs if provided
        resolved_inputs: list[Node] = []
        if inputs is not None:
            if not isinstance(inputs, list):
                raise TypeError("inputs must be a list of node names.")
            resolved_inputs = self._resolve_input_nodes(inputs)

        # Create custom node via factory
        try:
            custom_node = self._node_factory._create_custom_node_from_callable(
                name=name,
                inputs=resolved_inputs,
                formula=calculation_func,
                description=description,
            )
        except (ValueError, TypeError):
            logger.exception(f"Failed to create custom calculation node '{name}'")
            raise

        # Add with validation (includes cycle detection)
        added_node = self._add_node_with_validation(custom_node)

        logger.info(f"Added custom calculation node '{name}' with inputs {inputs}")
        return added_node

    def ensure_signed_nodes(
        self, base_node_ids: list[str], *, suffix: str = "_signed"
    ) -> list[str]:
        """Ensure signed calculation nodes (-1 * input) exist for each base node.

        Args:
            base_node_ids: List of existing node names to sign.
            suffix: Suffix to append for signed node names.

        Returns:
            List of names of newly created signed nodes.
        """
        created: list[str] = []
        for base_id in base_node_ids:
            signed_id = f"{base_id}{suffix}"
            # Skip if already present
            if signed_id in self._nodes:
                continue
            # Ensure base node exists
            if base_id not in self._nodes:
                from fin_statement_model.core.errors import NodeError

                raise NodeError(
                    f"Cannot create signed node for missing base node '{base_id}'",
                    node_id=base_id,
                )
            # Create formula node that multiplies by -1
            self.add_calculation(
                name=signed_id,
                input_names=[base_id],
                operation_type="formula",
                formula="-input_0",
                formula_variable_names=["input_0"],
            )
            created.append(signed_id)
        return created

    def change_calculation_method(
        self,
        node_name: str,
        new_method_key: str,
        **kwargs: dict[str, Any],
    ) -> None:
        """Change the calculation method for an existing calculation-based node.

        Args:
            node_name: Name of the existing calculation node.
            new_method_key: Key of the new calculation method to apply.
            **kwargs: Additional parameters required by the new calculation.

        Returns:
            None

        Raises:
            NodeError: If the target node does not exist or is not a CalculationNode.
            ValueError: If `new_method_key` is not a recognized calculation key.
            TypeError: If the new calculation cannot be instantiated with the provided arguments.

        Examples:
            >>> graph.change_calculation_method("GrossProfit", "addition")
        """
        node = self.manipulator.get_node(node_name)
        if node is None:
            raise NodeError("Node not found for calculation change", node_id=node_name)
        if not isinstance(node, CalculationNode):
            raise NodeError(
                f"Node '{node_name}' is not a CalculationNode", node_id=node_name
            )
        # Map method key to registry name
        if new_method_key not in self._node_factory._calculation_methods:
            raise ValueError(f"Calculation '{new_method_key}' is not recognized.")
        calculation_class_name = self._node_factory._calculation_methods[new_method_key]
        try:
            calculation_cls = Registry.get(calculation_class_name)
        except KeyError as e:
            raise ValueError(
                f"Calculation class '{calculation_class_name}' not found in registry."
            ) from e
        try:
            calculation_instance = calculation_cls(**kwargs)
        except TypeError as e:
            raise TypeError(
                f"Failed to instantiate calculation '{new_method_key}': {e}"
            )
        # Apply new calculation
        node.set_calculation(calculation_instance)
        # Clear cached calculations for this node
        if node_name in self._cache:
            del self._cache[node_name]
        logger.info(f"Changed calculation for node '{node_name}' to '{new_method_key}'")

    def get_metric(self, metric_id: str) -> Optional[Node]:
        """Return the metric node for a given metric ID, if present.

        Searches for a node with the given ID that was created as a metric
        (identified by having a `metric_name` attribute).

        Args:
            metric_id: Identifier of the metric node to retrieve.

        Returns:
            The Node corresponding to `metric_id` if it's a metric node, or None.

        Examples:
            >>> m = graph.get_metric("current_ratio")
            >>> if m:
            ...     logger.info(m.name)
        """
        node = self._nodes.get(metric_id)
        # Check if the node exists and has the metric_name attribute populated
        if node and getattr(node, "metric_name", None) == metric_id:
            return node
        return None

    def get_available_metrics(self) -> list[str]:
        """Return a sorted list of all metric node IDs currently in the graph.

        Identifies metric nodes by checking for the presence and non-None value
        of the `metric_name` attribute.

        Returns:
            A sorted list of metric node names.

        Examples:
            >>> graph.get_available_metrics()
            ['current_ratio', 'debt_equity_ratio']
        """
        # Iterate through all nodes and collect names of those that are metrics
        metric_node_names = [
            node.name
            for node in self._nodes.values()
            if getattr(node, "metric_name", None) is not None
        ]
        return sorted(metric_node_names)

    def get_metric_info(self, metric_id: str) -> dict[str, Any]:
        """Return detailed information for a specific metric node.

        Args:
            metric_id: Identifier of the metric node to inspect.

        Returns:
            A dict containing 'id', 'name', 'description', and 'inputs' for the metric.

        Raises:
            ValueError: If `metric_id` does not correspond to a metric node.

        Examples:
            >>> info = graph.get_metric_info("current_ratio")
            >>> logger.info(info['inputs'])
        """
        metric_node = self.get_metric(metric_id)
        if metric_node is None:
            if metric_id in self._nodes:
                raise ValueError(
                    f"Node '{metric_id}' exists but is not a metric (missing metric_name attribute)."
                )
            raise ValueError(f"Metric node '{metric_id}' not found in graph.")

        # Extract info directly from the FormulaCalculationNode
        try:
            # Use getattr for safety, retrieving stored metric metadata
            description = getattr(metric_node, "metric_description", "N/A")
            # metric_name stored on the node is the key from the registry
            registry_key = getattr(metric_node, "metric_name", metric_id)

            # We might want the display name from the original definition.
            # Fetch the definition again if needed for the display name.
            try:
                metric_def = metric_registry.get(registry_key)
                display_name = metric_def.name
            except Exception:
                logger.warning(
                    f"Could not reload metric definition for '{registry_key}' to get display name. Using node name '{metric_id}' instead."
                )
                display_name = metric_id  # Fallback to node name

            inputs = metric_node.get_dependencies()
        except Exception as e:
            # Catch potential attribute errors or other issues
            logger.error(
                f"Error retrieving info for metric node '{metric_id}': {e}",
                exc_info=True,
            )
            raise ValueError(
                f"Failed to retrieve metric info for '{metric_id}': {e}"
            ) from e

        return {
            "id": metric_id,
            "name": display_name,
            "description": description,
            "inputs": inputs,
        }

    @overload
    def get_adjusted_value(
        self,
        node_name: str,
        period: str,
        filter_input: "AdjustmentFilterInput" = None,
        *,
        return_flag: Literal[True],
    ) -> tuple[float, bool]: ...

    @overload
    def get_adjusted_value(
        self,
        node_name: str,
        period: str,
        filter_input: "AdjustmentFilterInput" = None,
        *,
        return_flag: Literal[False] = False,
    ) -> float: ...

    def get_adjusted_value(
        self,
        node_name: str,
        period: str,
        filter_input: "AdjustmentFilterInput" = None,
        *,
        return_flag: bool = False,
    ) -> float | tuple[float, bool]:
        """Calculates the value of a node for a period, applying selected adjustments.

        Fetches the base calculated value, retrieves adjustments matching the filter,
        applies them in order, and returns the result.

        Args:
            node_name: The name of the node to calculate.
            period: The time period identifier.
            filter_input: Criteria for selecting which adjustments to apply.
                          Can be an AdjustmentFilter instance, a set of tags (for include_tags),
                          a callable predicate `fn(adj: Adjustment) -> bool`, or None
                          (applies all adjustments in the default scenario).
            return_flag: If True, return a tuple (adjusted_value, was_adjusted_flag).
                         If False (default), return only the adjusted_value.

        Returns:
            The adjusted float value, or a tuple (value, flag) if return_flag is True.

        Raises:
            NodeError: If the specified node does not exist.
            CalculationError: If an error occurs during the base calculation or adjustment application.
            TypeError: If filter_input is an invalid type.
        """
        # 1. Get the base value (result of underlying node calculation)
        try:
            base_value = self.calculate(node_name, period)
        except (NodeError, CalculationError, TypeError):
            # Propagate errors from base calculation
            logger.exception(
                f"Error getting base value for '{node_name}' in period '{period}'"
            )
            raise

        # 2. Get filtered adjustments from the manager
        try:
            adjustments_to_apply = self.adjustment_manager.get_filtered_adjustments(
                node_name=node_name, period=period, filter_input=filter_input
            )
        except TypeError:
            logger.exception("Invalid filter type provided for get_adjusted_value")
            raise

        # 3. Apply the adjustments
        adjusted_value, was_adjusted = self.adjustment_manager.apply_adjustments(
            base_value, adjustments_to_apply
        )

        # 4. Return result based on flag
        if return_flag:
            return adjusted_value, was_adjusted
        else:
            return adjusted_value

    def calculate(self, node_name: str, period: str) -> float:
        """Calculate and return the value of a specific node for a given period.

        This method uses internal caching to speed repeated calls, and wraps
        underlying errors in CalculationError for clarity.

        Args:
            node_name: Name of the node to calculate.
            period: Time period identifier for the calculation.

        Returns:
            The calculated float value for the node and period.

        Raises:
            NodeError: If the specified node does not exist.
            TypeError: If the node has no callable `calculate` method.
            CalculationError: If an error occurs during the node's calculation.

        Examples:
            >>> value = graph.calculate("Revenue", "2023")
        """
        # Return cached value if present
        if node_name in self._cache and period in self._cache[node_name]:
            logger.debug(f"Cache hit for node '{node_name}', period '{period}'")
            return self._cache[node_name][period]
        # Resolve node
        node = self.manipulator.get_node(node_name)
        if node is None:
            raise NodeError(f"Node '{node_name}' not found", node_id=node_name)
        # Validate calculate method
        if not hasattr(node, "calculate") or not callable(node.calculate):
            raise TypeError(f"Node '{node_name}' has no callable calculate method.")
        # Perform calculation with error handling
        try:
            value = node.calculate(period)
        except (
            NodeError,
            ConfigurationError,
            CalculationError,
            ValueError,
            KeyError,
            ZeroDivisionError,
        ) as e:
            logger.error(
                f"Error calculating node '{node_name}' for period '{period}': {e}",
                exc_info=True,
            )
            raise CalculationError(
                message=f"Failed to calculate node '{node_name}'",
                node_id=node_name,
                period=period,
                details={"original_error": str(e)},
            ) from e
        # Cache and return
        self._cache.setdefault(node_name, {})[period] = value
        logger.debug(f"Cached value for node '{node_name}', period '{period}': {value}")
        return value

    def recalculate_all(self, periods: Optional[list[str]] = None) -> None:
        """Recalculate all nodes for given periods, clearing all caches first.

        Args:
            periods: List of period strings, a single string, or None to use all periods.

        Returns:
            None

        Raises:
            TypeError: If `periods` is not a list, string, or None.

        Examples:
            >>> graph.recalculate_all(["2023", "2024"])
        """
        # Normalize periods input
        if periods is None:
            periods_to_use = self.periods
        elif isinstance(periods, str):
            periods_to_use = [periods]
        elif isinstance(periods, list):
            periods_to_use = periods
        else:
            raise TypeError(
                "Periods must be a list of strings, a single string, or None."
            )
        # Clear all caches (node-level and central) to force full recalculation
        self.clear_all_caches()
        if not periods_to_use:
            return
        # Recalculate each node for each period
        for node_name in list(self._nodes.keys()):
            for period in periods_to_use:
                try:
                    self.calculate(node_name, period)
                except Exception as e:
                    logger.warning(
                        f"Error recalculating node '{node_name}' for period '{period}': {e}"
                    )

    def clear_all_caches(self) -> None:
        """Clear all node-level and central calculation caches.

        Returns:
            None

        Examples:
            >>> graph.clear_all_caches()
        """
        logger.debug(f"Clearing node-level caches for {len(self.nodes)} nodes.")
        for node in self.nodes.values():
            if hasattr(node, "clear_cache"):
                try:
                    node.clear_cache()
                except Exception as e:
                    logger.warning(f"Failed to clear cache for node '{node.name}': {e}")
        # Clear central calculation cache
        self.clear_calculation_cache()
        logger.debug("Cleared central calculation cache.")

    def clear_calculation_cache(self) -> None:
        """Clear the graph's internal calculation cache.

        Returns:
            None

        Examples:
            >>> graph.clear_calculation_cache()
        """
        self._cache.clear()
        logger.debug("Cleared graph calculation cache.")

    def clear(self) -> None:
        """Reset the graph by clearing nodes, periods, adjustments, and caches."""
        self._nodes = {}
        self._periods = []
        self._cache = {}

        # --- Adjustment Manager Integration ---
        self.adjustment_manager.clear_all()
        # --- End Adjustment Manager Integration ---

        logger.info("Graph cleared: nodes, periods, adjustments, and caches reset.")

    def add_financial_statement_item(
        self, name: str, values: dict[str, float]
    ) -> FinancialStatementItemNode:
        """Add a basic financial statement item (data node) to the graph.

        Args:
            name: Unique name for the financial statement item node.
            values: Mapping of period strings to float values for this item.

        Returns:
            The newly created `FinancialStatementItemNode`.

        Raises:
            ValueError: If node name is invalid.
            TypeError: If `values` is not a dict or contains invalid types.

        Examples:
            >>> item_node = graph.add_financial_statement_item("SG&A", {"2023": 50.0})
            >>> item_node.calculate("2023")
            50.0
        """
        # Validate inputs
        if not isinstance(values, dict):
            raise TypeError("Values must be provided as a dict[str, float]")

        # Create a new financial statement item node
        new_node = self._node_factory.create_financial_statement_item(
            name=name, values=values.copy()
        )

        # Add with validation (no cycle detection needed for data nodes)
        # Cast to FinancialStatementItemNode for correct return type
        from typing import cast

        added_node = cast(
            FinancialStatementItemNode,
            self._add_node_with_validation(
                new_node,
                check_cycles=False,  # Data nodes don't have inputs, so no cycles possible
                validate_inputs=False,  # Data nodes don't have inputs to validate
            ),
        )

        logger.info(
            f"Added FinancialStatementItemNode '{name}' with periods {list(values.keys())}"
        )
        return added_node

    def update_financial_statement_item(
        self, name: str, values: dict[str, float], replace_existing: bool = False
    ) -> FinancialStatementItemNode:
        """Update values for an existing financial statement item node.

        Args:
            name: Name of the existing financial statement item node.
            values: Mapping of new period strings to float values.
            replace_existing: If True, replace existing values entirely; otherwise merge.

        Returns:
            The updated `FinancialStatementItemNode`.

        Raises:
            NodeError: If the node does not exist.
            TypeError: If the node is not a `FinancialStatementItemNode` or `values` is not a dict.

        Examples:
            >>> graph.update_financial_statement_item("SG&A", {"2024": 60.0})
        """
        node = self.manipulator.get_node(name)
        if node is None:
            raise NodeError("Node not found", node_id=name)
        if not isinstance(node, FinancialStatementItemNode):
            raise TypeError(f"Node '{name}' is not a FinancialStatementItemNode")
        if not isinstance(values, dict):
            raise TypeError("Values must be provided as a dict[str, float]")
        if replace_existing:
            node.values = values.copy()
        else:
            node.values.update(values)
        self.add_periods(list(values.keys()))
        logger.info(
            f"Updated FinancialStatementItemNode '{name}' with periods {list(values.keys())}; replace_existing={replace_existing}"
        )
        return node

    def get_financial_statement_items(self) -> list[Node]:
        """Retrieve all financial statement item nodes from the graph.

        Returns:
            A list of `FinancialStatementItemNode` objects currently in the graph.

        Examples:
            >>> items = graph.get_financial_statement_items()
        """
        from fin_statement_model.core.nodes import (
            FinancialStatementItemNode,
        )  # Keep import local as it's specific

        return [
            node
            for node in self.nodes.values()
            if isinstance(node, FinancialStatementItemNode)
        ]

    def __repr__(self) -> str:
        """Provide a concise, developer-friendly string representation of the graph.

        Summarize total nodes, FS items, calculations, dependencies, and periods.

        Returns:
            A string summarizing the graph's structure and contents.

        Examples:
            >>> logger.info(repr(graph))
        """
        from fin_statement_model.core.nodes import (
            FinancialStatementItemNode,
        )  # Keep import local

        num_nodes = len(self.nodes)
        periods_str = ", ".join(map(repr, self.periods)) if self.periods else "None"

        fs_item_count = 0
        calc_node_count = 0
        other_node_count = 0
        dependencies_count = 0

        for node in self.nodes.values():
            if isinstance(node, FinancialStatementItemNode):
                fs_item_count += 1
            elif is_calculation_node(node):
                calc_node_count += 1
                # Prioritize get_dependencies if available, otherwise check inputs
                if hasattr(node, "get_dependencies"):
                    try:
                        dependencies_count += len(node.get_dependencies())
                    except Exception as e:
                        logger.warning(
                            f"Error calling get_dependencies for node '{node.name}': {e}"
                        )
                elif hasattr(node, "inputs"):
                    try:
                        if isinstance(node.inputs, list):
                            # Ensure inputs are nodes with names
                            dep_names = [
                                inp.name for inp in node.inputs if hasattr(inp, "name")
                            ]
                            dependencies_count += len(dep_names)
                        elif isinstance(node.inputs, dict):
                            # Assume keys are dependency names for dict inputs
                            dependencies_count += len(node.inputs)
                    except Exception as e:
                        logger.warning(
                            f"Error processing inputs for node '{node.name}': {e}"
                        )
            else:
                other_node_count += 1

        repr_parts = [
            f"Total Nodes: {num_nodes}",
            f"FS Items: {fs_item_count}",
            f"Calculations: {calc_node_count}",
        ]
        if other_node_count > 0:
            repr_parts.append(f"Other: {other_node_count}")
        repr_parts.append(f"Dependencies: {dependencies_count}")
        repr_parts.append(f"Periods: [{periods_str}]")

        return f"<{type(self).__name__}({', '.join(repr_parts)})>"

    def has_cycle(self, source_node: Node, target_node: Node) -> bool:
        """Check if a cycle exists from a source node to a target node.

        This method delegates to GraphTraverser to determine if `target_node` is
        reachable from `source_node` via successors, indicating that adding an edge
        from `target_node` to `source_node` would create a cycle.

        Args:
            source_node: The starting node for cycle detection.
            target_node: The node to detect return path to.

        Returns:
            True if a cycle exists, False otherwise.
        """
        if source_node.name not in self._nodes or target_node.name not in self._nodes:
            return False

        # Use GraphTraverser's reachability check
        return self.traverser._is_reachable(source_node.name, target_node.name)

    def get_node(self, name: str) -> Optional[Node]:
        """Retrieve a node from the graph by its name.

        Args:
            name: The unique name of the node to retrieve.

        Returns:
            The `Node` instance if found, else None.

        Examples:
            >>> node = graph.get_node("Revenue")
        """
        return self.manipulator.get_node(name)

    def _add_node_with_validation(
        self, node: Node, check_cycles: bool = True, validate_inputs: bool = True
    ) -> Node:
        """Internal method for adding nodes with common validation logic.

        Args:
            node: The Node instance to add
            check_cycles: Whether to perform cycle detection
            validate_inputs: Whether to validate input node references

        Returns:
            The added node

        Raises:
            ValueError: If node name is invalid
            NodeError: If input validation fails
            CircularDependencyError: If adding the node would create a cycle
        """
        # 1. Name validation
        if not node.name or not isinstance(node.name, str):
            raise ValueError("Node name must be a non-empty string")

        # 2. Check for existing node
        if node.name in self._nodes:
            logger.warning(f"Overwriting existing node '{node.name}'")

        # 3. Input validation (if applicable)
        if validate_inputs and hasattr(node, "inputs") and node.inputs:
            self._validate_node_inputs(node)

        # 4. Cycle detection (if applicable)
        if (
            check_cycles
            and hasattr(node, "inputs")
            and node.inputs
            and self.traverser.would_create_cycle(node)
        ):
            # Try to find the actual cycle path for better error message
            cycle_path = None
            for input_node in node.inputs:
                if hasattr(input_node, "name"):
                    path = self.traverser.find_cycle_path(input_node.name, node.name)
                    if path:
                        cycle_path = path
                        break

            raise CircularDependencyError(
                f"Adding node '{node.name}' would create a cycle",
                cycle=cycle_path or [node.name, "...", node.name],
            )

        # 5. Register node
        self._nodes[node.name] = node

        # 6. Update periods if applicable
        if hasattr(node, "values") and isinstance(node.values, dict):
            self.add_periods(list(node.values.keys()))

        logger.debug(f"Added node '{node.name}' to graph")
        return node

    def _validate_node_inputs(self, node: Node) -> None:
        """Validate that all input nodes exist in the graph.

        Args:
            node: The node whose inputs to validate

        Raises:
            NodeError: If any input node is missing
        """
        missing_inputs = []

        if hasattr(node, "inputs") and node.inputs:
            for input_node in node.inputs:
                if hasattr(input_node, "name"):
                    if input_node.name not in self._nodes:
                        missing_inputs.append(input_node.name)
                # Handle case where inputs might be strings instead of Node objects
                elif isinstance(input_node, str) and input_node not in self._nodes:
                    missing_inputs.append(input_node)

        if missing_inputs:
            raise NodeError(
                f"Cannot add node '{node.name}': missing required input nodes {missing_inputs}",
                node_id=node.name,
            )

    def _resolve_input_nodes(self, input_names: list[str]) -> list[Node]:
        """Resolve input node names to Node objects.

        Args:
            input_names: List of node names to resolve

        Returns:
            List of resolved Node objects

        Raises:
            NodeError: If any input node name does not exist
        """
        resolved_inputs: list[Node] = []
        missing = []

        for name in input_names:
            node = self._nodes.get(name)
            if node is None:
                missing.append(name)
            else:
                resolved_inputs.append(node)

        if missing:
            raise NodeError(f"Cannot resolve input nodes: missing nodes {missing}")

        return resolved_inputs

    def add_node(self, node: Node) -> None:
        """Add a node to the graph.

        Args:
            node: A ``Node`` instance to add to the graph.

        Raises:
            TypeError: If the provided object is not a Node instance.

        Examples:
            >>> from fin_statement_model.core.nodes import FinancialStatementItemNode
            >>> node = FinancialStatementItemNode("Revenue", {"2023": 1000})
            >>> graph.add_node(node)
        """
        from fin_statement_model.core.nodes.base import Node as _NodeBase

        if not isinstance(node, _NodeBase):
            raise TypeError(f"Expected Node instance, got {type(node).__name__}")

        return self.manipulator.add_node(node)

    def remove_node(self, node_name: str) -> None:
        """Remove a node from the graph by name, updating dependencies.

        Args:
            node_name: The name of the node to remove.

        Returns:
            None

        Examples:
            >>> graph.remove_node("OldItem")
        """
        return self.manipulator.remove_node(node_name)

    def replace_node(self, node_name: str, new_node: Node) -> None:
        """Replace an existing node with a new node instance.

        Args:
            node_name: Name of the node to replace.
            new_node: The new `Node` instance to substitute.

        Returns:
            None

        Examples:
            >>> graph.replace_node("Item", updated_node)
        """
        return self.manipulator.replace_node(node_name, new_node)

    def has_node(self, node_id: str) -> bool:
        """Check if a node with the given ID exists in the graph.

        Args:
            node_id: The name of the node to check.

        Returns:
            True if the node exists, False otherwise.

        Examples:
            >>> graph.has_node("Revenue")
        """
        return self.manipulator.has_node(node_id)

    def set_value(self, node_id: str, period: str, value: float) -> None:
        """Set or update the value for a node in a specific period.

        Args:
            node_id: The name of the node.
            period: The period identifier to set the value for.
            value: The float value to assign.

        Returns:
            None

        Raises:
            ValueError: If the period is not recognized by the graph.
            NodeError: If the node does not exist.
            TypeError: If the node does not support setting a value.

        Examples:
            >>> graph.set_value("SG&A", "2024", 55.0)
        """
        return self.manipulator.set_value(node_id, period, value)

    def topological_sort(self) -> list[str]:
        """Perform a topological sort of all graph nodes.

        Returns:
            A list of node IDs in topological order.

        Raises:
            ValueError: If a cycle is detected in the graph.

        Examples:
            >>> order = graph.topological_sort()
        """
        return self.traverser.topological_sort()

    def get_calculation_nodes(self) -> list[str]:
        """Get all calculation node IDs in the graph.

        Returns:
            A list of node names that have associated calculations.

        Examples:
            >>> graph.get_calculation_nodes()
        """
        return self.traverser.get_calculation_nodes()

    def get_dependencies(self, node_id: str) -> list[str]:
        """Get the direct predecessor node IDs (dependencies) for a given node.

        Args:
            node_id: The name of the node to inspect.

        Returns:
            A list of node IDs that the given node depends on.

        Examples:
            >>> graph.get_dependencies("GrossProfit")
        """
        return self.traverser.get_dependencies(node_id)

    def get_dependency_graph(self) -> dict[str, list[str]]:
        """Get the full dependency graph mapping of node IDs to their inputs.

        Returns:
            A dict mapping each node ID to a list of its dependency node IDs.

        Examples:
            >>> graph.get_dependency_graph()
        """
        return self.traverser.get_dependency_graph()

    def detect_cycles(self) -> list[list[str]]:
        """Detect all cycles in the graph's dependency structure.

        Returns:
            A list of cycles, each represented as a list of node IDs.

        Examples:
            >>> graph.detect_cycles()
        """
        return self.traverser.detect_cycles()

    def validate(self) -> list[str]:
        """Validate the graph structure for errors such as cycles or missing nodes.

        Returns:
            A list of validation error messages, empty if valid.

        Examples:
            >>> graph.validate()
        """
        return self.traverser.validate()

    def breadth_first_search(
        self, start_node: str, direction: str = "successors"
    ) -> list[list[str]]:
        """Perform a breadth-first search (BFS) traversal of the graph.

        Args:
            start_node: The starting node ID for BFS.
            direction: Either 'successors' or 'predecessors' to traverse.

        Returns:
            A nested list of node IDs per BFS level.

        Raises:
            ValueError: If `direction` is not 'successors' or 'predecessors'.

        Examples:
            >>> graph.breadth_first_search("Revenue", "successors")
        """
        return self.traverser.breadth_first_search(start_node, direction)

    def get_direct_successors(self, node_id: str) -> list[str]:
        """Get immediate successor node IDs for a given node.

        Args:
            node_id: The name of the node to inspect.

        Returns:
            A list of node IDs that directly follow the given node.

        Examples:
            >>> graph.get_direct_successors("Revenue")
        """
        return self.traverser.get_direct_successors(node_id)

    def get_direct_predecessors(self, node_id: str) -> list[str]:
        """Get immediate predecessor node IDs (inputs) for a given node.

        Args:
            node_id: The name of the node to inspect.

        Returns:
            A list of node IDs that the given node directly depends on.

        Examples:
            >>> graph.get_direct_predecessors("GrossProfit")
        """
        return self.traverser.get_direct_predecessors(node_id)

    def merge_from(self, other_graph: "Graph") -> None:
        """Merge nodes and periods from another Graph into this one.

        Adds periods from the other graph if they don't exist in this graph.
        Adds nodes from the other graph if they don't exist.
        If a node exists in both graphs, attempts to merge the 'values' dictionary
        from the other graph's node into this graph's node.

        Args:
            other_graph: The Graph instance to merge data from.

        Raises:
            TypeError: If other_graph is not a Graph instance.
        """
        if not isinstance(other_graph, Graph):
            raise TypeError("Can only merge from another Graph instance.")

        logger.info(f"Starting merge from graph {other_graph!r} into {self!r}")

        # 1. Update periods
        new_periods = [p for p in other_graph.periods if p not in self.periods]
        if new_periods:
            self.add_periods(new_periods)
            logger.debug(f"Merged periods: {new_periods}")

        # 2. Merge nodes
        nodes_added = 0
        nodes_updated = 0
        for node_name, other_node in other_graph.nodes.items():
            existing_node = self.get_node(node_name)
            if existing_node is not None:
                # Node exists, merge values if applicable
                if (
                    hasattr(existing_node, "values")
                    and hasattr(other_node, "values")
                    and isinstance(getattr(existing_node, "values", None), dict)
                    and isinstance(getattr(other_node, "values", None), dict)
                ):
                    try:
                        # Perform the update
                        existing_node.values.update(other_node.values)
                        nodes_updated += 1
                        logger.debug(f"Merged values into existing node '{node_name}'")
                        # No need to call self.add_node(existing_node) as it's already there
                    except AttributeError:
                        # Should not happen due to hasattr checks, but defensive
                        logger.warning(
                            f"Could not merge values for node '{node_name}' due to missing 'values' attribute despite hasattr check."
                        )
                    except Exception as e:
                        logger.warning(
                            f"Could not merge values for node '{node_name}': {e}"
                        )
                else:
                    # Nodes exist but cannot merge values (e.g., calculation nodes without stored values)
                    logger.debug(
                        f"Node '{node_name}' exists in both graphs, but values not merged (missing/incompatible 'values' attribute). Keeping target graph's node."
                    )
            else:
                # Node doesn't exist in target graph, add it
                try:
                    # Ensure we add a copy if nodes might be shared or mutable in complex ways,
                    # but for now, assume adding the instance is okay.
                    self.add_node(other_node)
                    nodes_added += 1
                except Exception:
                    logger.exception(
                        f"Failed to add new node '{node_name}' during merge:"
                    )

        logger.info(
            f"Merge complete. Nodes added: {nodes_added}, Nodes updated (values merged): {nodes_updated}"
        )

    # --- Adjustment Management API ---

    def add_adjustment(
        self,
        node_name: str,
        period: str,
        value: float,
        reason: str,
        adj_type: AdjustmentType = AdjustmentType.ADDITIVE,
        scale: float = 1.0,
        priority: int = 0,
        tags: Optional[set[AdjustmentTag]] = None,
        scenario: Optional[str] = None,
        user: Optional[str] = None,
        start_period: Optional[str] = None,  # Phase 2
        end_period: Optional[str] = None,  # Phase 2
        adj_id: Optional[UUID] = None,  # Allow specifying ID, e.g., for re-creation
    ) -> UUID:
        """Adds a discretionary adjustment to a specific node and period.

        Creates an Adjustment object and delegates storage to the AdjustmentManager.

        Args:
            node_name: The name of the target node.
            period: The primary period the adjustment applies to.
            value: The numeric value of the adjustment.
            reason: Text description of why the adjustment was made.
            adj_type: How the adjustment combines with the base value.
            scale: Attenuation factor for the adjustment (0.0 to 1.0, Phase 2).
            priority: Tie-breaker for applying multiple adjustments (lower number applied first).
            tags: Set of descriptive tags for filtering and analysis.
            scenario: The named scenario this adjustment belongs to. Defaults to DEFAULT_SCENARIO if None.
            user: Identifier for the user who created the adjustment.
            start_period: The first period the adjustment is effective (inclusive, Phase 2).
            end_period: The last period the adjustment is effective (inclusive, Phase 2).
            adj_id: Optional specific UUID to use for the adjustment.

        Returns:
            The UUID of the created or updated adjustment.

        Raises:
            NodeError: If the target node_name does not exist in the graph.
            ValidationError: If adjustment parameters are invalid (e.g., scale out of bounds).
        """
        if not self.has_node(node_name):
            raise NodeError(
                f"Cannot add adjustment: Node '{node_name}' not found.",
                node_id=node_name,
            )

        # Need Pydantic's ValidationError and uuid4
        from pydantic import ValidationError
        from uuid import uuid4

        # Need Adjustment model details
        from fin_statement_model.core.adjustments.models import Adjustment

        # Assign default scenario if None was passed
        actual_scenario = scenario if scenario is not None else DEFAULT_SCENARIO

        # Create the adjustment object - Pydantic handles validation (e.g., scale)
        try:
            adj = Adjustment(
                id=adj_id or uuid4(),  # Generate new ID if not provided
                node_name=node_name,
                period=period,
                start_period=start_period,
                end_period=end_period,
                value=value,
                type=adj_type,
                scale=scale,
                priority=priority,
                tags=tags or set(),
                scenario=actual_scenario,  # Use the actual scenario
                reason=reason,
                user=user,
                # timestamp is added automatically by the model
            )
        except ValidationError:
            logger.exception(f"Failed to create adjustment for node '{node_name}'")
            raise  # Re-raise Pydantic's validation error

        self.adjustment_manager.add_adjustment(adj)
        logger.info(
            f"Added adjustment {adj.id} for node '{node_name}', period '{period}', scenario '{scenario}'."
        )
        return adj.id

    def remove_adjustment(self, adj_id: UUID) -> bool:
        """Removes an adjustment by its unique ID.

        Args:
            adj_id: The UUID of the adjustment to remove.

        Returns:
            True if an adjustment was found and removed, False otherwise.
        """
        removed = self.adjustment_manager.remove_adjustment(adj_id)
        if removed:
            logger.info(f"Removed adjustment {adj_id}.")
        else:
            logger.warning(f"Attempted to remove non-existent adjustment {adj_id}.")
        return removed

    def get_adjustments(
        self, node_name: str, period: str, *, scenario: Optional[str] = None
    ) -> list[Adjustment]:
        """Retrieves all adjustments for a specific node, period, and scenario.

        Args:
            node_name: The name of the target node.
            period: The target period.
            scenario: The scenario to retrieve adjustments for. Defaults to DEFAULT_SCENARIO if None.

        Returns:
            A list of Adjustment objects matching the criteria, sorted by application order.
        """
        if not self.has_node(node_name):
            # Or return empty list? Returning empty seems safer.
            logger.warning(f"Node '{node_name}' not found when getting adjustments.")
            return []
        # Assign default scenario if None was passed
        actual_scenario = scenario if scenario is not None else DEFAULT_SCENARIO
        return self.adjustment_manager.get_adjustments(
            node_name, period, scenario=actual_scenario
        )

    def list_all_adjustments(self) -> list[Adjustment]:
        """Returns a list of all adjustments currently managed by the graph.

        Returns:
            A list containing all Adjustment objects across all nodes, periods, and scenarios.
        """
        return self.adjustment_manager.get_all_adjustments()

    def was_adjusted(
        self, node_name: str, period: str, filter_input: "AdjustmentFilterInput" = None
    ) -> bool:
        """Checks if a node's value for a given period was affected by any selected adjustments.

        Args:
            node_name: The name of the node to check.
            period: The time period identifier.
            filter_input: Criteria for selecting which adjustments to consider (same as get_adjusted_value).

        Returns:
            True if any adjustment matching the filter was applied to the base value, False otherwise.

        Raises:
            NodeError: If the specified node does not exist.
            CalculationError: If an error occurs during the underlying calculation.
            TypeError: If filter_input is an invalid type.
        """
        try:
            _, was_adjusted_flag = self.get_adjusted_value(
                node_name, period, filter_input, return_flag=True
            )
            return was_adjusted_flag
        except (NodeError, CalculationError, TypeError):
            # Propagate errors consistently
            logger.exception(f"Error checking if node '{node_name}' was adjusted")
            raise

    # --- End Adjustment Management API ---
