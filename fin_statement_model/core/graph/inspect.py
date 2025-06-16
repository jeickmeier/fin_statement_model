from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Iterable, cast

# Avoid heavy imports; only import typing and internal engine helpers lazily

if TYPE_CHECKING:
    from fin_statement_model.core.graph.graph import Graph

__all__: list[str] = ["GraphInspector"]


class GraphInspector:
    """Read-only utilities for examining a :class:`~fin_statement_model.core.graph.Graph`.

    End-users obtain an instance via the ``graph.inspect`` attribute.  All
    helpers **must not** mutate the underlying graph – they operate purely on
    immutable state snapshots, therefore thread-safe.
    """

    def __init__(self, graph: "Graph") -> None:  # pragma: no cover – imported later
        # Store *private* reference – consumers should not reach into it.
        self._graph = graph
        # Always read current immutable snapshot via dynamic property to avoid
        # stale references after structural mutations.

    # ------------------------------------------------------------------
    # Topology helpers --------------------------------------------------
    # ------------------------------------------------------------------
    def topological_sort(self) -> list[str]:
        """Return all node codes in dependency order (inputs first)."""
        return list(self._graph._state.order)

    def detect_cycles(self) -> list[list[str]]:
        """Return a list of directed cycles detected in the graph."""
        from fin_statement_model.core.graph.engine.inspect import detect_cycles as _cyc

        return _cyc(self._graph._state)

    def validate(self) -> list[str]:
        """Return human-readable validation error messages (empty if valid)."""
        errors: list[str] = []
        # Missing dependency check --------------------------------------
        for code, node in self._graph._state.nodes.items():
            for dep in node.inputs:
                if dep not in self._graph._state.nodes:
                    errors.append(f"Node '{code}' depends on non-existent node '{dep}'")
        # Cycle detection ------------------------------------------------
        for cyc in self.detect_cycles():
            errors.append(f"Circular dependency: {' -> '.join(cyc)}")
        return errors

    # ------------------------------------------------------------------
    # Dependency graph helpers -----------------------------------------
    # ------------------------------------------------------------------
    def get_dependency_graph(self) -> dict[str, list[str]]:
        """Return mapping *node → sorted dependencies* (read-only)."""
        return {c: sorted(n.inputs) for c, n in self._graph._state.nodes.items()}

    def get_calculation_nodes(self) -> list[str]:
        from fin_statement_model.core.graph.domain import NodeKind

        return [
            c for c, n in self._graph._state.nodes.items() if n.kind is NodeKind.FORMULA
        ]

    def get_dependencies(self, node: str) -> list[str]:
        from fin_statement_model.core.graph.engine.inspect import dependencies as _deps

        return _deps(self._graph._state, node)

    def get_direct_successors(self, node: str) -> list[str]:
        from fin_statement_model.core.graph.engine.inspect import successors as _succ

        return _succ(self._graph._state, node)

    def get_direct_predecessors(self, node: str) -> list[str]:
        from fin_statement_model.core.graph.engine.inspect import predecessors as _pred

        return _pred(self._graph._state, node)

    def breadth_first_search(
        self,
        start_node: str,
        *,
        direction: str = "successors",
    ) -> list[list[str]]:
        """Breadth-first traversal returning layers of nodes."""
        from fin_statement_model.core.graph.engine.inspect import breadth_first as _bf

        return _bf(self._graph._state, start_node, direction=direction)

    # ------------------------------------------------------------------
    # Convenience helpers matching previous Traverser API --------------
    # ------------------------------------------------------------------
    def would_create_cycle(self, new_node: object) -> bool:
        """Return ``True`` if inserting *new_node* would introduce a cycle."""

        from fin_statement_model.core.graph.engine.topology import CycleError, toposort

        code = str(getattr(new_node, "name", getattr(new_node, "code", "")))
        deps_raw = getattr(new_node, "inputs", [])
        deps = {getattr(d, "name", getattr(d, "code", str(d))) for d in deps_raw}
        if not deps:
            return False

        class _Proxy:
            def __init__(self, c: str, d: Iterable[str]):
                self.code: str = c
                self.inputs: Iterable[str] = d

        proxy = _Proxy(code, deps)
        mapping = dict(self._graph._state.nodes)
        mapping_cast = cast(Dict[str, Any], mapping)
        mapping_cast[code] = proxy
        try:
            toposort(mapping_cast)
            return False
        except CycleError:
            return True

    def find_cycle_path(self, start: str, end: str) -> list[str] | None:
        """Return a simple node path if *start* and *end* share a cycle."""

        cycles = self.detect_cycles()
        for cyc in cycles:
            if start in cyc and end in cyc:
                # rotate list so it starts at *start*
                while cyc[0] != start:
                    cyc.append(cyc.pop(0))
                if cyc[-1] != end:
                    cyc.append(end)
                return cyc
        return None
