"""Diff helpers for Template Registry & Engine (TRE).

This module provides lightweight comparison utilities for assessing structural
and value-level differences between two **Graph** instances.
The functions are intentionally stateless and side-effect-free so they can be
re-used by higher-level APIs (e.g. `TemplateRegistry.diff`).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fin_statement_model.templates.models import (
    DiffResult,
    StructureDiff,
    ValuesDiff,
)

# Imports used only for typing ----------------------------------------------------------------
if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Sequence

    from fin_statement_model.core.graph import Graph

logger = logging.getLogger(__name__)

__all__: list[str] = [
    "compare_structure",
    "compare_values",
    "diff",
]


# ---------------------------------------------------------------------------
# Structure comparison
# ---------------------------------------------------------------------------


def _node_signature(node: Any) -> Any:
    """Return a *stable* signature representing *node* configuration.

    We rely on each node implementing ``to_dict`` which is already a contract
    of the core node hierarchy.  The returned mapping is used for equality
    comparison only - no attempt is made to hash or serialise it.
    """
    try:
        sig = node.to_dict()
        sig = sig.copy()
        # Strip out highly volatile fields that should *not* trigger a
        # structural diff.  Currently only the stored time-series "values"
        # on data nodes fall into this category.
        sig.pop("values", None)
    except Exception:  # pragma: no cover  # noqa: BLE001 - fallback signature
        # Fallback to repr which is less precise but never fails
        return repr(node)
    else:
        return sig


def compare_structure(graph_a: Graph, graph_b: Graph) -> StructureDiff:
    """Return topological differences between *graph_a* and *graph_b*.

    The algorithm is intentionally simple:
    1. Added / removed nodes are determined via set diffs on ``graph.nodes`` keys.
    2. Nodes present in both graphs are compared via their ``to_dict``
       representations - any inequality marks the node as *changed*.
       A short description string is stored but the exact change is not diffed
       (future improvements could add granular field-level analysis).

    Complexity: :math:`O(N)` where ``N`` is the number of nodes.
    """
    nodes_a = graph_a.nodes
    nodes_b = graph_b.nodes

    added_nodes = [n for n in nodes_b if n not in nodes_a]
    removed_nodes = [n for n in nodes_a if n not in nodes_b]

    changed_nodes: dict[str, str] = {}

    common_nodes = (n for n in nodes_a if n in nodes_b)
    for name in common_nodes:
        sig_a = _node_signature(nodes_a[name])
        sig_b = _node_signature(nodes_b[name])
        if sig_a != sig_b:
            changed_nodes[name] = "config"

    return StructureDiff(
        added_nodes=sorted(added_nodes),
        removed_nodes=sorted(removed_nodes),
        changed_nodes=dict(sorted(changed_nodes.items())),
    )


# ---------------------------------------------------------------------------
# Value comparison
# ---------------------------------------------------------------------------


def compare_values(
    graph_a: Graph,
    graph_b: Graph,
    *,
    periods: Sequence[str] | None = None,
    atol: float = 1e-9,
) -> ValuesDiff:
    """Return period-by-period numerical deltas between two graphs.

    Args:
        graph_a: Base graph (left-hand side).
        graph_b: Graph to compare against ``graph_a`` (right-hand side).
        periods: Optional explicit period list. When *None* the intersection
            of ``graph_a.periods`` and ``graph_b.periods`` is used.
        atol: Absolute tolerance below which a delta is considered *equal* and
            therefore suppressed in the returned diff.
    """
    # Determine periods to iterate ----------------------------------------------
    period_list = list(periods) if periods is not None else [p for p in graph_a.periods if p in graph_b.periods]

    if not period_list:
        raise ValueError("No common periods to compare - provide explicit 'periods' argument?")

    changed_cells: dict[str, float] = {}
    max_delta: float | None = None

    common_nodes = [n for n in graph_a.nodes if n in graph_b.nodes]

    calc_a = graph_a.calculate  # local bindings for speed
    calc_b = graph_b.calculate

    for node in common_nodes:
        for period in period_list:
            try:
                val_a = calc_a(node, period)
                val_b = calc_b(node, period)
            except Exception as exc:  # pragma: no cover  # noqa: BLE001 - propagate
                logger.debug("Error calculating values for node '%s' period '%s': %s", node, period, exc)
                continue

            delta = float(val_b) - float(val_a)
            if abs(delta) > atol:
                key = f"{node}|{period}"
                changed_cells[key] = delta
                abs_delta = abs(delta)
                if max_delta is None or abs_delta > max_delta:
                    max_delta = abs_delta

    return ValuesDiff(changed_cells=changed_cells, max_delta=max_delta)


# ---------------------------------------------------------------------------
# Aggregated diff helper
# ---------------------------------------------------------------------------


def diff(
    graph_a: Graph,
    graph_b: Graph,
    *,
    include_values: bool = True,
    periods: Sequence[str] | None = None,
    atol: float = 1e-9,
) -> DiffResult:
    """Return combined structure and (optionally) value diff result."""
    structure = compare_structure(graph_a, graph_b)
    values = None
    if include_values:
        values = compare_values(graph_a, graph_b, periods=periods, atol=atol)

    return DiffResult(structure=structure, values=values)
