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
    ...     formula_variable_names=["input_0", "input_1"]
    ... )
    >>> g.calculate("GrossProfit", "2023")
    40.0
    >>> g.get_available_metrics()
    []

# pragma: no cover

This module defines ``CalculationEngine`` – an isolated service that will
orchestrate calculations and cache management for ``Graph``.  At this stage it
contains only minimal scaffolding so that other modules can import it without
runtime errors.  Full logic will be migrated in step 1.3 of the refactor plan.
"""

from __future__ import annotations

from typing import Callable, Optional, Dict, Any, List

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from fin_statement_model.core.node_factory import NodeFactory

# Local imports deliberately avoid importing Graph to meet step 1.2 criteria
from fin_statement_model.core.nodes import Node  # allowed (core-level)

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
        period_provider: Callable[[], List[str]],
        node_names_provider: Callable[[], List[str]],
        # Builder-helper collaborators
        node_factory: "NodeFactory",
        nodes_dict: Dict[str, "Node"],
        add_node_with_validation: Callable[["Node"], "Node"],
        resolve_input_nodes: Callable[[List[str]], List["Node"]],
        add_periods: Callable[[List[str]], None],
        cache: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> None:
        # Internal state – no external Graph refs
        self._node_resolver = node_resolver
        self._period_provider = period_provider
        self._node_names_provider = node_names_provider
        self._cache: Dict[str, Dict[str, float]] = cache or {}

        # Store builder collaborators
        self._node_factory = node_factory
        self._nodes = nodes_dict  # direct reference to Graph._nodes
        self._add_node_with_validation = add_node_with_validation
        self._resolve_input_nodes = resolve_input_nodes
        self._add_periods = add_periods

    # ---------------------------------------------------------------------
    # Public API (stubs)
    # ---------------------------------------------------------------------
    def calculate(self, node_name: str, period: str) -> float:  # noqa: D401
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
            NodeError,
            ConfigurationError,
        )  # noqa: F401

        logger = logging.getLogger(__name__)

        # Fast-path cache hit ------------------------------------------------
        if node_name in self._cache and period in self._cache[node_name]:
            logger.debug("Cache hit for node '%s', period '%s'", node_name, period)
            return self._cache[node_name][period]

        # Resolve node ------------------------------------------------------
        node = self._node_resolver(node_name)
        if node is None:  # pragma: no cover – resolver must mirror Graph semantics
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
            logger.error(
                "Error calculating node '%s' for period '%s': %s",
                node_name,
                period,
                exc,
                exc_info=True,
            )
            raise CalculationError(
                message=f"Failed to calculate node '{node_name}'",
                node_id=node_name,
                period=period,
                details={"original_error": str(exc)},
            ) from exc

        # Cache & return ----------------------------------------------------
        self._cache.setdefault(node_name, {})[period] = value
        logger.debug(
            "Cached value for node '%s', period '%s': %s", node_name, period, value
        )
        return value

    def recalc_all(self, periods: Optional[List[str]] = None) -> None:  # noqa: D401
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

        # Import only for type consistency / side-effects. NodeError is unused but
        # kept here to mirror original Graph behaviour without altering public
        # re-export expectations.

        logger = logging.getLogger(__name__)

        # Determine periods list – mirror Graph logic ----------------------
        if periods is None:
            periods_to_use = self._period_provider()
        elif isinstance(periods, str):
            periods_to_use = [periods]
        elif isinstance(periods, list):
            periods_to_use = periods
        else:
            raise TypeError(
                "Periods must be a list of strings, a single string, or None."
            )

        # Clear central cache to force recalculation -----------------------
        self.clear_all()

        if not periods_to_use:
            return

        for node_name in list(self._node_names_provider()):
            for period in periods_to_use:
                try:
                    self.calculate(node_name, period)
                except Exception as exc:  # noqa: BLE001
                    # Match Graph behaviour: log & continue
                    logger.warning(
                        "Error recalculating node '%s' for period '%s': %s",
                        node_name,
                        period,
                        exc,
                    )

    # Cache-management helpers ------------------------------------------------
    def clear_all(self) -> None:  # noqa: D401
        """Clear the internal calculation cache (stub)."""
        self._cache.clear()

    # Convenience: expose cache for future injection/tests -------------------
    @property
    def cache(self) -> Dict[str, Dict[str, float]]:  # noqa: D401
        """Return the underlying two-level cache mapping."""
        return self._cache

    # ------------------------------------------------------------------
    #  Builder helpers moved from Graph
    # ------------------------------------------------------------------

    def add_calculation(
        self,
        name: str,
        input_names: List[str],
        operation_type: str,
        formula_variable_names: Optional[List[str]] = None,
        **calculation_kwargs: Any,
    ) -> Node:
        """Add a calculation node to the graph.

        Ported verbatim from ``Graph.add_calculation`` – only collaborators
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

    def add_metric(
        self,
        metric_name: str,
        node_name: Optional[str] = None,
        *,
        input_node_map: Optional[Dict[str, str]] = None,
    ) -> Node:
        """Add a metric calculation node based on a metric definition.

        This is a direct port of ``Graph.add_metric`` with references adjusted
        to use collaborators injected into ``CalculationEngine``.
        """
        from fin_statement_model.core.metrics import metric_registry
        from fin_statement_model.core.errors import (
            NodeError,
            ConfigurationError,
        )

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
        except KeyError as exc:
            raise ConfigurationError(
                f"Unknown metric definition: '{metric_name}'"
            ) from exc

        required_inputs = metric_def.inputs
        formula = metric_def.formula
        description = metric_def.description

        input_node_names: List[str] = []
        formula_variable_names: List[str] = []
        missing: List[str] = []

        for req_input_name in required_inputs:
            target_node_name = req_input_name  # default
            if input_node_map and req_input_name in input_node_map:
                target_node_name = input_node_map[req_input_name]
            elif input_node_map:
                missing.append(f"{req_input_name} (mapping missing in input_node_map)")
                continue

            if target_node_name not in self._nodes:
                missing.append(target_node_name)
            else:
                input_node_names.append(target_node_name)
                formula_variable_names.append(req_input_name)

        if missing:
            raise NodeError(
                f"Cannot create metric '{metric_name}': missing required nodes {missing}",
                node_id=node_name,
            )

        # Reuse add_calculation helper -----------------------------------
        try:
            new_node = self.add_calculation(
                name=node_name,
                input_names=input_node_names,
                operation_type="formula",
                formula_variable_names=formula_variable_names,
                formula=formula,
                metric_name=metric_name,
                metric_description=description,
            )
        except Exception as exc:  # noqa: BLE001
            import logging

            logging.getLogger(__name__).exception(
                "Failed to create calculation node for metric '%s' as node '%s'",
                metric_name,
                node_name,
            )
            raise ConfigurationError(
                f"Error creating node for metric '{metric_name}': {exc}"
            ) from exc

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
        inputs: Optional[List[str]] = None,
        description: str = "",
    ) -> Node:
        """Add a custom calculation node using a Python callable."""
        # Validate callable
        if not callable(calculation_func):
            raise TypeError("calculation_func must be callable.")

        # Resolve inputs if provided
        resolved_inputs: List[Node] = []
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

            logging.getLogger(__name__).exception(
                "Failed to create custom calculation node '%s'", name
            )
            raise

        # Add with validation
        added_node = self._add_node_with_validation(custom_node)

        import logging

        logging.getLogger(__name__).info(
            "Added custom calculation node '%s' with inputs %s", name, inputs
        )
        return added_node

    def ensure_signed_nodes(
        self, base_node_ids: List[str], *, suffix: str = "_signed"
    ) -> List[str]:
        """Ensure signed calculation nodes (-1 * input) exist for each base node."""
        created: List[str] = []
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
        **kwargs: Dict[str, Any],
    ) -> None:
        """Change the calculation method for an existing calculation-based node."""
        from fin_statement_model.core.nodes import CalculationNode
        from fin_statement_model.core.calculations import Registry

        from fin_statement_model.core.errors import NodeError

        node = self._nodes.get(node_name)
        if node is None:
            raise NodeError("Node not found for calculation change", node_id=node_name)
        if not isinstance(node, CalculationNode):
            raise NodeError(
                f"Node '{node_name}' is not a CalculationNode", node_id=node_name
            )

        if (
            new_method_key not in self._node_factory._calculation_methods
        ):  # pylint: disable=protected-access
            raise ValueError(f"Calculation '{new_method_key}' is not recognized.")

        calculation_class_name = self._node_factory._calculation_methods[
            new_method_key
        ]  # pylint: disable=protected-access

        try:
            calculation_cls = Registry.get(calculation_class_name)
        except KeyError as exc:
            raise ValueError(
                f"Calculation class '{calculation_class_name}' not found in registry."
            ) from exc

        try:
            calculation_instance = calculation_cls(**kwargs)
        except TypeError as exc:
            raise TypeError(
                f"Failed to instantiate calculation '{new_method_key}': {exc}"
            )

        node.set_calculation(calculation_instance)

        # Clear cached calculations for this node
        if node_name in self._cache:
            del self._cache[node_name]

    # ---------------- Metric query helpers -------------------------------

    def get_metric(self, metric_id: str) -> Optional[Node]:
        node = self._nodes.get(metric_id)
        if node and getattr(node, "metric_name", None) == metric_id:
            return node
        return None

    def get_available_metrics(self) -> List[str]:
        return sorted(
            [n.name for n in self._nodes.values() if getattr(n, "metric_name", None)]
        )

    def get_metric_info(self, metric_id: str) -> Dict[str, Any]:
        from fin_statement_model.core.metrics import metric_registry

        metric_node = self.get_metric(metric_id)
        if metric_node is None:
            if metric_id in self._nodes:
                raise ValueError(
                    f"Node '{metric_id}' exists but is not a metric (missing metric_name attribute)."
                )
            raise ValueError(f"Metric node '{metric_id}' not found in graph.")

        description = getattr(metric_node, "metric_description", "N/A")
        registry_key = getattr(metric_node, "metric_name", metric_id)

        try:
            metric_def = metric_registry.get(registry_key)
            display_name = metric_def.name
        except Exception:  # noqa: BLE001
            display_name = metric_id

        inputs = (
            metric_node.get_dependencies()
            if hasattr(metric_node, "get_dependencies")
            else []
        )

        return {
            "id": metric_id,
            "name": display_name,
            "description": description,
            "inputs": inputs,
        }
