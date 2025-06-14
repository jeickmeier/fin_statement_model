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

from __future__ import annotations

import logging
from typing import Any, Optional, cast, Union, Iterable
from collections.abc import Callable
from uuid import UUID

from fin_statement_model.core.node_factory import NodeFactory
from fin_statement_model.core.nodes import Node, FinancialStatementItemNode
from fin_statement_model.core.graph.services import (
    CalculationEngine,
    PeriodService,
    AdjustmentService,
    DataItemService,
    MergeService,
)
from fin_statement_model.core.graph.manipulator import GraphManipulator
from fin_statement_model.core.graph.traverser import GraphTraverser
from fin_statement_model.core.adjustments.models import (
    AdjustmentFilterInput,
    AdjustmentType,
    AdjustmentTag,
)
from fin_statement_model.core.adjustments.manager import AdjustmentManager
from fin_statement_model.core.graph.services import GraphIntrospector
from fin_statement_model.core.graph.services import NodeRegistryService
from fin_statement_model.core.time.period import Period  # local import


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

    def __init__(
        self,
        periods: Optional[list[str]] = None,
        *,
        # Dependency-injection hooks – allow callers to override services in tests
        calc_engine_cls: type["CalculationEngine"] = CalculationEngine,
        period_service_cls: type["PeriodService"] = PeriodService,
        adjustment_service_cls: type["AdjustmentService"] = AdjustmentService,
        data_item_service_cls: type["DataItemService"] | None = None,
        merge_service_cls: type["MergeService"] | None = None,
        introspector_cls: type["GraphIntrospector"] | None = None,
        registry_service_cls: type["NodeRegistryService"] | None = None,
    ):
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

        # ------------------------------------------------------------------
        # Registry service --------------------------------------------------
        # ------------------------------------------------------------------
        if registry_service_cls is None:
            registry_service_cls = NodeRegistryService

        self._registry_service = registry_service_cls(
            nodes_dict=self._nodes,
            traverser_provider=lambda: self.traverser,
            add_periods=self.add_periods,
        )

        # ------------------------------------------------------------------
        # Service layer instantiation (new)
        # ------------------------------------------------------------------
        # Period management – share underlying list reference so legacy code remains valid
        self._period_service = period_service_cls(self._periods)

        # Calculation engine – receives resolver & cache reference
        self._calc_engine = calc_engine_cls(
            node_resolver=cast(Callable[[str], Node], self.get_node),
            period_provider=lambda: self._period_service.periods,
            node_names_provider=lambda: list(self._nodes.keys()),
            cache=self._cache,
            node_factory=self._node_factory,
            nodes_dict=self._nodes,
            add_node_with_validation=self._registry_service.add_node_with_validation,
            resolve_input_nodes=self._registry_service.resolve_input_nodes,
            add_periods=self.add_periods,
        )

        # Adjustment manager and service -----------------------------------
        self.adjustment_manager = AdjustmentManager()
        self._adjustment_service = adjustment_service_cls(
            manager=self.adjustment_manager
        )

        # ------------------------------------------------------------------
        # Data-item helper service -----------------------------------------
        # ------------------------------------------------------------------
        if data_item_service_cls is None:
            data_item_service_cls = DataItemService

        self._data_item_service = data_item_service_cls(
            node_factory=self._node_factory,
            add_node_with_validation=self._registry_service.add_node_with_validation,
            add_periods=self.add_periods,
            node_getter=self.get_node,
            node_names_provider=lambda: list(self._nodes.keys()),
        )

        # ------------------------------------------------------------------
        # Merge service ----------------------------------------------------
        # ------------------------------------------------------------------
        if merge_service_cls is None:
            merge_service_cls = MergeService

        self._merge_service = merge_service_cls(
            add_periods=self.add_periods,
            periods_provider=lambda: self.periods,
            node_getter=self.get_node,
            add_node=self.add_node,
            nodes_provider=lambda: self._nodes,
        )

        # ------------------------------------------------------------------
        # Introspector service ---------------------------------------------
        # ------------------------------------------------------------------
        if introspector_cls is None:
            introspector_cls = GraphIntrospector

        self._introspector = introspector_cls(
            nodes_provider=lambda: self._nodes,
            periods_provider=lambda: self.periods,
            traverser_provider=lambda: self.traverser,
        )

        # Handle initial periods via service
        if periods:
            if not isinstance(periods, list):
                raise TypeError("Initial periods must be a list")
            self._period_service.add_periods(periods)

        self.manipulator = GraphManipulator(self)
        self.traverser = GraphTraverser(self)

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
    def periods(self) -> list[str]:  # noqa: D401
        """Return the **string identifiers** of all periods in chronological order."""
        return self._period_service.periods

    def add_periods(self, periods: Iterable[Union[str, Period]]) -> None:
        """Add additional periods (raw strings or :class:`Period` instances)."""
        if isinstance(periods, str):  # Preserve legacy validation semantics
            raise TypeError(
                "Periods must be provided as a list/iterable, not a string."
            )

        period_strings: list[str] = [
            str(p) if isinstance(p, Period) else p for p in periods
        ]
        self._period_service.add_periods(period_strings)

    def add_calculation(
        self,
        name: str,
        input_names: list[str],
        operation_type: str,
        formula_variable_names: Optional[list[str]] = None,
        **calculation_kwargs: Any,
    ) -> Node:  # noqa: D401
        """Create and register a calculation node via the injected :class:`CalculationEngine`."""
        return self._calc_engine.add_calculation(
            name,
            input_names,
            operation_type,
            formula_variable_names=formula_variable_names,
            **calculation_kwargs,
        )

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
        return self._calc_engine.add_metric(
            metric_name,
            node_name,
            input_node_map=input_node_map,
        )

    def add_custom_calculation(
        self,
        name: str,
        calculation_func: Callable[..., float],
        inputs: Optional[list[str]] = None,
        description: str = "",
    ) -> Node:
        """Delegate to ``CalculationEngine``."""
        return self._calc_engine.add_custom_calculation(
            name,
            calculation_func,
            inputs,
            description,
        )

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
        return self._calc_engine.ensure_signed_nodes(base_node_ids, suffix=suffix)

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
        return self._calc_engine.change_calculation_method(
            node_name,
            new_method_key,
            **kwargs,
        )

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
        return self._calc_engine.get_metric(metric_id)

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
        return self._calc_engine.get_available_metrics()

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
        return self._calc_engine.get_metric_info(metric_id)

    def get_adjusted_value(
        self,
        node_name: str,
        period: str,
        filter_input: "AdjustmentFilterInput" = None,
        *,
        return_flag: bool = False,
    ) -> float | tuple[float, bool]:
        """Return node value adjusted for discretionary entries (thin delegate)."""

        # Base calculation remains in Graph to avoid circular dependency.
        base_value = self.calculate(node_name, period)

        adjustments = self._adjustment_service.get_filtered_adjustments(
            node_name, period, filter_input
        )

        adjusted_value, was_adjusted = self._adjustment_service.apply_adjustments(
            base_value, adjustments
        )

        return (adjusted_value, was_adjusted) if return_flag else adjusted_value

    def calculate(self, node_name: str, period: Union[str, Period]) -> float:
        """Compute ``node_name`` for *period* via the :class:`CalculationEngine`."""
        return self._calc_engine.calculate(node_name, period)

    def recalculate_all(
        self, periods: Optional[Iterable[Union[str, Period]]] = None
    ) -> None:
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
        # Delegate to engine after validating *periods* parameter
        self._calc_engine.recalc_all(
            list(periods) if isinstance(periods, Iterable) else periods
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
        # Clear central calculation cache via engine
        self.clear_calculation_cache()
        logger.debug("Cleared central calculation cache via CalculationEngine.")

    def clear_calculation_cache(self) -> None:
        """Clear the graph's internal calculation cache.

        Returns:
            None

        Examples:
            >>> graph.clear_calculation_cache()
        """
        self._calc_engine.clear_all()
        logger.debug("Cleared graph calculation cache via CalculationEngine.")

    def clear(self) -> None:
        """Reset the graph by clearing nodes, periods, adjustments, and caches."""
        # Reset node registry
        self._nodes = {}
        # Clear periods via PeriodService (shared list)
        self._period_service._periods.clear()
        # Reset central cache dict and ensure engine sees the change
        self._cache.clear()
        # Clear adjustments
        self.adjustment_manager.clear_all()

        logger.info("Graph cleared: nodes, periods, adjustments, and caches reset.")

    def add_financial_statement_item(
        self, name: str, values: dict[str, float]
    ) -> FinancialStatementItemNode:  # noqa: D401
        """Thin façade delegating to ``DataItemService``."""
        return self._data_item_service.add_financial_statement_item(name, values)

    def update_financial_statement_item(
        self, name: str, values: dict[str, float], replace_existing: bool = False
    ) -> FinancialStatementItemNode:  # noqa: D401
        """Thin façade delegating to ``DataItemService``."""
        return self._data_item_service.update_financial_statement_item(
            name, values, replace_existing=replace_existing
        )

    def get_financial_statement_items(
        self,
    ) -> list[FinancialStatementItemNode]:  # noqa: D401
        """Thin façade delegating to ``DataItemService``."""
        return self._data_item_service.get_financial_statement_items()

    def __repr__(self) -> str:
        """Provide a concise, developer-friendly string representation of the graph.

        Summarize total nodes, FS items, calculations, dependencies, and periods.

        Returns:
            A string summarizing the graph's structure and contents.

        Examples:
            >>> logger.info(repr(graph))
        """
        return self._introspector.make_repr()

    def has_cycle(self, source_node: Node, target_node: Node) -> bool:
        """Return ``True`` if an edge from *target_node* to *source_node* forms a cycle."""
        return self._introspector.has_cycle(source_node, target_node)

    # ------------------------------------------------------------------
    # Thin registry/manipulator façades needed by external services
    # ------------------------------------------------------------------

    def add_node(self, node: Node) -> None:  # noqa: D401
        """Add a node via ``NodeRegistryService`` (kept for backward-compat helpers)."""
        self._registry_service.add_node_with_validation(node)

    def get_node(self, node_name: str) -> Optional[Node]:
        """Return the node with the given name, if it exists in the graph.

        Args:
            node_name: Name of the node to retrieve.

        Returns:
            The Node corresponding to `node_name` if it exists in the graph, or None.

        Examples:
            >>> graph = Graph()
            >>> item_node = graph.add_financial_statement_item("Revenue", {"2023": 100})
            >>> logger.info(graph.get_node("Revenue") == item_node)
        """
        return self._nodes.get(node_name)

    def has_node(self, node_id: str) -> bool:  # noqa: D401
        """Return True if a node with *node_id* is present in the graph."""
        return node_id in self._nodes

    # ---------------- Adjustment helpers requested by external packages ----

    def list_all_adjustments(self) -> list[Any]:  # noqa: D401
        """Return a list of every adjustment managed by the graph."""
        return self._adjustment_service.list_all_adjustments()

    def was_adjusted(
        self,
        node_name: str,
        period: str,
        filter_input: "AdjustmentFilterInput" = None,
    ) -> bool:  # noqa: D401
        """Return True if any adjustments match the criteria for the given node/period."""
        return self._adjustment_service.was_adjusted(node_name, period, filter_input)

    # ------------------------------------------------------------------
    # Traversal façade wrappers (used by tests and external modules)
    # ------------------------------------------------------------------

    def topological_sort(self) -> list[str]:  # noqa: D401
        return self.traverser.topological_sort()

    def get_calculation_nodes(self) -> list[str]:  # noqa: D401
        return self.traverser.get_calculation_nodes()

    def get_dependencies(self, node_id: str) -> list[str]:  # noqa: D401
        return self.traverser.get_dependencies(node_id)

    def get_dependency_graph(self) -> dict[str, list[str]]:  # noqa: D401
        return self.traverser.get_dependency_graph()

    def detect_cycles(self) -> list[list[str]]:  # noqa: D401
        return self.traverser.detect_cycles()

    def breadth_first_search(
        self, start_node: str, direction: str = "successors"
    ) -> list[list[str]]:  # noqa: D401
        return self.traverser.breadth_first_search(start_node, direction)

    def get_direct_successors(self, node_id: str) -> list[str]:  # noqa: D401
        return self.traverser.get_direct_successors(node_id)

    def get_direct_predecessors(self, node_id: str) -> list[str]:  # noqa: D401
        return self.traverser.get_direct_predecessors(node_id)

    # ------------------------------------------------------------------
    # Adjustment API façade ---------------------------------------------
    # ------------------------------------------------------------------

    def add_adjustment(
        self,
        node_name: str,
        period: str,
        value: float,
        reason: str,
        adj_type: "AdjustmentType" = AdjustmentType.ADDITIVE,
        scale: float = 1.0,
        priority: int = 0,
        tags: Optional[set["AdjustmentTag"]] = None,
        scenario: Optional[str] = None,
        user: Optional[str] = None,
        *,
        adj_id: Optional["UUID"] = None,
    ) -> "UUID":  # noqa: D401
        return self._adjustment_service.add_adjustment(
            node_name,
            period,
            value,
            reason,
            adj_type,
            scale,
            priority,
            tags,
            scenario,
            user,
            adj_id=adj_id,
        )

    def remove_adjustment(self, adj_id: "UUID") -> bool:  # noqa: D401
        return self._adjustment_service.remove_adjustment(adj_id)

    # ------------------------------------------------------------------
    # Manipulator wrappers ----------------------------------------------
    # ------------------------------------------------------------------

    def remove_node(self, node_name: str) -> None:  # noqa: D401
        self.manipulator.remove_node(node_name)

    def replace_node(self, node_name: str, new_node: Node) -> None:  # noqa: D401
        self.manipulator.replace_node(node_name, new_node)

    def set_value(self, node_id: str, period: str, value: float) -> None:  # noqa: D401
        self.manipulator.set_value(node_id, period, value)

    # ------------------------------------------------------------------
    # Merge façade ------------------------------------------------------

    def merge_from(self, other_graph: "Graph") -> None:  # noqa: D401
        """Merge nodes and periods from *other_graph* into this graph."""
        if not isinstance(other_graph, Graph):
            raise TypeError("Can only merge from another Graph instance.")
        self._merge_service.merge_from(other_graph)

    def validate(self) -> list[str]:  # noqa: D401
        """Run structural validation checks and return list of problems (empty if none)."""
        return self.traverser.validate()
