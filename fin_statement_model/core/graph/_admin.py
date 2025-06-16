"""Low-level write helpers for advanced users & tests.

The functions in this module are *not* part of the official public API.  They
are intentionally placed in a leading-underscore module so that importing them
requires an explicit opt-in::

    from fin_statement_model.core.graph import _admin
    _admin.merge_from(dst, src)

All helpers are thin wrappers that delegate to internal (private) methods on
:class:`~fin_statement_model.core.graph.Graph` so they stay in sync with the
main implementation.
"""

from __future__ import annotations

from typing import Any, Dict, cast

from fin_statement_model.core.graph.graph import Graph

__all__: list[str] = [
    "merge_from",
    "add_node",
    "would_create_cycle",
    "clear_caches",
]


def merge_from(dst: Graph, src: Graph) -> None:  # pragma: no cover
    """Merge *src* graph into *dst* graph (best-effort)."""

    dst.merge_from(src)


def add_node(graph: Graph, node_obj: Any) -> None:  # pragma: no cover
    """Insert a **pre-built** node object into *graph*."""

    graph.add_node(node_obj)


def would_create_cycle(graph: Graph, node_obj: Any) -> bool:  # pragma: no cover
    """Return ``True`` if inserting *node_obj* would introduce a cycle."""

    # Re-use the logic previously implemented in GraphFacade.would_create_cycle.
    from fin_statement_model.core.graph.engine.topology import CycleError, toposort

    code = str(getattr(node_obj, "name", getattr(node_obj, "code", "")))
    deps_raw = getattr(node_obj, "inputs", [])
    deps = {getattr(d, "name", getattr(d, "code", str(d))) for d in deps_raw}
    if not deps:
        return False

    class _Proxy:
        def __init__(self, c: str, d: Any):
            self.code: str = c
            self.inputs: Any = d

    proxy = _Proxy(code, deps)
    mapping = dict(graph._state.nodes)  # pylint: disable=protected-access
    mapping_cast = cast(Dict[str, Any], mapping)
    mapping_cast[code] = proxy
    try:
        toposort(mapping)
        return False
    except CycleError:
        return True


def clear_caches(graph: Graph) -> None:  # pragma: no cover
    """Clear **all** cached calculation results on *graph*."""

    graph.clear_calculation_cache()
