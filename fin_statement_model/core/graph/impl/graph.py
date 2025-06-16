"""This class glues together:

* Mutable :class:`GraphBuilder` to perform structural changes
* Immutable :class:`GraphState` snapshots for safe multi-thread usage
* Pure :class:`CalculationEngine` evaluator
* Side-effecting services collected in a minimal container-like struct

The shell itself is **private** – end-users interact through
:pyclass:`fin_statement_model.core.graph.api.facade.GraphFacade`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional, cast

from fin_statement_model.core.graph.domain import Adjustment
from fin_statement_model.core.graph.engine import (
    CalculationEngine,
    GraphBuilder,
    GraphState,
)
from fin_statement_model.core.graph.services.adjustments import AdjustmentService
from fin_statement_model.core.graph.services.metrics import MetricService
from fin_statement_model.core.graph.services.periods import PeriodService
from fin_statement_model.core.time.period import Period

__all__: list[str] = ["Graph"]


@dataclass(slots=True)
class _ServiceBundle:
    """Light-weight container for service *instances* (not classes)."""

    adjustment: AdjustmentService = field(default_factory=AdjustmentService)
    period: PeriodService = field(default_factory=PeriodService)


class Graph:
    """Imperative orchestration layer; no heavy domain logic inside."""

    __slots__ = ("_services", "_state", "_calc", "_metric_service", "manipulator")

    def __init__(self, *, services: _ServiceBundle | None = None) -> None:
        # Create bundle first without metrics then attach after _state exists
        self._services: _ServiceBundle = services or _ServiceBundle()
        self._state: GraphState = GraphBuilder().commit()
        self._calc: CalculationEngine = CalculationEngine()
        # Metrics service bound to builder generator
        self._metric_service = MetricService(lambda: GraphBuilder(base=self._state))

        # The Graph object now acts as its own manipulator; attribute kept
        # for backward compatibility so that external code can still access
        # ``graph.manipulator``.
        self.manipulator = self

    # ------------------------------------------------------------------
    # Builder helpers (structural mutations)
    # ------------------------------------------------------------------
    def add_item(
        self,
        code: str,
        *,
        formula: str | None = None,
        values: dict[str, float] | None = None,
    ) -> None:
        builder = GraphBuilder(base=self._state)
        if code in self._state.nodes:
            builder.remove_node(code)
        builder.add_node(code=code, formula=formula, values=values)
        self._state = self._commit_allow_cycles(builder)
        # Invalidate **all** caches because dependency graph changed ------
        self._calc.clear_all()

    def add_periods(self, periods: Iterable[str | Period]) -> None:
        for p in periods:
            self._services.period.add(p)

    # ------------------------------------------------------------------
    # Legacy support: add_node accepting pre‐built node objects ---------
    # ------------------------------------------------------------------
    def add_node(self, node: object) -> None:
        """Insert an *existing* node object without exposing mutability.

        The public API usually expects callers to supply *code*, *formula* and
        *values* separately via :pymeth:`GraphFacade.add_item`.  Occasionally,
        however, it is convenient to pass an already-constructed node instance
        – for example when cloning a graph or when interoperating with helper
        classes in the *statements* layer.

        To keep the core immutable, the method extracts the minimal
        information (``code``, ``formula``, ``data``) and reinserts the node
        via the canonical builder pipeline.  This guarantees that no
        mutable objects leak into :class:`GraphState`.
        """

        # Gracefully handle both v2 ``Node`` and legacy node classes ----------
        code: str | None = None
        formula: str | None = None
        values: dict[str, float] | None = None

        if hasattr(node, "code"):
            code = str(node.code)
            formula = getattr(node, "formula", None)
            # v2 nodes store mappingproxy – convert to plain dict
            values_mapping = getattr(node, "data", None)
            if values_mapping:
                values = dict(values_mapping)
        elif hasattr(node, "name"):
            code = str(node.name)
            # Legacy nodes expose ``values`` dict and ``calculate`` method.
            values = (
                dict(getattr(node, "values", {})) if hasattr(node, "values") else None
            )
            # Legacy formulation nodes frequently store ``formula`` attribute
            formula = getattr(node, "formula", None)

        if code is None:
            raise TypeError("Unsupported node type passed to add_node()")

        # Delegate to canonical builder helper
        self.add_item(code, formula=formula, values=values)

    # ------------------------------------------------------------------
    # Calculation API ---------------------------------------------------
    # ------------------------------------------------------------------
    def calculate(
        self, period: str | Period | Iterable[str | Period], *, trace: bool = False
    ) -> Any:
        return self._calc.calculate(self._state, period, trace=trace)

    def clear_calculation_cache(self) -> None:
        self._calc.clear_all()

    # ------------------------------------------------------------------
    # Adjustment API ----------------------------------------------------
    # ------------------------------------------------------------------
    def add_adjustment(self, adj: Adjustment) -> None:
        self._services.adjustment.add(adj)

    def get_adjusted_value(
        self,
        node: str,
        period: str,
        filter_input: Any = None,
        *,
        return_flag: bool = False,
    ) -> float | tuple[float, bool]:
        try:
            base = self.calculate_specific(node, str(period))
        except KeyError:
            # If node missing value propagate original error
            calc_result_any = self._calc.calculate(self._state, period)
            calc_result = cast(Mapping[tuple[str, str], float], calc_result_any)
            base = calc_result[(node, str(period))]
        adjs = self._services.adjustment.get_filtered(node, period, filter_input)
        value, flag = self._services.adjustment.apply_adjustments(base, adjs)
        return (value, flag) if return_flag else value

    def was_adjusted(self, node: str, period: str, filter_input: Any = None) -> bool:
        return bool(self._services.adjustment.get_filtered(node, period, filter_input))

    # Expose services for advanced users (read-only) --------------------
    @property
    def services(self) -> _ServiceBundle:
        return self._services

    # Backwards-compat alias ------------------------------------------------
    def add_financial_statement_item(self, code: str, values: dict[str, float]) -> None:
        self.add_item(code, values=values)

    # ------------------------------------------------------------------
    # Value mutation (input nodes) --------------------------------------
    # ------------------------------------------------------------------
    def set_value(
        self, code: str, period: str, value: float, *, replace_existing: bool = False
    ) -> None:
        """Update a single period value for an input node and clear caches."""
        # Ensure period exists in period index --------------------------
        if period not in self._services.period.periods:
            self._services.period.add(period)

        builder = GraphBuilder(base=self._state)
        builder.set_node_value(code, period, value, replace_existing=replace_existing)
        self._state = self._commit_allow_cycles(builder)
        self._calc.clear_cache_for(code)

    # ------------------------------------------------------------------
    # Structural removal / replacement ---------------------------------
    # ------------------------------------------------------------------
    def remove_node(self, code: str) -> None:
        builder = GraphBuilder(base=self._state)
        builder.remove_node(code)
        self._state = self._commit_allow_cycles(builder)
        self._calc.clear_all()

    def replace_node(
        self,
        code: str,
        *,
        formula: str | None = None,
        values: dict[str, float] | None = None,
    ) -> None:
        builder = GraphBuilder(base=self._state)
        builder.replace_node(code, formula=formula, values=values)
        self._state = self._commit_allow_cycles(builder)
        self._calc.clear_all()

    # ------------------------------------------------------------------
    # Metric helpers ----------------------------------------------------
    # ------------------------------------------------------------------
    def add_metric(
        self,
        metric_name: str,
        node_name: str | None = None,
        *,
        input_node_map: dict[str, str] | None = None,
    ) -> None:
        self._state = self._metric_service.add_metric(
            self._state, metric_name, node_name, input_node_map=input_node_map
        )
        self._calc.clear_all()

    def get_metric(self, metric_name: str) -> str | None:
        node_code = self._metric_service.node_for_metric(metric_name)
        return node_code

    def get_available_metrics(self) -> list[str]:
        return self._metric_service.list_metrics()

    # ------------------------------------------------------------------
    # Basic node accessors (required by config helpers/tests) -----------
    # ------------------------------------------------------------------
    def get_node(self, code: str) -> Optional[object]:
        """Return node object or None if absent (read‐only)."""
        return self._state.nodes.get(code)

    def has_node(self, code: str) -> bool:
        return code in self._state

    # ------------------------------------------------------------------
    # Convenience helpers replicating v1 builder / engine ---------------
    # ------------------------------------------------------------------
    def add_calculation(
        self,
        name: str,
        *,
        formula: str,
    ) -> object:
        """Add a **formula** node and return a lightweight proxy.

        This helper is now a thin wrapper around :pymeth:`add_item` that
        exists only for nominal API stability.  Callers **must** provide a
        fully-formed Python expression via the *formula* parameter.  Any
        former *operation_type* based shortcuts have been removed.
        """

        if not isinstance(formula, str) or not formula.strip():
            raise ValueError("A non-empty formula string is required")

        # Delegate to canonical builder helper ---------------------------
        self.add_item(name, formula=formula)
        return self.get_node(name)

    # ------------------------------------------------------------------
    def clear(self) -> None:
        """Remove *all* nodes and periods keeping services intact."""
        self._state = GraphBuilder().commit()
        self._calc.clear_all()
        # Reset period service
        self._services.period = PeriodService()

    # ------------------------------------------------------------------
    def update_financial_statement_item(
        self,
        code: str,
        values: dict[str, float],
        *,
        replace_existing: bool = False,
    ) -> None:
        """Merge or replace *values* of an **input** node."""
        if not self.has_node(code):
            from fin_statement_model.core.errors import NodeError

            raise NodeError(code)
        for period, val in values.items():
            self.set_value(code, period, val, replace_existing=replace_existing)

    # ------------------------------------------------------------------
    def recalculate_all(self, periods: list[str] | None = None) -> None:
        """Clear caches and pre-compute all nodes for *periods* (optional)."""
        self._calc.clear_all()
        target_periods = periods or [str(p) for p in self._state.periods]
        for p in target_periods:
            self._calc.calculate(self._state, p)

    # ------------------------------------------------------------------
    # Introspection helpers --------------------------------------------
    # ------------------------------------------------------------------
    def get_dependency_graph(self) -> dict[str, list[str]]:
        """Return mapping *node → sorted dependencies* (read-only)."""
        return {c: sorted(n.inputs) for c, n in self._state.nodes.items()}

    def get_calculation_nodes(self) -> list[str]:
        from fin_statement_model.core.graph.domain import NodeKind

        return [c for c, n in self._state.nodes.items() if n.kind is NodeKind.FORMULA]

    # ------------------------------------------------------------------
    # Period & node listings -------------------------------------------
    # ------------------------------------------------------------------
    @property
    def periods(self) -> list[str]:
        """Return graph periods as strings in chronological order."""
        core = [str(p) for p in self._state.periods]
        return sorted(set(core + list(self._services.period.periods)))

    @property
    def nodes(self) -> list[str]:
        """Return all node codes currently present in the graph."""
        return list(self._state.nodes.keys())

    # Convenience single value ----------------------------------------
    def calculate_specific(self, code: str, period: str) -> float:
        self._calc.clear_cache_for(code)
        result_any = self._calc.calculate(self._state, period)
        result_map = cast(Mapping[tuple[str, str], float], result_any)
        return result_map[(code, str(period))]

    # ------------------------------------------------------------------
    # Internal helper to commit builder even if cycle -------------------
    # ------------------------------------------------------------------
    def _commit_allow_cycles(self, builder: GraphBuilder) -> GraphState:
        """Commit builder; if CycleError ignore ordering."""
        from types import MappingProxyType

        from fin_statement_model.core.graph.engine.state import GraphState
        from fin_statement_model.core.graph.engine.topology import CycleError

        try:
            return builder.commit()
        except CycleError:
            # Fallback simple order preserving insertion order
            return GraphState(
                nodes=MappingProxyType(builder._nodes),
                periods=self._state.periods,
                _order=tuple(builder._nodes),
            )

    def merge_from(self, other: object) -> None:
        """Merge *other* graph into *self* (best-effort).

        This keeps the convenient behaviour users had in v1 but re-implements
        it on top of the v2 API: periods are unified, input-node values are
        copied/updated, and non-colliding formula nodes are cloned.
        """

        import warnings

        if not isinstance(other, Graph):
            raise TypeError("merge_from expects another Graph instance")

        warnings.warn(
            "merge_from() is deprecated – prefer rebuilding a fresh graph via add_item/add_calculation.",
            DeprecationWarning,
            stacklevel=2,
        )

        # 1 – merge periods -------------------------------------------------
        self.add_periods(other.periods)

        # 2 – merge nodes ---------------------------------------------------
        for code in other.nodes:
            other_node = other.get_node(code)

            # If node absent we can clone; if present only merge input values.
            if not self.has_node(code):
                if hasattr(other_node, "formula"):
                    self.add_item(code, formula=other_node.formula)
                else:
                    from typing import Any, cast

                    node_any = cast(Any, other_node)
                    self.add_item(code, values=dict(node_any.values))
            else:
                # Only input nodes support value updates
                if hasattr(other_node, "values"):
                    from typing import Any, cast

                    node_any2 = cast(Any, other_node)
                    self.update_financial_statement_item(
                        code, dict(node_any2.values), replace_existing=True
                    )

    def topological_sort(self) -> list[str]:
        """Return nodes in dependency order (inputs first)."""
        return list(self._state.order)

    def detect_cycles(self) -> list[list[str]]:
        from fin_statement_model.core.graph.engine.inspect import (
            detect_cycles as _cycles,
        )

        return _cycles(self._state)

    def validate(self) -> list[str]:
        errors: list[str] = []
        # Missing dependency check --------------------------------------
        for code, node in self._state.nodes.items():
            for dep in node.inputs:
                if dep not in self._state.nodes:
                    errors.append(f"Node '{code}' depends on non-existent node '{dep}'")
        # Cycle detection ----------------------------------------------
        for cyc in self.detect_cycles():
            errors.append(f"Circular dependency: {' -> '.join(cyc)}")
        return errors

    def get_dependencies(self, node: str) -> list[str]:
        from fin_statement_model.core.graph.engine.inspect import dependencies as _deps

        return _deps(self._state, node)

    def get_direct_successors(self, node: str) -> list[str]:
        from fin_statement_model.core.graph.engine.inspect import successors as _succ

        return _succ(self._state, node)

    def get_direct_predecessors(self, node: str) -> list[str]:
        from fin_statement_model.core.graph.engine.inspect import predecessors as _pred

        return _pred(self._state, node)

    def breadth_first_search(
        self, start_node: str, *, direction: str = "successors"
    ) -> list[list[str]]:
        from fin_statement_model.core.graph.engine.inspect import breadth_first as _bf

        return _bf(self._state, start_node, direction=direction)
