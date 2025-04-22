"""Calculation engine for financial statement calculations.

This module provides the CalculationEngine class which is responsible for managing
calculation nodes and performing calculations on the financial data graph.
"""

from typing import Optional, Any, Callable
import logging

from .node_factory import NodeFactory
from .nodes import (
    Node,
    StrategyCalculationNode,
    MetricCalculationNode,
)

# Remove direct import of METRIC_DEFINITIONS
# from .metrics import METRIC_DEFINITIONS
# Import the registry instance instead
from .metrics import metric_registry
from .errors import (
    ConfigurationError,
    NodeError,
    CalculationError,
)

# Configure logging
logger = logging.getLogger(__name__)


class CalculationEngine:
    """Manages calculation nodes and performs calculations using a shared node registry.

    Handles adding calculation and metric nodes, performing calculations,
    managing calculation strategies, and caching results. This engine operates
    on a node registry that is shared with other components, like a Graph object,
    allowing for integrated graph management and calculation.

    Attributes:
        _node_factory: An instance of NodeFactory used to create nodes.
        _nodes: A dictionary representing the shared registry of nodes.
        _cache: A dictionary used for caching calculation results.
        _metric_names: A set storing the names of nodes added as metrics.
    """

    def __init__(self, nodes_registry: dict[str, Node]):
        """Initialize the CalculationEngine with a shared node registry.

        Args:
            nodes_registry: The dictionary instance shared across graph components
                            to store all nodes (e.g., from a Graph object).

        Example:
            >>> shared_nodes = {}
            >>> engine = CalculationEngine(shared_nodes)
            >>> # The engine now operates on the 'shared_nodes' dictionary.
        """
        self._node_factory = NodeFactory()  # Keep its own factory
        self._nodes = nodes_registry  # Use the shared registry
        self._cache: dict[str, dict[str, float]] = {}  # Keep internal cache for calc results
        # Metrics are just nodes, store their names if needed for specific logic,
        # but the node itself lives in the shared self._nodes registry.
        self._metric_names: set[str] = set()

    def add_calculation(
        self,
        name: str,
        input_names: list[str],
        operation_type: str,
        **kwargs: dict[str, Any],
    ) -> Node:
        """Add a strategy-based calculation node to the shared registry.

        Resolves input node names from the shared registry, creates the node
        using the internal NodeFactory, and adds it to the shared registry.

        Args:
            name: Name of the calculation node to create.
            input_names: List of names of input nodes required for the calculation.
                         These nodes must already exist in the shared registry.
            operation_type: Key identifying the calculation strategy (e.g., 'addition')
                            registered with the NodeFactory.
            **kwargs: Additional arguments passed to the calculation strategy
                      constructor via the NodeFactory.

        Returns:
            The created StrategyCalculationNode, now stored in the shared registry.

        Raises:
            NodeError: If any input node name is not found in the shared registry.
            ValueError: If the node name or operation_type is invalid, or if the
                        strategy creation fails within the factory.
            TypeError: If strategy constructor arguments are incorrect.

        Example:
            >>> shared_nodes = {'revenue': RevenueNode('revenue'), 'cogs': CogsNode('cogs')}
            >>> engine = CalculationEngine(shared_nodes)
            >>> try:
            ...     gross_profit_node = engine.add_calculation(
            ...         name='gross_profit',
            ...         input_names=['revenue', 'cogs'],
            ...         operation_type='subtraction'
            ...     )
            ...     print(f"Node '{gross_profit_node.name}' added.")
            ... except NodeError as e:
            ...     print(e)
            Node 'gross_profit' added.
        """
        # 1. Resolve input node names from the shared self._nodes registry
        resolved_inputs: list[Node] = []
        missing_nodes = []
        for node_name in input_names:
            node = self._nodes.get(node_name)
            if node is None:
                missing_nodes.append(node_name)
            else:
                resolved_inputs.append(node)

        if missing_nodes:
            raise NodeError(
                f"Cannot create calculation node '{name}': Missing required input nodes in shared registry: {missing_nodes}"
            )

        # 2. Create the calculation node using the factory with resolved nodes
        try:
            node = self._node_factory.create_calculation_node(
                name=name,
                inputs=resolved_inputs,
                calculation_type=operation_type,
                **kwargs,
            )
        except (NodeError, ValueError, TypeError):
            logger.exception(
                "Failed to create calculation node '%s' for type '%s' via factory.",
                name,
                operation_type,
            )
            raise

        # 3. Add the created node to the shared registry
        if name in self._nodes:
            logger.warning(f"Overwriting existing node in shared registry: '{name}'")
        self._nodes[name] = node  # Add to the shared dict

        logger.info(
            f"Added calculation node '{name}' (type: '{operation_type}') to shared registry."
        )
        return node

    def add_metric(self, metric_name: str, node_name: str) -> MetricCalculationNode:
        """Add a metric calculation node based on a definition to the shared registry.

        Looks up the metric definition, resolves required input nodes from the
        shared registry, creates the MetricCalculationNode using the factory,
        and adds it to the shared registry. Tracks the node name as a metric.

        Args:
            metric_name: The key identifying the metric in the metric registry.
                         Example: 'gross_margin'.
            node_name: The unique name to assign to the newly created metric node
                       within the shared registry. Example: 'calculated_gross_margin'.

        Returns:
            The created MetricCalculationNode, now stored in the shared registry.

        Raises:
            ValueError: If a node with `node_name` already exists in the shared registry.
            NodeError: If a required input node for the metric is not found in the
                       shared registry.
            ConfigurationError: If `metric_name` is not defined in the metric registry
                                or its definition is invalid (e.g., missing 'inputs' or 'formula').
            TypeError: If `node_name` is not a non-empty string.

        Example:
            >>> # Assuming 'gross_margin' is defined in metric_registry and requires
            >>> # 'gross_profit' and 'revenue' nodes, which exist in shared_nodes.
            >>> shared_nodes = {
            ...     'revenue': DataNode('revenue', data={'2023': 1000}),
            ...     'gross_profit': DataNode('gross_profit', data={'2023': 400})
            ... }
            >>> engine = CalculationEngine(shared_nodes)
            >>> try:
            ...     metric_node = engine.add_metric(
            ...         metric_name='gross_margin',
            ...         node_name='calculated_gross_margin'
            ...     )
            ...     print(f"Metric node '{metric_node.name}' added.")
            ... except (NodeError, ConfigurationError, ValueError) as e:
            ...     print(e)
            Metric node 'calculated_gross_margin' added.
            >>> # 'calculated_gross_margin' node is now in shared_nodes.
        """
        if not node_name or not isinstance(node_name, str):
            raise TypeError("Metric node name must be a non-empty string.")
        # Check shared registry for conflicts
        if node_name in self._nodes:
            raise ValueError(
                f"A node with name '{node_name}' already exists in the shared registry."
            )

        # 1. Look up metric definition using the registry
        try:
            metric_def = metric_registry.get(metric_name)
        except KeyError:  # Registry raises KeyError if not found
            # Use ConfigurationError for issues with definitions/config
            raise ConfigurationError(f"Unknown metric definition: '{metric_name}'")

        # metric_def = METRIC_DEFINITIONS[metric_name]
        required_input_names = metric_def.get("inputs")

        # Validate definition structure
        if required_input_names is None or not isinstance(required_input_names, list):
            raise ConfigurationError(
                f"Metric definition for '{metric_name}' is invalid: missing or invalid 'inputs' list."
            )
        if "formula" not in metric_def:
            raise ConfigurationError(
                f"Metric definition for '{metric_name}' is invalid: missing 'formula'."
            )

        # 2. Resolve input nodes from the shared self._nodes registry
        resolved_input_nodes: dict[str, Node] = {}
        missing_nodes = []
        for req_name in required_input_names:
            node = self._nodes.get(req_name)  # Look in shared registry
            if node is None:
                missing_nodes.append(req_name)
            else:
                resolved_input_nodes[req_name] = node

        if missing_nodes:
            raise NodeError(
                f"Cannot create metric '{metric_name}' (node '{node_name}'): Missing required input nodes in shared registry: {missing_nodes}"
            )

        # 3. Create the metric node using the factory
        try:
            node = self._node_factory.create_metric_node(
                name=node_name,
                metric_name=metric_name,
                input_nodes=resolved_input_nodes,
            )
        except (ValueError, TypeError, ConfigurationError, NodeError):
            logger.exception(
                "Failed to create metric node '%s' for metric '%s' via factory.",
                node_name,
                metric_name,
            )
            raise

        # 4. Add the created node to the shared registry
        # No separate _metrics dict needed, it lives in self._nodes
        self._nodes[node_name] = node
        self._metric_names.add(node_name)  # Track that this name corresponds to a metric

        logger.info(f"Added metric '{metric_name}' as node '{node_name}' to shared registry.")
        return node

    def calculate(self, node_name: str, period: str) -> float:
        """Calculate the value of a node for a specific period using the shared registry.

        Checks the internal cache first. If not found, retrieves the node from the
        shared registry, calls its `calculate` method, caches the result, and
        returns it.

        Args:
            node_name: Name of the node (must exist in the shared registry).
            period: The period identifier (e.g., '2023Q1') for which to calculate.

        Returns:
            The calculated value for the node and period.

        Raises:
            NodeError: If the node with `node_name` is not found in the shared registry.
            CalculationError: If an error occurs during the node's calculation method.
                              Wraps the original exception.
            TypeError: If the retrieved node object does not have a callable
                       `calculate` method.

        Example:
            >>> shared_nodes = {
            ...     'revenue': DataNode('revenue', data={'2023Q1': 100}),
            ...     'expenses': DataNode('expenses', data={'2023Q1': 60})
            ... }
            >>> engine = CalculationEngine(shared_nodes)
            >>> engine.add_calculation('profit', ['revenue', 'expenses'], 'subtraction')
            >>> try:
            ...     profit_q1 = engine.calculate('profit', '2023Q1')
            ...     print(f"Profit for 2023Q1: {profit_q1}")
            ... except (NodeError, CalculationError) as e:
            ...     print(e)
            Profit for 2023Q1: 40.0
            >>> # Result is now cached for ('profit', '2023Q1')
        """
        # Check calculation cache first
        if node_name in self._cache and period in self._cache[node_name]:
            logger.debug(f"Cache hit for node '{node_name}', period '{period}'")
            return self._cache[node_name][period]

        # Get the node from the shared registry
        node = self._nodes.get(node_name)

        if node is None:
            # No need to check separate _metrics dict
            raise NodeError(f"Node '{node_name}' not found in shared registry for calculation.")

        logger.debug(f"Calculating value for node '{node_name}', period '{period}'")
        # Calculate the value
        try:
            if not hasattr(node, "calculate") or not callable(node.calculate):
                raise TypeError(
                    f"Node '{node_name}' of type {type(node).__name__} does not have a callable calculate method."
                )

            value = node.calculate(period)

            # Cache the result
            if node_name not in self._cache:
                self._cache[node_name] = {}
            self._cache[node_name][period] = value
            logger.debug(
                f"Calculated value for node '{node_name}', period '{period}': {value}. Stored in cache."
            )
        except (
            NodeError,
            CalculationError,
            ValueError,
            KeyError,
            ZeroDivisionError,
        ) as e:  # Catch specific calculation-related errors
            # Let TypeError propagate as it indicates a programming error (wrong node type)
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
        else:
            return value

    def recalculate_all(self, periods: Optional[list[str]] = None) -> None:
        """Recalculate all nodes in the shared registry for the given periods.

        Clears the engine's calculation cache first. Then, if periods are provided,
        iterates through all nodes currently in the shared registry and calls
        `calculate` for each node and period to repopulate the cache. If no
        periods are given, only the cache is cleared, and recalculation happens
        lazily on subsequent `calculate` calls.

        Args:
            periods: An optional list of period identifiers (e.g., ['2023Q1', '2023Q2'])
                     to recalculate for. If None, only clears the cache.

        Example:
            >>> shared_nodes = { ... } # Setup nodes
            >>> engine = CalculationEngine(shared_nodes)
            >>> # Perform initial calculations...
            >>> engine.calculate('profit', '2023Q1')
            >>> engine.calculate('revenue', '2023Q1')
            >>> # ... Data is updated externally ...
            >>> # Force recalculation for Q1 and calculate Q2
            >>> engine.recalculate_all(periods=['2023Q1', '2023Q2'])
            >>> # Cache is repopulated for 'profit' and 'revenue' for these periods.
        """
        # Clear the engine's calculation cache before recalculating
        self.clear_cache()
        logger.info(f"Cleared calculation cache. Recalculating for periods: {periods}")

        # If no periods specified, calculation happens on demand, cache is just cleared.
        if not periods:
            logger.debug("No specific periods provided for recalculate_all. Cache cleared.")
            return

        # Recalculate all nodes in the shared registry for each period
        # We only need to iterate through self._nodes now
        node_names_to_recalculate = list(self._nodes.keys())  # Get names from shared registry
        logger.debug(
            f"Attempting to recalculate {len(node_names_to_recalculate)} nodes for {len(periods)} periods."
        )

        for node_name in node_names_to_recalculate:
            for period in periods:
                try:
                    # This will calculate and fill the cache if not already done
                    self.calculate(node_name, period)
                except Exception as e:
                    # Log specific error but continue recalculating others
                    logger.warning(
                        f"Error recalculating node '{node_name}' for period '{period}': {e}"
                    )

    def get_available_operations(self) -> dict[str, str]:
        """Retrieve the available calculation operations from the NodeFactory.

        Delegates to the internal NodeFactory to get the registered calculation
        strategies (operation types and their descriptions).

        Returns:
            A dictionary mapping operation type keys (e.g., 'addition') to their
            descriptions.

        Example:
            >>> engine = CalculationEngine({})
            >>> ops = engine.get_available_operations()
            >>> print('addition' in ops)
            True
            >>> print(ops['addition']) # doctest: +ELLIPSIS
            Adds...
        """
        # This depends only on the factory, not the nodes registry
        return self._node_factory.get_available_operations()

    def change_calculation_strategy(
        self, node_name: str, new_strategy_name: str, **kwargs: dict[str, Any]
    ) -> None:
        """Change the calculation strategy for an existing strategy-based node.

        Finds the specified node in the shared registry, verifies it's a
        StrategyCalculationNode, and then calls its `change_strategy` method.
        Clears the cache for this specific node after the change.

        Args:
            node_name: Name of the node in the shared registry whose strategy should
                       be changed. Must be an instance of StrategyCalculationNode.
            new_strategy_name: Name of the new calculation strategy to apply, which
                               must be registered in the NodeFactory.
            **kwargs: Additional arguments required by the new strategy's constructor.

        Raises:
            ValueError: If the node with `node_name` is not found in the shared registry,
                        or if it is not an instance of StrategyCalculationNode.
            LookupError: If `new_strategy_name` is not found in the NodeFactory.
            TypeError: If `**kwargs` do not match the new strategy's requirements.

        Example:
            >>> shared_nodes = {'a': DataNode('a'), 'b': DataNode('b')}
            >>> engine = CalculationEngine(shared_nodes)
            >>> calc_node = engine.add_calculation('sum_ab', ['a', 'b'], 'addition')
            >>> print(type(calc_node.strategy).__name__)
            AdditionCalculationStrategy
            >>> # Change to subtraction
            >>> try:
            ...     engine.change_calculation_strategy('sum_ab', 'subtraction')
            ...     print(type(shared_nodes['sum_ab'].strategy).__name__)
            ... except (ValueError, LookupError) as e:
            ...     print(e)
            SubtractionCalculationStrategy
            >>> # Engine cache for 'sum_ab' is cleared.
        """
        # Look up node in shared registry
        node = self._nodes.get(node_name)
        if node is None:
            raise ValueError(
                f"Node '{node_name}' not found in shared registry for changing strategy."
            )

        if not isinstance(node, StrategyCalculationNode):
            raise ValueError(
                f"Node '{node_name}' is not a strategy calculation node (type: {type(node).__name__})"
            )

        # Delegate to the node's method
        node.change_strategy(new_strategy_name, **kwargs)
        logger.info(f"Changed strategy for node '{node_name}' to '{new_strategy_name}'")

        # Clear engine cache for this node as its calculation changed
        if node_name in self._cache:
            del self._cache[node_name]
            logger.debug(f"Cleared engine cache for node '{node_name}' after strategy change.")

    def add_custom_calculation(
        self,
        name: str,
        calculation_func: Callable[..., float],
        inputs: Optional[list[str]] = None,
        description: str = "",
    ) -> Node:
        """Add a custom calculation node defined by a Python function to the registry.

        Resolves input node names from the shared registry, creates a custom
        calculation node (likely via the NodeFactory using the provided function
        as the formula), and adds it to the shared registry.

        Args:
            name: The unique name for the new custom calculation node.
            calculation_func: The Python callable (function or method) that
                              performs the calculation. It signature should match
                              the expected signature of a FormulaNode's formula
                              (e.g., `func(period: str, inputs: Dict[str, float]) -> float`).
            inputs: An optional list of names of input nodes required by the
                    `calculation_func`. These nodes must exist in the shared registry.
            description: An optional description for the custom calculation node.

        Returns:
            The newly created custom calculation node instance (typically a FormulaNode),
            now stored in the shared registry.

        Raises:
            NodeError: If any specified input node name is not found in the shared registry.
            ValueError: If `name` already exists or if the factory encounters an issue.
            TypeError: If `calculation_func` is not suitable or factory fails.

        Example:
            >>> def custom_ratio(period: str, inputs: Dict[str, float]) -> float:
            ...     return inputs['numerator'] / inputs['denominator'] if inputs['denominator'] else 0.0
            >>> shared_nodes = {
            ...     'numerator': DataNode('numerator', data={'2023': 50}),
            ...     'denominator': DataNode('denominator', data={'2023': 100})
            ... }
            >>> engine = CalculationEngine(shared_nodes)
            >>> try:
            ...     ratio_node = engine.add_custom_calculation(
            ...         name='my_ratio',
            ...         calculation_func=custom_ratio,
            ...         inputs=['numerator', 'denominator'],
            ...         description='Custom ratio calculation'
            ...     )
            ...     print(f"Custom node '{ratio_node.name}' added.")
            ...     # Now calculate it
            ...     value = engine.calculate('my_ratio', '2023')
            ...     print(f"Calculated ratio: {value}")
            ... except (NodeError, ValueError, TypeError, CalculationError) as e:
            ...     print(e)
            Custom node 'my_ratio' added.
            Calculated ratio: 0.5
        """
        # Resolve input node names from the shared registry
        resolved_inputs: list[Node] = []
        missing_nodes = []
        input_names = inputs or []  # Ensure it's a list
        for node_name in input_names:
            node = self._nodes.get(node_name)
            if node is None:
                missing_nodes.append(node_name)
            else:
                resolved_inputs.append(node)

        if missing_nodes:
            raise NodeError(
                f"Cannot create custom calculation node '{name}': Missing required input nodes: {missing_nodes}"
            )

        # Create the custom calculation node using the factory with resolved nodes
        # Assuming factory has _create_custom_node_from_callable or similar internal method
        # Let's assume NodeFactory needs update if add_custom_calculation is public
        # Check NodeFactory: it has _create_custom_node_from_callable
        # This engine method should probably use that factory method.
        try:
            # Use the (renamed) factory method
            node = self._node_factory._create_custom_node_from_callable(
                name=name,
                inputs=resolved_inputs,  # Pass resolved nodes
                formula=calculation_func,  # Pass the callable
                description=description,
            )
        except (NodeError, ValueError, TypeError):
            logger.exception(
                "Failed to create custom calculation node '%s' via factory.",
                name,
            )
            raise

        # Add to the shared node registry
        if name in self._nodes:
            logger.warning(f"Overwriting existing node in shared registry: '{name}'")
        self._nodes[name] = node
        logger.info(f"Added custom calculation node '{name}' to shared registry.")

        return node

    def add_calculation_node(self, node: Node):
        """Add an existing, pre-constructed node instance directly to the registry.

        Useful for integrating nodes created outside the engine's factory methods.
        Warns if a node with the same name already exists, overwriting it.

        Args:
            node: The fully instantiated Node object to add to the shared registry.
                  Its `name` attribute will be used as the key.

        Example:
            >>> class MySpecialNode(Node):
            ...    def calculate(self, period): return 42
            ...
            >>> special_node = MySpecialNode(name="special_value")
            >>> shared_nodes = {}
            >>> engine = CalculationEngine(shared_nodes)
            >>> engine.add_calculation_node(special_node)
            >>> print('special_value' in shared_nodes)
            True
            >>> print(engine.calculate('special_value', 'any_period'))
            42.0
        """
        if node.name in self._nodes:
            logger.warning(f"Overwriting existing node in shared registry: '{node.name}'")
        self._nodes[node.name] = node
        logger.info(f"Added pre-constructed node '{node.name}' to shared registry.")

    def get_metric(self, metric_id: str) -> Optional[Node]:
        """Retrieve a metric node by its name (ID) from the shared registry.

        Looks up the `metric_id` in the shared registry and checks if it was
        specifically registered as a metric (via `add_metric`).

        Args:
            metric_id: The name of the node that was registered as a metric.

        Returns:
            The Node instance if found and registered as a metric, otherwise None.

        Example:
            >>> # Assume 'gm_calc' was added via engine.add_metric(...)
            >>> shared_nodes = { ... }
            >>> engine = CalculationEngine(shared_nodes)
            >>> # ... engine.add_metric('gross_margin', 'gm_calc') ...
            >>> metric_node = engine.get_metric('gm_calc')
            >>> if metric_node:
            ...    print(f"Found metric node: {metric_node.name}")
            >>> else:
            ...    print("Metric node not found or not registered as metric.")

        """
        # Metrics are just nodes in the shared registry
        node = self._nodes.get(metric_id)
        if node and metric_id in self._metric_names:
            return node
        # Return None if not found or if the name doesn't correspond to a known metric
        return None

    def get_available_metrics(self) -> list[str]:
        """Get a sorted list of names for all nodes currently registered as metrics.

        Returns:
            A list containing the names of nodes added via `add_metric`.

        Example:
            >>> # Assume 'gm_calc' and 'npm_calc' were added via engine.add_metric(...)
            >>> shared_nodes = { ... }
            >>> engine = CalculationEngine(shared_nodes)
            >>> # ... engine.add_metric('gross_margin', 'gm_calc') ...
            >>> # ... engine.add_metric('net_profit_margin', 'npm_calc') ...
            >>> metric_names = engine.get_available_metrics()
            >>> print(metric_names) # Should be sorted
            ['gm_calc', 'npm_calc']
        """
        # Return the names we tracked when adding metrics
        return sorted(list(self._metric_names))

    def get_metric_info(self, metric_id: str) -> Optional[dict]:
        """Get descriptive information about a specific metric node.

        Retrieves the metric node using `get_metric` and extracts details like
        its name, description, and input dependencies.

        Args:
            metric_id: The name (ID) of the metric node to query.

        Returns:
            A dictionary containing information about the metric ('name',
            'description', 'inputs'), or None if the metric node cannot be found.
            Note: Returns None is deprecated, raises ValueError instead.

        Raises:
            ValueError: If a node with `metric_id` exists but was not registered
                        as a metric, or if no node with `metric_id` is found at all.

        Example:
            >>> # Assume 'gm_calc' was added via engine.add_metric(...)
            >>> # and requires 'gross_profit', 'revenue'.
            >>> shared_nodes = { ... }
            >>> engine = CalculationEngine(shared_nodes)
            >>> # ... engine.add_metric('gross_margin', 'gm_calc', ...) ...
            >>> try:
            ...     info = engine.get_metric_info('gm_calc')
            ...     print(f"Name: {info['name']}")
            ...     print(f"Inputs: {info['inputs']}") # Example output
            ... except ValueError as e:
            ...     print(e)
            Name: gm_calc
            Inputs: ['gross_profit', 'revenue']
        """
        # Get the node (must be a tracked metric name)
        node = self.get_metric(metric_id)
        if node is None:
            # Raise error if the ID is totally unknown or just not a metric?
            # Let's be specific: raise if it's not a known metric ID.
            if metric_id in self._nodes:
                raise ValueError(f"Node '{metric_id}' exists but was not registered as a metric.")
            else:
                raise ValueError(f"Metric with ID '{metric_id}' not found.")

        # Construct info dict - assumes MetricCalculationNode structure or similar
        info = {
            "name": node.name,
            "description": getattr(node, "description", None),  # Handle if no description
        }
        # Get dependencies based on the node type or method
        if hasattr(node, "get_dependencies"):
            try:
                info["inputs"] = node.get_dependencies()  # Assumes returns list of names
            except Exception as e:
                logger.warning(f"Could not get dependencies for metric '{metric_id}': {e}")
                info["inputs"] = []  # Default to empty list on error
        elif (
            hasattr(node, "inputs") and node.inputs is not None
        ):  # Check if inputs attr exists and is not None
            # Fallback: try to get names from inputs attribute if it exists
            if isinstance(node.inputs, list):  # StrategyNode, CustomNode
                info["inputs"] = [inp.name for inp in node.inputs if hasattr(inp, "name")]
            elif isinstance(node.inputs, dict):  # FormulaNode, MetricNode
                # Get the names of the nodes held in the input dictionary values
                info["inputs"] = [inp.name for inp in node.inputs.values() if hasattr(inp, "name")]
            else:
                info["inputs"] = []
        else:
            info["inputs"] = []

        return info

    def clear_cache(self):
        """Clear the engine's internal calculation cache entirely.

        This forces recalculation of values upon the next `calculate` call for
        any node and period.

        Example:
            >>> engine = CalculationEngine({})
            >>> # ... perform some calculations, cache gets populated ...
            >>> engine.clear_cache()
            >>> # Subsequent calls to engine.calculate() will recompute values.
        """
        self._cache.clear()
        logger.info("Calculation engine cache cleared.")

    def reset(self):
        """Reset the calculation engine's state, clearing cache and metric tracking.

        This method clears the internal calculation cache and the set of tracked
        metric names. It **does not** modify the shared `_nodes` registry itself,
        as that is managed externally (e.g., by a Graph instance).

        Example:
            >>> engine = CalculationEngine({})
            >>> # ... add metrics, perform calculations ...
            >>> engine.reset()
            >>> print(engine.get_available_metrics())
            []
            >>> # Cache is also empty, but shared_nodes registry is unaffected.
        """
        # Does NOT clear self._nodes as it's shared and owned by Graph
        self.clear_cache()
        self._metric_names.clear()
        logger.info("Calculation engine reset (cache and metric tracking cleared).")

    def _execute_dependencies(self, node_id: str, period: str, **kwargs: dict[str, Any]) -> dict:
        """Recursively execute dependencies for a node.

        This method is used internally to handle dependencies between nodes.
        It recursively calculates the value of a node based on its dependencies.

        Args:
            node_id: The ID of the node to calculate.
            period: The period for which to calculate the node.
            **kwargs: Additional keyword arguments to pass to the node's calculate method.

        Returns:
            A dictionary containing the calculated value and any errors encountered.
        """
        # Placeholder implementation - needs actual logic
        logger.warning(
            f"_execute_dependencies for {node_id} period {period} is not fully implemented."
        )
        return {"value": None, "errors": ["Not Implemented"]}
