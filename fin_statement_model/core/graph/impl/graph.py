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

from fin_statement_model.core.graph.domain import Adjustment, Period
from fin_statement_model.core.graph.engine import (
    CalculationEngine,
    GraphBuilder,
    GraphState,
)
from fin_statement_model.core.graph.services.adjustments import AdjustmentService
from fin_statement_model.core.graph.services.metrics import MetricService
from fin_statement_model.core.graph.services.periods import PeriodService

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
        input_names: list[str],
        operation_type: str,
        *,
        formula: str | None = None,
        formula_variable_names: list[str] | None = None,
    ) -> object:
        """Convenience wrapper for constructing a calculation node.

        Args:
            name: Code for the *new* node.
            input_names: Ordered list of dependency codes.
            operation_type: One of ``"addition"``, ``"subtraction"``,
                ``"multiplication"``, ``"division"`` or ``"formula"``.
            formula: Raw expression string required only when
                *operation_type* is ``"formula"``.
            formula_variable_names: Optional placeholders (e.g.
                ``["input_0", "input_1"]``) that will be replaced
                positionally by *input_names* when *operation_type* equals
                ``"formula"``.
        """

        if not isinstance(input_names, (list, tuple, set)):
            raise TypeError("input_names must be a list of node codes")

        # 1. Build Python expression --------------------------------------
        op_type = operation_type.lower()
        expr: str
        if op_type in {"addition", "add"}:
            expr = " + ".join(input_names)
        elif op_type in {"subtraction", "subtract", "minus"}:
            if len(input_names) != 2:
                raise ValueError("subtraction requires exactly two inputs in tests")
            expr = f"{input_names[0]} - {input_names[1]}"
        elif op_type in {"multiplication", "multiply"}:
            expr = " * ".join(input_names)
        elif op_type in {"division", "divide"}:
            if len(input_names) != 2:
                raise ValueError("division requires exactly two inputs in tests")
            expr = f"{input_names[0]} / {input_names[1]}"
        elif op_type == "formula":
            if formula is None:
                raise ValueError("formula operation_type requires a formula string")
            expr = formula
            if formula_variable_names is not None:
                for placeholder, real in zip(
                    formula_variable_names, input_names, strict=False
                ):
                    expr = expr.replace(placeholder, real)
        else:
            raise ValueError(f"Unsupported operation_type: {operation_type}")

        # 2. Delegate to generic builder helper ---------------------------
        self.add_item(name, formula=expr)
        return self.get_node(name)

    # ------------------------------------------------------------------
    def change_calculation_method(self, code: str, new_operation_type: str) -> None:
        raise AttributeError(
            "change_calculation_method has been removed; rebuild the node with add_item/add_calculation instead."
        )

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

    def ensure_signed_nodes(self, codes: list[str]) -> None:
        raise AttributeError(
            "ensure_signed_nodes has been removed; create negative formula nodes directly."
        )

    def merge_from(self, other: object) -> None:
        raise AttributeError(
            "merge_from has been removed; use add_item/add_calculation instead."
        )

    def topological_sort(self) -> list[str]:
        raise AttributeError(
            "topological_sort has been removed; use add_item/add_calculation instead."
        )

    def detect_cycles(self) -> list[list[str]]:
        raise AttributeError(
            "detect_cycles has been removed; use add_item/add_calculation instead."
        )

    def validate(self) -> list[str]:
        raise AttributeError(
            "validate has been removed; use add_item/add_calculation instead."
        )

    def get_dependencies(self, node: str) -> list[str]:
        raise AttributeError(
            "get_dependencies has been removed; use add_item/add_calculation instead."
        )

    def get_direct_successors(self, node: str) -> list[str]:
        raise AttributeError(
            "get_direct_successors has been removed; use add_item/add_calculation instead."
        )

    def get_direct_predecessors(self, node: str) -> list[str]:
        raise AttributeError(
            "get_direct_predecessors has been removed; use add_item/add_calculation instead."
        )

    def breadth_first_search(
        self, start_node: str, *, direction: str = "successors"
    ) -> list[list[str]]:
        raise AttributeError(
            "breadth_first_search has been removed; use add_item/add_calculation instead."
        )
