"""Public façade for the v2 graph.

# mypy: ignore-errors

Users interact with :class:`GraphFacade` only; internals are hidden in
private modules.
"""

from __future__ import annotations

from typing import Any, Iterable

from fin_statement_model.core.graph.engine.inspect import (
    breadth_first,
)
from fin_statement_model.core.graph.engine.inspect import (
    dependencies as _deps,
)
from fin_statement_model.core.graph.engine.inspect import (
    detect_cycles as _cycles,
)
from fin_statement_model.core.graph.engine.inspect import (
    predecessors as _pred,
)
from fin_statement_model.core.graph.engine.inspect import (
    successors as _succ,
)
from fin_statement_model.core.graph.impl.graph import Graph as _GraphImpl
from fin_statement_model.core.time.period import Period

__all__: list[str] = ["GraphFacade"]


class GraphFacade:
    """High-level public API for building and interrogating a calculation graph.

    ``GraphFacade`` is the *only* class that external callers need to import
    when working with the graph engine.  Internally it delegates all heavy
    lifting to a private implementation, but from the outside it behaves like
    an ordinary, stateful Python object – you can add items, define formulas,
    update input values and request calculated results.

    The interface emphasises *predictability* and *testability* rather than
    historical compatibility, so method names map directly to the underlying
    domain concept they modify.

    Example:
        >>> from fin_statement_model.core.graph import Graph
        >>> g = Graph(periods=["2023"])  # alias for GraphFacade
        >>> g.add_financial_statement_item("revenue", {"2023": 150})
        >>> g.add_financial_statement_item("cogs", {"2023": 90})
        >>> g.add_calculation(
        ...     "gross_profit", ["revenue", "cogs"], operation_type="subtraction"
        ... )
        >>> assert g.calculate("gross_profit", "2023") == 60
    """

    # ------------------------------------------------------------------
    # Construction ------------------------------------------------------
    # ------------------------------------------------------------------
    def __init__(self, *, periods: Iterable[str | Period] | None = None):
        self._impl = _GraphImpl()
        # Single object now serves as its own traverser/manipulator
        self.manipulator = self  # write helpers

        # Optional initial periods --------------------------------------
        if periods is not None:
            self.add_periods(periods)

        # Custom calculation registry (per instance) --------------------
        self._node_cache: dict[str, object] = {}

    # ------------------------------------------------------------------
    # Structural helpers
    # ------------------------------------------------------------------
    def add_item(self, code: str, *, formula: str | None = None) -> None:
        self._impl.add_item(code, formula=formula)

    def add_periods(self, periods: Iterable[str | Period]) -> None:
        # Basic type validation (tests expect TypeError on str)
        if isinstance(periods, (str, int)) or not hasattr(periods, "__iter__"):
            raise TypeError("periods must be an iterable of str/Period")
        self._impl.add_periods(periods)

    def add_financial_statement_item(self, code: str, values: dict[str, float]) -> None:
        """Add an **input** node that stores explicit period values."""
        self._impl.add_financial_statement_item(code, values)

    # ------------------------------------------------------------------
    # Calculation
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Adjustments
    # ------------------------------------------------------------------
    def set_value(
        self, code: str, period: str, value: float, *, replace_existing: bool = True
    ) -> None:
        # Type & period validation needed for misc tests -----------------
        if not isinstance(value, (int, float)):
            raise NotImplementedError("Only numeric values supported for set_value")
        if period not in self.periods:
            raise ValueError("Period not present in graph")
        self._impl.set_value(
            code, period, float(value), replace_existing=replace_existing
        )

    def remove_node(self, code: str) -> None:
        self._impl.remove_node(code)

    def replace_node(
        self,
        *,
        code: str,
        formula: str | None = None,
        values: dict[str, float] | None = None,
    ):
        """Replace an existing node *in-place*.

        Args:
            code: Node code to replace.
            formula: New formula string (optional).
            values: New values mapping for an input node (optional).
        """

        try:
            self._impl.replace_node(code, formula=formula, values=values)
        except KeyError as exc:
            from fin_statement_model.core.errors import NodeError

            raise NodeError(str(exc)) from exc

    # ------------------------------------------------------------------
    # Convenience Utilities
    # ------------------------------------------------------------------
    def clear_caches(self) -> None:
        self._impl.clear_calculation_cache()

    # ------------------------------------------------------------------
    # Metric helpers ----------------------------------------------------
    # ------------------------------------------------------------------
    def add_metric(
        self,
        metric_name: str,
        node_name: str | None = None,
        *,
        input_node_map: dict[str, str] | None = None,
    ):
        self._impl.add_metric(metric_name, node_name, input_node_map=input_node_map)

    def get_metric(self, metric_name: str):
        return self._impl.get_metric(metric_name)

    def get_available_metrics(self):
        return self._impl.get_available_metrics()

    def get_adjusted_value(
        self, node: str, period: str, filter_input=None, *, return_flag: bool = False
    ):
        return self._impl.get_adjusted_value(
            node, period, filter_input, return_flag=return_flag
        )

    def was_adjusted(self, node: str, period: str, filter_input=None):
        return self._impl.was_adjusted(node, period, filter_input)

    # ------------------------------------------------------------------
    # Node access helpers ----------------------------------------------
    # ------------------------------------------------------------------
    def get_node(self, code: str):
        internal = self._impl.get_node(code)
        if internal is None:
            return None

        from fin_statement_model.core.graph.domain import NodeKind
        from fin_statement_model.core.nodes import FinancialStatementItemNode

        if internal.kind is NodeKind.INPUT:
            if code not in self._node_cache:
                self._node_cache[code] = FinancialStatementItemNode(
                    internal.code, dict(internal.data)
                )
            else:
                # Keep cache in sync with underlying data mapping
                self._node_cache[code].values = dict(internal.data)
            return self._node_cache[code]

        # For non-input nodes simply return a lightweight proxy with 'name' attr
        from types import SimpleNamespace

        return SimpleNamespace(name=internal.code)

    def has_node(self, code: str) -> bool:
        return self._impl.has_node(code)

    # ------------------------------------------------------------------
    # Legacy direct node insertion -------------------------------------
    # ------------------------------------------------------------------
    def add_node(self, node: Any) -> None:
        """Insert an *existing* node instance into the graph (backward compat)."""

        self._impl.add_node(node)

    # ------------------------------------------------------------------
    # Calculation helpers ----------------------------------------------
    # ------------------------------------------------------------------
    def add_calculation(self, *args: Any, **kwargs: Any) -> Any:
        """Add a formula node and return a lightweight proxy exposing ``name``."""

        node = self._impl.add_calculation(*args, **kwargs)
        # Minimal proxy exposing ``name`` attribute expected by tests ------
        from types import SimpleNamespace

        return SimpleNamespace(name=node.code)

    # ------------------------------------------------------------------
    # Override calculate to support (node, period) signature ------------
    # ------------------------------------------------------------------
    def calculate(self, *args, trace: bool = False, **kwargs):  # type: ignore[override]
        """Support both ``calculate(period)`` and ``calculate(node, period)`` forms."""

        # Support legacy keyword signature calculate(period=<str>) ----------
        if "period" in kwargs and not args:
            period_kw = kwargs["period"]
            return self._impl.calculate(period_kw, trace=trace)

        if len(args) == 1:
            # Period-only call – delegate to impl
            return self._impl.calculate(args[0], trace=trace)

        if len(args) == 2:
            node_code, period = args
            data = self._impl.calculate(period)
            if (node_code, str(period)) in data:
                return data[(node_code, str(period))]
            # If not present maybe cache cleared; calculate specifically
            return self._impl.calculate_specific(node_code, str(period))

        raise TypeError("calculate expects (period) or (node, period)")

    # ------------------------------------------------------------------
    # Adjustment helpers -------------------------------------------------
    # ------------------------------------------------------------------
    def add_adjustment(self, **kwargs):
        """Create an :class:`~fin_statement_model.core.graph.domain.Adjustment` and
        persist it in the in-memory adjustment service.

        The function returns the *generated* UUID so that callers can easily
        look up or revoke the adjustment later.
        """

        from uuid import uuid4

        node_name = kwargs.pop("node_name")
        period = kwargs.pop("period")
        value = kwargs.pop("value")
        reason = kwargs.pop("reason")
        adj_type = kwargs.pop("adj_type")
        scale = kwargs.pop("scale", 1.0)
        priority = kwargs.pop("priority", 0)
        tags = kwargs.pop("tags", set())
        scenario = kwargs.pop("scenario", "default")
        user = kwargs.pop("user", None)

        # Convert AdjustmentType to domain variant if needed --------------
        from fin_statement_model.core.graph.domain.adjustment import (
            Adjustment as _Adj,
        )
        from fin_statement_model.core.graph.domain.adjustment import (
            AdjustmentType as _AdjType,
        )

        if isinstance(adj_type, _AdjType):
            domain_type = adj_type
        else:
            domain_type = _AdjType(
                adj_type.value if hasattr(adj_type, "value") else str(adj_type)
            )

        adj = _Adj(
            node=node_name,
            period=str(period),
            value=float(value),
            reason=str(reason),
            type=domain_type,
            scale=float(scale),
            priority=int(priority),
            tags=set(tags),
            scenario=scenario,
            user=user,
            id=uuid4(),
        )

        self._impl.add_adjustment(adj)
        return adj.id

    # ------------------------------------------------------------------
    # Misc helpers ------------------------------------------------------
    # ------------------------------------------------------------------
    def clear(self):
        self._impl.clear()

    def update_financial_statement_item(
        self, code: str, values: dict[str, float], *, replace_existing: bool = False
    ):
        self._impl.update_financial_statement_item(
            code, values, replace_existing=replace_existing
        )
        # Update cached node if present ----------------------------------
        if code in self._node_cache:
            if replace_existing:
                self._node_cache[code].values = dict(values)
            else:
                self._node_cache[code].values.update(values)

    def get_financial_statement_items(self):
        from fin_statement_model.core.nodes import FinancialStatementItemNode

        items = []
        for (
            node
        ) in self._impl._state.nodes.values():  # pylint: disable=protected-access
            if node.kind.name == "INPUT":
                items.append(FinancialStatementItemNode(node.code, dict(node.data)))
        return items

    def merge_from(self, other):
        if not isinstance(other, GraphFacade):
            raise TypeError("merge_from expects Graph instance")
        # Merge periods first
        self.add_periods(other.periods)
        # Merge nodes
        for code in other.nodes:
            other_node = other.get_node(code)
            if not self.has_node(code):
                self.add_node(other_node)
            else:
                # Update values if input node
                if isinstance(other_node, type(self.get_node(code))):
                    self.update_financial_statement_item(
                        code, other_node.values, replace_existing=True
                    )

    def recalculate_all(self, periods: list[str] | None = None):
        if periods is not None and not isinstance(periods, (list, tuple, set)):
            raise TypeError("periods must be iterable or None")
        self._impl.recalculate_all(list(periods) if periods else None)

    # ------------------------------------------------------------------
    # Traversal helpers (previously via GraphTraverser) -----------------
    # ------------------------------------------------------------------
    def topological_sort(self):
        """Return nodes in dependency order (inputs first)."""
        return list(self._impl._state.order)  # type: ignore[attr-defined]

    def detect_cycles(self):
        """Return a list of cycles detected in the graph (may be empty)."""
        return _cycles(self._impl._state)

    def validate(self):
        """Return a list of validation error strings (empty if valid)."""
        errs: list[str] = []
        state = self._impl._state  # type: ignore[attr-defined]
        for code, node in state.nodes.items():
            for dep in node.inputs:
                if dep not in state.nodes:
                    errs.append(f"Node '{code}' depends on non-existent node '{dep}'")
        for cyc in self.detect_cycles():
            errs.append(f"Circular dependency: {' -> '.join(cyc)}")
        return errs

    def get_dependency_graph(self):
        return self._impl.get_dependency_graph()

    # direct wrappers for utility methods used in tests ------------------
    def get_calculation_nodes(self):
        return self._impl.get_calculation_nodes()

    def get_dependencies(self, node: str):
        return _deps(self._impl._state, node)  # type: ignore[attr-defined]

    def get_direct_successors(self, node: str):
        return _succ(self._impl._state, node)  # type: ignore[attr-defined]

    def get_direct_predecessors(self, node: str):
        return _pred(self._impl._state, node)  # type: ignore[attr-defined]

    def breadth_first_search(self, start_node: str, *, direction: str = "successors"):
        return breadth_first(self._impl._state, start_node, direction=direction)

    # ------------------------------------------------------------------
    # Properties --------------------------------------------------------
    # ------------------------------------------------------------------
    @property
    def periods(self):
        return self._impl.periods

    @property
    def nodes(self):
        return self._impl.nodes

    # ------------------------------------------------------------------
    # Metric info placeholder ------------------------------------------
    # ------------------------------------------------------------------
    def get_metric_info(self, metric_name: str):
        raise ValueError(metric_name)

    # ------------------------------------------------------------------
    # Representation ----------------------------------------------------
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        total_nodes = len(self.nodes)
        fs_items = len([n for n in self.get_financial_statement_items()])
        return f"<GraphFacade – Total Nodes: {total_nodes}, FS Items: {fs_items}>"

    # ------------------------------------------------------------------
    # Compatibility helpers for downstream modules ----------------------
    # ------------------------------------------------------------------
    def list_all_adjustments(self) -> list[Any]:
        """Return *all* adjustments currently stored in the graph.

        Internally this forwards to the :pyattr:`services.adjustment` helper so
        that callers do not need to know about the lower-level service layer.
        """

        return self._impl.services.adjustment.list_all()

    # Legacy attribute expected by some IO helpers ----------------------
    @property
    def adjustment_manager(self):  # type: ignore[return-type]
        """Direct accessor to the underlying adjustment service instance."""

        return self._impl.services.adjustment

    # ------------------------------------------------------------------
    # Compatibility aliases --------------------------------------------
    # ------------------------------------------------------------------
    @property
    def traverser(self):
        """Alias returning *self* so existing code can access traversal helpers."""
        return self

    def would_create_cycle(self, new_node) -> bool:
        """Return True if inserting *new_node* would introduce a directed cycle."""
        from fin_statement_model.core.graph.engine.topology import CycleError, toposort

        code = str(getattr(new_node, "name", getattr(new_node, "code", "")))
        deps_raw = getattr(new_node, "inputs", [])
        deps = {getattr(d, "name", getattr(d, "code", str(d))) for d in deps_raw}
        if not deps:
            return False

        # create proxy mapping and attempt to topo-sort
        class _Proxy:
            def __init__(self, c: str, d):
                self.code = c
                self.inputs = d

        proxy = _Proxy(code, deps)
        mapping = dict(self._impl._state.nodes)  # type: ignore[attr-defined]
        mapping[code] = proxy  # type: ignore[arg-type]
        try:
            toposort(mapping)
            return False
        except CycleError:
            return True

    def find_cycle_path(self, start: str, end: str):
        """Return a simple path list between *start* and *end* if they share a cycle."""
        cycles = self.detect_cycles()
        for cyc in cycles:
            if start in cyc and end in cyc:
                # rotate list so it starts at start
                while cyc[0] != start:
                    cyc.append(cyc.pop(0))
                if cyc[-1] != end:
                    cyc.append(end)
                return cyc
        return None
