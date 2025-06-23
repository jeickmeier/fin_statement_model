"""Calculation engine stub extracted from Graph.

CalculationEngine is an isolated service that orchestrates calculations and cache management for the Graph.
It is responsible for evaluating node values, managing the calculation cache, and supporting the addition
of calculation nodes and metrics. All calculation logic is delegated here from the Graph and its mix-ins.

Key responsibilities:
    - Calculate node values for specific periods
    - Manage a central calculation cache
    - Add calculation nodes and metrics
    - Support custom calculation functions
    - Change calculation methods for nodes
    - Provide metric inspection helpers

Examples:
    >>> from fin_statement_model.core.graph import Graph
    >>> g = Graph(periods=["2023"])
    >>> _ = g.add_financial_statement_item("Revenue", {"2023": 100.0})
    >>> _ = g.add_financial_statement_item("COGS", {"2023": 60.0})
    >>> _ = g.add_calculation(
    ...     name="GrossProfit",
    ...     input_names=["Revenue", "COGS"],
    ...     operation_type="formula",
    ...     formula="input_0 - input_1",
    ...     formula_variable_names=["input_0", "input_1"],
    ... )
    >>> g.calculate("GrossProfit", "2023")
    40.0
    >>> g.get_available_metrics()
    []

# pragma: no cover

This module defines ``CalculationEngine`` - an isolated service that will
orchestrate calculations and cache management for ``Graph``.  At this stage it
contains only minimal scaffolding so that other modules can import it without
runtime errors.  Full logic will be migrated in step 1.3 of the refactor plan.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable

    from fin_statement_model.core.metrics.models import MetricDefinition
    from fin_statement_model.core.node_factory import NodeFactory
    from fin_statement_model.core.nodes import Node

# Local imports deliberately avoid importing Graph to meet step 1.2 criteria

__all__: list[str] = ["CalculationEngine"]


class CalculationEngine:  # pylint: disable=too-few-public-methods
    """Isolated calculation orchestration service.

    Args:
        node_resolver: Callable that, given a node name, returns a ``Node`` instance.
        period_provider: Zero-arg callable returning the list of available periods.
        node_names_provider: Zero-arg callable returning the list of all node names.
        # Builder-helper collaborators
        node_factory: "NodeFactory"
        nodes_dict: Dict[str, "Node"]
        add_node_with_validation: Callable[["Node"], "Node"]
        resolve_input_nodes: Callable[[List[str]], List["Node"]]
        add_periods: Callable[[List[str]], None]
        cache: Optional pre-populated two-level cache mapping ``node_name → period → value``.
    """

    def __init__(
        self,
        *,
        node_resolver: Callable[[str], Node],
        period_provider: Callable[[], list[str]],
        node_names_provider: Callable[[], list[str]],
        # Builder-helper collaborators
        node_factory: NodeFactory,
        nodes_dict: dict[str, Node],
        add_node_with_validation: Callable[[Node], Node],
        resolve_input_nodes: Callable[[list[str]], list[Node]],
        add_periods: Callable[[list[str]], None],
        cache: dict[str, dict[str, float]] | None = None,
    ) -> None:
        """Instantiate a CalculationEngine detached from the public Graph API.

        The constructor relies on *dependency injection* - it receives a set of
        callables and shared data structures from the owning ``Graph`` instance
        instead of importing it directly.  This decouples the engine and avoids
        circular dependencies during the ongoing refactor.

        Args:
            node_resolver: Callable resolving a node name to the concrete
                :class:`fin_statement_model.core.nodes.base.Node` instance.
            period_provider: Callable returning the list of currently known
                period identifiers.
            node_names_provider: Callable yielding all node names present in
                the graph (used by *recalc_all*).
            node_factory: Shared ``NodeFactory`` instance used for
                programmatic node creation.
            nodes_dict: Reference to the graph's internal ``_nodes`` mapping so
                the engine can access already-instantiated nodes.
            add_node_with_validation: Helper that adds a node to the graph and
                performs validation (cycle detection, name clashes, …).
            resolve_input_nodes: Helper translating input *names* to concrete
                node objects, leveraging the owning graph's capabilities.
            add_periods: Callable allowing the engine to add new periods to the
                graph when calculation helpers need to expand the timeline.
            cache: Optional pre-populated calculation cache.  When *None*, a
                fresh empty cache is created.
        """
        # Internal state - no external Graph refs
        self._node_resolver = node_resolver
        self._period_provider = period_provider
        self._node_names_provider = node_names_provider
        self._cache: dict[str, dict[str, float]] = cache or {}

        # Store builder collaborators
        self._node_factory = node_factory
        self._nodes = nodes_dict  # direct reference to Graph._nodes
        self._add_node_with_validation = add_node_with_validation
        self._resolve_input_nodes = resolve_input_nodes
        self._add_periods = add_periods

    # ---------------------------------------------------------------------
    # Public API (stubs)
    # ---------------------------------------------------------------------
    def calculate(self, node_name: str, period: str) -> float:
        """Calculate and return the value of *node_name* for *period*.

        This is mostly a verbatim copy of the original ``Graph.calculate`` method,
        refactored to work in isolation:

        * Uses ``_node_resolver`` instead of ``Graph.manipulator.get_node``.
        * Writes/reads central cache owned by the engine.
        * Raises the same domain-specific errors so callers' behaviour is
          unchanged.
        """
        import logging  # local to avoid circular deps at import time

        # Import only for type consistency / side-effects. NodeError is unused but
        # kept here to mirror original Graph behaviour without altering public
        # re-export expectations.
        from fin_statement_model.core.errors import (
            CalculationError,
            ConfigurationError,
            NodeError,
        )

        logger = logging.getLogger(__name__)

        # Fast-path cache hit ------------------------------------------------
        if node_name in self._cache and period in self._cache[node_name]:
            logger.debug("Cache hit for node '%s', period '%s'", node_name, period)
            return self._cache[node_name][period]

        # Resolve node ------------------------------------------------------
        node = self._node_resolver(node_name)
        if node is None:  # pragma: no cover - resolver must mirror Graph semantics
            raise NodeError(f"Node '{node_name}' not found", node_id=node_name)

        # Validate calculate method ----------------------------------------
        if not hasattr(node, "calculate") or not callable(node.calculate):
            raise TypeError(f"Node '{node_name}' has no callable calculate method.")

        # Perform calculation ---------------------------------------------
        try:
            value = node.calculate(period)
        except (
            NodeError,
            ConfigurationError,
            CalculationError,
            ValueError,
            KeyError,
            ZeroDivisionError,
        ) as exc:
            logger.exception(
                "Error calculating node '%s' for period '%s'",
                node_name,
                period,
            )
            raise CalculationError(
                message=f"Failed to calculate node '{node_name}'",
                node_id=node_name,
                period=period,
                details={"original_error": str(exc)},
            ) from exc

        # Cache & return ----------------------------------------------------
        self._cache.setdefault(node_name, {})[period] = value
        logger.debug("Cached value for node '%s', period '%s': %s", node_name, period, value)
        return value

    def recalc_all(self, periods: list[str] | None = None) -> None:
        """Recalculate every node for *periods*.

        Implementation mimics original ``Graph.recalculate_all`` but requires the
        caller to iterate over all node names.  Because *CalculationEngine* does
        not (and should not) know the graph's registry, we expose a simple
        fallback behaviour: raise *NotImplementedError* until the graph passes
        an explicit list of node names via ``periods`` parameter being *not*
        `None` **and** provides a helper attribute ``_all_node_names``.
        The Graph façade will shim this in step 1.3.
        """
        import logging

        from fin_statement_model.core.errors import FinStatementModelError

        # Import only for type consistency / side-effects. NodeError is unused but
        # kept here to mirror original Graph behaviour without altering public
        # re-export expectations.

        logger = logging.getLogger(__name__)

        # Determine periods list - mirror Graph logic ----------------------
        if periods is None:
            periods_to_use = self._period_provider()
        elif isinstance(periods, str):
            periods_to_use = [periods]
        elif isinstance(periods, list):
            periods_to_use = periods
        else:
            raise TypeError("Periods must be a list of strings, a single string, or None.")

        # Clear central cache to force recalculation -----------------------
        self.clear_all()

        if not periods_to_use:
            return

        for node_name in list(self._node_names_provider()):
            for period in periods_to_use:
                try:
                    self.calculate(node_name, period)
                except FinStatementModelError as exc:
                    # Match Graph behaviour: log & continue
                    logger.warning(
                        "Error recalculating node '%s' for period '%s': %s",
                        node_name,
                        period,
                        exc,
                    )

    # Cache-management helpers ------------------------------------------------
    def clear_all(self) -> None:
        """Clear the internal calculation cache (stub)."""
        self._cache.clear()

    # Convenience: expose cache for future injection/tests -------------------
    @property
    def cache(self) -> dict[str, dict[str, float]]:
        """Return the underlying two-level cache mapping."""
        return self._cache

    # ------------------------------------------------------------------
    #  Builder helpers moved from Graph
    # ------------------------------------------------------------------

    def add_calculation(
        self,
        name: str,
        input_names: list[str],
        operation_type: str,
        formula_variable_names: list[str] | None = None,
        **calculation_kwargs: Any,
    ) -> Node:
        """Add a calculation node to the graph.

        Ported verbatim from ``Graph.add_calculation`` - only collaborators
        replaced with attributes on ``CalculationEngine``.
        """
        # -----------------------------------------------------------------
        # Default variable names for formula calculations
        # -----------------------------------------------------------------
        # For formula-based calculation nodes, if no explicit
        # ``formula_variable_names`` are provided we default to using the
        # ``input_names``.  This allows authors to write formulas directly
        # with the original input names instead of the positional
        # ``input_0``/``input_1`` aliases.  The previous behaviour (falling
        # back to positional variables) is still available by explicitly
        # passing a list such as ``["input_0", "input_1", ...]``.
        if operation_type == "formula" and formula_variable_names is None:
            formula_variable_names = input_names.copy()

        # Validate inputs --------------------------------------------------
        if not isinstance(input_names, list):
            raise TypeError("input_names must be a list of node names.")

        # Resolve input node names to Node objects -------------------------
        resolved_inputs = self._resolve_input_nodes(input_names)

        # Create the node via factory -------------------------------------
        try:
            node = self._node_factory.create_calculation_node(
                name=name,
                inputs=resolved_inputs,
                calculation_type=operation_type,
                formula_variable_names=formula_variable_names,
                **calculation_kwargs,
            )
        except (ValueError, TypeError):
            import logging

            logger = logging.getLogger(__name__)
            logger.exception(
                "Failed to create calculation node '%s' with type '%s'",
                name,
                operation_type,
            )
            raise

        # Add with validation (includes cycle detection) ------------------
        added_node = self._add_node_with_validation(node)

        import logging

        logging.getLogger(__name__).info(
            "Added calculation node '%s' of type '%s' with inputs %s",
            name,
            operation_type,
            input_names,
        )
        return added_node

    def _load_metric_definition(self, metric_name: str) -> MetricDefinition:
        """Return the metric definition for *metric_name* or raise ConfigurationError."""
        from fin_statement_model.core.errors import ConfigurationError
        from fin_statement_model.core.metrics import metric_registry

        try:
            return metric_registry.get(metric_name)
        except KeyError as exc:
            raise ConfigurationError(f"Unknown metric definition: '{metric_name}'") from exc

    def _map_metric_inputs(
        self,
        required_inputs: list[str],
        input_node_map: dict[str, str] | None,
    ) -> tuple[list[str], list[str]]:
        """Resolve and validate input nodes for a metric.

        Args:
            required_inputs: The inputs defined by the metric.
            input_node_map: Optional caller-provided mapping from required input
                names to actual node IDs in the graph.

        Returns:
            A tuple ``(input_node_names, formula_variable_names)``.

        Raises:
            NodeError: If any required input nodes are missing.
        """
        from fin_statement_model.core.errors import NodeError

        missing: list[str] = []
        input_node_names: list[str] = []
        formula_variable_names: list[str] = []

        for req_input in required_inputs:
            target_node = input_node_map.get(req_input) if input_node_map and req_input in input_node_map else req_input

            if target_node not in self._nodes:
                # Cast to str to satisfy static type checker (target_node can be None if mapping missing)
                missing.append(str(target_node))
            else:
                input_node_names.append(target_node)
                formula_variable_names.append(req_input)

        if missing:
            raise NodeError(
                f"Missing required nodes {missing}",
                node_id=",".join(missing),
            )

        return input_node_names, formula_variable_names

    # ------------------------------------------------------------------
    # Metric helpers
    # ------------------------------------------------------------------

    def add_metric(
        self,
        metric_name: str,
        node_name: str | None = None,
        *,
        input_node_map: dict[str, str] | None = None,
    ) -> Node:
        """Add a metric calculation node based on a metric definition."""
        from fin_statement_model.core.errors import ConfigurationError, NodeError

        # Derive node_name -------------------------------------------------
        node_name = node_name or metric_name
        if not node_name or not isinstance(node_name, str):
            raise TypeError("Metric node name must be a non-empty string.")
        if node_name in self._nodes:
            raise ValueError(f"A node with name '{node_name}' already exists in the graph.")

        # Load metric definition ------------------------------------------
        metric_def = self._load_metric_definition(metric_name)

        # Map & validate inputs -------------------------------------------
        try:
            input_node_names, formula_variable_names = self._map_metric_inputs(metric_def.inputs, input_node_map)
        except NodeError as exc:
            # Re-wrap with better context keeping compatibility
            raise NodeError(f"Cannot create metric '{metric_name}': {exc}", node_id=node_name) from exc

        # Create underlying calculation node ------------------------------
        try:
            new_node = self.add_calculation(
                name=node_name,
                input_names=input_node_names,
                operation_type="formula",
                formula_variable_names=formula_variable_names,
                formula=metric_def.formula,
                metric_name=metric_name,
                metric_description=metric_def.description,
            )
        except Exception as exc:
            import logging

            logging.getLogger(__name__).exception(
                "Failed to create calculation node for metric '%s' as node '%s'",
                metric_name,
                node_name,
            )
            raise ConfigurationError(f"Error creating node for metric '{metric_name}': {exc}") from exc

        import logging

        logging.getLogger(__name__).info(
            "Added metric '%s' as calculation node '%s' with inputs %s",
            metric_name,
            node_name,
            input_node_names,
        )
        return new_node

    # ------------------------------------------------------------------
    # Additional helpers ported from Graph
    # ------------------------------------------------------------------

    def add_custom_calculation(
        self,
        name: str,
        calculation_func: Callable[..., float],
        inputs: list[str] | None = None,
        description: str = "",
    ) -> Node:
        """Add a custom calculation node using a Python callable."""
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
            custom_node = self._node_factory._create_custom_node_from_callable(  # pylint: disable=protected-access
                name=name,
                inputs=resolved_inputs,
                formula=calculation_func,
                description=description,
            )
        except (ValueError, TypeError):
            import logging

            logging.getLogger(__name__).exception("Failed to create custom calculation node '%s'", name)
            raise

        # Add with validation
        added_node = self._add_node_with_validation(custom_node)

        import logging

        logging.getLogger(__name__).info("Added custom calculation node '%s' with inputs %s", name, inputs)
        return added_node

    def ensure_signed_nodes(self, base_node_ids: list[str], *, suffix: str = "_signed") -> list[str]:
        """Ensure signed calculation nodes (-1 * input) exist for each base node."""
        created: list[str] = []
        for base_id in base_node_ids:
            signed_id = f"{base_id}{suffix}"
            if signed_id in self._nodes:
                continue
            if base_id not in self._nodes:
                from fin_statement_model.core.errors import NodeError

                raise NodeError(
                    f"Cannot create signed node for missing base node '{base_id}'",
                    node_id=base_id,
                )
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
        """Change the calculation method for an existing calculation-based node."""
        from fin_statement_model.core.calculations import Registry
        from fin_statement_model.core.errors import NodeError
        from fin_statement_model.core.nodes import CalculationNode

        node = self._nodes.get(node_name)
        if node is None:
            raise NodeError("Node not found for calculation change", node_id=node_name)
        if not isinstance(node, CalculationNode):
            raise NodeError(f"Node '{node_name}' is not a CalculationNode", node_id=node_name)

        if new_method_key not in self._node_factory._calculation_methods:  # pylint: disable=protected-access
            raise ValueError(f"Calculation '{new_method_key}' is not recognized.")

        calculation_class_name = self._node_factory._calculation_methods[new_method_key]  # pylint: disable=protected-access

        try:
            calculation_cls = Registry.get(calculation_class_name)
        except KeyError as exc:
            raise ValueError(f"Calculation class '{calculation_class_name}' not found in registry.") from exc

        try:
            calculation_instance = calculation_cls(**kwargs)
        except TypeError as exc:
            raise TypeError(f"Failed to instantiate calculation '{new_method_key}': {exc}") from exc

        node.set_calculation(calculation_instance)

        # Clear cached calculations for this node
        if node_name in self._cache:
            del self._cache[node_name]

    # ---------------- Metric query helpers -------------------------------

    def get_metric(self, metric_id: str) -> Node | None:
        """Return the *metric* node for *metric_id* if it exists.

        Args:
            metric_id: The canonical identifier of the metric node to fetch.

        Returns:
            The corresponding :class:`fin_statement_model.core.nodes.base.Node` if
            present *and* marked as a metric (``metric_name`` attribute),
            otherwise ``None``.
        """
        node = self._nodes.get(metric_id)
        if node and getattr(node, "metric_name", None) == metric_id:
            return node
        return None

    def get_available_metrics(self) -> list[str]:
        """Return the IDs of all metrics currently available in the graph."""
        return sorted([n.name for n in self._nodes.values() if getattr(n, "metric_name", None)])

    def get_metric_info(self, metric_id: str) -> dict[str, Any]:
        """Return a human-readable information dictionary for *metric_id*.

        The helper consolidates information from the metric definition registry
        and the concrete metric node to provide callers with a lightweight
        metadata payload (used by CLI / UI front-ends).

        Args:
            metric_id: Identifier of the metric node.

        Raises:
            ValueError: If the requested metric does not exist or is not a
                metric node.

        Returns:
            A dictionary containing keys ``id``, ``name``, ``description`` and
            ``inputs``.
        """
        from fin_statement_model.core.metrics import metric_registry

        metric_node = self.get_metric(metric_id)
        if metric_node is None:
            if metric_id in self._nodes:
                raise ValueError(f"Node '{metric_id}' exists but is not a metric (missing metric_name attribute).")
            raise ValueError(f"Metric node '{metric_id}' not found in graph.")

        description = getattr(metric_node, "metric_description", "N/A")
        registry_key = getattr(metric_node, "metric_name", metric_id)

        try:
            metric_def = metric_registry.get(registry_key)
            display_name = metric_def.name
        except KeyError:
            display_name = metric_id

        inputs = metric_node.get_dependencies() if hasattr(metric_node, "get_dependencies") else []

        return {
            "id": metric_id,
            "name": display_name,
            "description": description,
            "inputs": inputs,
        }
