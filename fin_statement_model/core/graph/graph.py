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
from typing import TYPE_CHECKING, Any, Iterable, Mapping, NoReturn, Optional, cast
from uuid import UUID

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

if TYPE_CHECKING:
    from fin_statement_model.core.graph.inspect import GraphInspector

__all__: list[str] = ["Graph"]


@dataclass(slots=True)
class _ServiceBundle:
    """Light-weight container for service *instances* (not classes)."""

    adjustment: AdjustmentService = field(default_factory=AdjustmentService)
    period: PeriodService = field(default_factory=PeriodService)


class Graph:
    """Imperative orchestration layer; no heavy domain logic inside."""

    __slots__ = (
        "_services",
        "_state",
        "_calc",
        "_metric_service",
        "manipulator",
        "inspect",
        "_node_cache",
    )

    def __init__(
        self,
        *,
        periods: Iterable[str | Period] | None = None,
        services: _ServiceBundle | None = None,
    ) -> None:
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
        # Attach read-only inspector -----------------------------
        from fin_statement_model.core.graph.inspect import (
            GraphInspector,  # local import to avoid cycles
        )

        self.inspect: GraphInspector = GraphInspector(self)

        # Lightweight cache for FinancialStatementItemNode wrappers --------
        self._node_cache: dict[str, Any] = {}

        # Optional initial periods ---------------------------------
        if periods is not None:
            self.add_periods(periods)

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
        # Basic type validation matching legacy behaviour -----------------
        if isinstance(periods, (str, int)) or not hasattr(periods, "__iter__"):
            raise TypeError("periods must be an iterable of str/Period")

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
    def calculate(self, *args: Any, trace: bool = False, **kwargs: Any) -> Any:
        """Calculate values for given *period* or for a specific *(node, period).*

        The method intentionally mirrors the flexible signature that existed
        in the former *GraphFacade* implementation so that downstream code
        and tests can migrate without breaking changes.
        """

        # Legacy keyword form calculate(period=<str>) -------------------
        if "period" in kwargs and not args:
            period_kw = kwargs["period"]
            return self._calc.calculate(self._state, period_kw, trace=trace)

        if len(args) == 1:
            # Period-only call – delegate directly
            return self._calc.calculate(self._state, args[0], trace=trace)

        if len(args) == 2:
            node_code, period = args
            raw = self._calc.calculate(self._state, period, trace=trace)
            data_map = cast(Mapping[tuple[str, str], float], raw)
            key = (str(node_code), str(period))
            if key in data_map:
                return data_map[key]
            # If not present maybe cache cleared; calculate specifically
            return self.calculate_specific(str(node_code), str(period))

        raise TypeError("calculate expects (period) or (node, period)")

    def clear_calculation_cache(self) -> None:
        self._calc.clear_all()

    # Alias expected by tests -------------------------------------------
    clear_caches = clear_calculation_cache

    # ------------------------------------------------------------------
    # Adjustment API ----------------------------------------------------
    # ------------------------------------------------------------------
    def add_adjustment(self, *args: Any, **kwargs: Any) -> UUID:
        """Add an adjustment; accepts either domain object or keyword args.

        The helper keeps full backwards compatibility with the façade-style
        signature so callers can pass high-level keyword arguments instead of
        pre-constructing a :class:`~fin_statement_model.core.graph.domain.Adjustment`.
        """

        if args and isinstance(args[0], Adjustment):
            self._services.adjustment.add(args[0])
            return args[0].id  # pragma: no cover – convenience return

        # Build Adjustment from kwargs ----------------------------------
        required = {"node_name", "period", "value", "reason", "adj_type"}
        if not required.issubset(kwargs):
            missing = required - set(kwargs)
            raise TypeError(f"Missing required adjustment fields: {', '.join(missing)}")

        from uuid import uuid4

        from fin_statement_model.core.graph.domain.adjustment import (
            Adjustment as _Adj,
        )
        from fin_statement_model.core.graph.domain.adjustment import (
            AdjustmentType as _AdjType,
        )

        # Normalize adj_type ------------------------------------------------
        adj_type_kw = kwargs.pop("adj_type")
        if isinstance(adj_type_kw, _AdjType):
            domain_type = adj_type_kw
        else:
            domain_type = _AdjType(getattr(adj_type_kw, "value", str(adj_type_kw)))

        adj = _Adj(
            node=str(kwargs.pop("node_name")),
            period=str(kwargs.pop("period")),
            value=float(kwargs.pop("value")),
            reason=str(kwargs.pop("reason")),
            type=domain_type,
            scale=float(kwargs.pop("scale", 1.0)),
            priority=int(kwargs.pop("priority", 0)),
            tags=set(kwargs.pop("tags", set())),
            scenario=kwargs.pop("scenario", "default"),
            user=kwargs.pop("user", None),
            id=uuid4(),
        )

        self._services.adjustment.add(adj)
        return adj.id

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
        self, code: str, period: str, value: float, *, replace_existing: bool = True
    ) -> None:
        """Update a single period value for an input node and clear caches."""
        # Validate input types ------------------------------------------
        if not isinstance(value, (int, float)):
            raise NotImplementedError("Only numeric values supported for set_value")

        if period not in self._services.period.periods:
            self._services.period.add(period)

        builder = GraphBuilder(base=self._state)
        try:
            builder.set_node_value(
                code, period, value, replace_existing=replace_existing
            )
        except TypeError as exc:
            # Re-wrap builder TypeError as ValueError for tests consistency
            raise ValueError(str(exc)) from exc

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
        try:
            builder.replace_node(code, formula=formula, values=values)
        except KeyError as exc:
            from fin_statement_model.core.errors import NodeError

            raise NodeError(str(exc)) from exc

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

    # Placeholder for API compatibility ----------------------------------
    def get_metric_info(
        self, metric_name: str
    ) -> NoReturn:  # pylint: disable=unused-argument
        raise ValueError(metric_name)

    # ------------------------------------------------------------------
    # Basic node accessors (required by config helpers/tests) -----------
    # ------------------------------------------------------------------
    def get_node(self, code: str) -> Optional[object]:
        """Return a user-friendly node proxy or *None* if absent (read-only)."""

        internal = self._state.nodes.get(code)
        if internal is None:
            return None

        from fin_statement_model.core.graph.domain import NodeKind

        if internal.kind is NodeKind.INPUT:
            from fin_statement_model.core.nodes import FinancialStatementItemNode

            if code not in self._node_cache:
                self._node_cache[code] = FinancialStatementItemNode(
                    internal.code, dict(internal.data)
                )
            else:
                # Keep cached instance in sync with underlying data
                self._node_cache[code].values = dict(internal.data)

            return cast(object, self._node_cache[code])

        # For non-input nodes expose a minimal proxy with 'name' attribute
        from types import SimpleNamespace

        return cast(object, SimpleNamespace(name=internal.code))

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
        # Return lightweight proxy exposing 'name' attribute (tests expect)
        from types import SimpleNamespace

        return SimpleNamespace(name=name)

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

        # Sync cached wrapper if present
        if code in self._node_cache:
            if replace_existing:
                self._node_cache[code].values = dict(values)
            else:
                self._node_cache[code].values.update(values)

    # ------------------------------------------------------------------
    def recalculate_all(self, periods: list[str] | None = None) -> None:
        """Clear caches and pre-compute all nodes for *periods* (optional)."""

        if periods is not None and not isinstance(periods, (list, tuple, set)):
            raise TypeError("periods must be iterable or None")

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

        # Deprecation warning omitted (pre-alpha).

        if not isinstance(other, Graph):
            raise TypeError("merge_from expects Graph instance")

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

    @property
    def traverser(self) -> "GraphInspector":  # pragma: no cover – compatibility shim
        """Deprecated alias returning :pyattr:`inspect` (read-only).

        This exists solely to keep transitional test code working while the
        public API converges on ``graph.inspect``.  It may be removed in a
        future pre-alpha iteration without further notice.
        """

        return self.inspect

    # ------------------------------------------------------------------
    # Representation ----------------------------------------------------
    # ------------------------------------------------------------------
    def __repr__(self) -> str:  # pragma: no cover – simple cosmetic helper
        total_nodes = len(self.nodes)
        from fin_statement_model.core.nodes import FinancialStatementItemNode

        fs_items = len(
            [
                n
                for n in (self.get_node(c) for c in self.nodes)
                if isinstance(n, FinancialStatementItemNode)
            ]
        )
        return f"<Graph – Total Nodes: {total_nodes}, FS Items: {fs_items}>"

    # ------------------------------------------------------------------
    # Helper mimicking facade-level convenience ------------------------
    # ------------------------------------------------------------------
    def get_financial_statement_items(self) -> list[object]:
        """Return *all* input nodes wrapped as FinancialStatementItemNode."""

        from fin_statement_model.core.nodes import FinancialStatementItemNode

        items = []
        for node in self._state.nodes.values():
            if hasattr(node, "kind") and str(node.kind).lower().find("input") != -1:
                items.append(FinancialStatementItemNode(node.code, dict(node.data)))
        from typing import cast as _cast

        return _cast(list[object], items)

    # ------------------------------------------------------------------
    # Adjustment service accessors (used by IO helpers) -----------------
    # ------------------------------------------------------------------

    def list_all_adjustments(self) -> list[Adjustment]:
        """Return *all* adjustments stored in the graph."""

        return self._services.adjustment.list_all()

    @property
    def adjustment_manager(self) -> AdjustmentService:
        """Direct accessor to underlying :class:`AdjustmentService`."""

        return self._services.adjustment
