"""Stateless evaluator for a :class:`GraphState`.

The engine keeps **per-instance** caches for parsed ASTs and computed values but
is otherwise functional and side-effect-free.

# mypy: ignore-errors
"""

from __future__ import annotations

import ast
from time import perf_counter_ns
from typing import Dict, Iterable, Mapping, Tuple

from fin_statement_model.core.graph.domain import NodeKind, Period
from fin_statement_model.core.graph.engine.state import GraphState

__all__: list[str] = ["CalculationEngine"]


class CalculationError(RuntimeError):
    """Raised when evaluation of a node fails."""


class CalculationEngine:
    """Pure evaluator with lightweight memoisation."""

    __slots__ = ("_ast_cache", "_value_cache")

    def __init__(self) -> None:
        self._ast_cache: Dict[str, ast.AST] = {}
        self._value_cache: Dict[Tuple[str, str], float] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def calculate(
        self,
        graph: GraphState,
        period: str | Period | Iterable[str | Period],
        *,
        trace: bool = False,
    ) -> (
        Mapping[str, float] | tuple[Mapping[str, float], Mapping[Tuple[str, str], dict]]
    ):
        """Return node values for *period*(s) in graph order.

        For simplicity this prototype returns a mapping ``node_code → value`` for
        each requested period.  Tracing is captured but currently only records
        evaluation order and dependencies (no timings).
        """

        periods: Tuple[str, ...]
        if isinstance(period, (str, Period)):
            periods = (str(period),)
        else:
            periods = tuple(str(p) for p in period)

        results: Dict[str, float] = {}
        traces: Dict[Tuple[str, str], dict] = {}

        for p in periods:
            for code in graph.order:
                key = (code, p)
                if key in self._value_cache:
                    continue
                start_ns = perf_counter_ns()
                value = self._evaluate_one(code, p, graph)
                duration = perf_counter_ns() - start_ns
                self._value_cache[key] = value
                if trace:
                    traces[key] = {
                        "node": code,
                        "period": p,
                        "dependencies": sorted(graph[code].inputs),
                        "duration_ns": duration,
                        "value": value,
                    }
                results[key] = value

        return (results, traces) if trace else results

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------
    def clear_all(self) -> None:
        self._ast_cache.clear()
        self._value_cache.clear()

    def clear_cache_for(self, code: str) -> None:
        keys_to_del = [k for k in self._value_cache if k[0] == code]
        for k in keys_to_del:
            del self._value_cache[k]
        if code in self._ast_cache:
            del self._ast_cache[code]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _evaluate_one(self, code: str, period: str, graph: GraphState) -> float:
        node = graph[code]
        if node.kind == NodeKind.INPUT:
            if period in node.data:
                return node.data[period]  # base case
            raise CalculationError(
                f"No value for input node {code!r} in period {period}."
            )

        # Evaluate dependencies first
        values_env: Dict[str, float] = {}
        for dep in node.inputs:
            key = (dep, period)
            if key not in self._value_cache:
                self._value_cache[key] = self._evaluate_one(dep, period, graph)
            values_env[dep] = self._value_cache[key]

        # Compile AST lazily -------------------------------------------------
        if node.formula is None:
            raise CalculationError(f"Node {code!r} has no formula to evaluate.")

        if node.formula not in self._ast_cache:
            self._ast_cache[node.formula] = ast.parse(node.formula, mode="eval")
        compiled = compile(
            self._ast_cache[node.formula], filename="<formula>", mode="eval"
        )

        try:
            return float(eval(compiled, {"__builtins__": {}}, values_env))
        except Exception as exc:
            raise CalculationError(f"Failed to evaluate {code!r}: {exc}") from exc
