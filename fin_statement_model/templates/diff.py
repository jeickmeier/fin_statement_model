"""Template comparison utilities for the Template Registry & Engine (TRE).

This module provides stateless, side-effect-free comparison functions for
analyzing differences between financial statement template graphs. The utilities
support both structural analysis (node topology changes) and value-level 
comparison (numerical deltas).

The functions are designed to be composable and reusable across different
parts of the system, including the TemplateRegistry.diff() API and standalone
template analysis workflows.

Key Functions:
    - **compare_structure()**: Analyze topology differences (added/removed/changed nodes)
    - **compare_values()**: Calculate numerical deltas between corresponding cells
    - **diff()**: Comprehensive comparison combining structure and values

Example:
    >>> from fin_statement_model.templates.diff import diff
    >>> from fin_statement_model.templates import TemplateRegistry
    >>> 
    >>> # Get two template graphs
    >>> graph_a = TemplateRegistry.instantiate('lbo.standard_v1')
    >>> graph_b = graph_a.clone()
    >>> 
    >>> # Make some changes to graph_b
    >>> graph_b.add_periods(['2029'])
    >>> 
    >>> # Compare the graphs
    >>> result = diff(graph_a, graph_b, include_values=True)
    >>> print(f"Structure changes: {len(result.structure.added_nodes)} added")
    >>> print(f"Value changes: {len(result.values.changed_cells)} cells")
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
    """Generate a stable signature for node configuration comparison.

    Creates a hashable representation of a node's configuration by extracting
    its dictionary representation and removing volatile fields like time-series
    values that shouldn't trigger structural diffs.

    Args:
        node: Graph node implementing the to_dict() method

    Returns:
        Stable configuration signature suitable for equality comparison

    Example:
        >>> # Assuming node implements to_dict()
        >>> sig1 = _node_signature(revenue_node)
        >>> sig2 = _node_signature(revenue_node_copy)
        >>> sig1 == sig2  # True if configurations match
        True
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
    """Analyze topological differences between two financial statement graphs.

    Performs a comprehensive structural comparison identifying added nodes,
    removed nodes, and nodes with changed configurations. The algorithm
    focuses on graph topology and node configuration while ignoring
    time-series values.

    Args:
        graph_a: Base graph for comparison (left-hand side)
        graph_b: Target graph to compare against graph_a (right-hand side)

    Returns:
        StructureDiff containing categorized structural changes:
            - added_nodes: Nodes present only in graph_b
            - removed_nodes: Nodes present only in graph_a  
            - changed_nodes: Nodes in both graphs with different configurations

    Example:
        >>> from fin_statement_model.templates.diff import compare_structure
        >>> 
        >>> # Create two graphs with different structures
        >>> structure_diff = compare_structure(base_graph, modified_graph)
        >>> 
        >>> print(f"Added: {structure_diff.added_nodes}")
        >>> print(f"Removed: {structure_diff.removed_nodes}")
        >>> print(f"Changed: {list(structure_diff.changed_nodes.keys())}")

    Note:
        The comparison uses each node's to_dict() representation for
        configuration analysis. Time-series values are excluded to focus
        on structural rather than data changes. Complexity is O(N) where
        N is the number of nodes.
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
    """Calculate period-by-period numerical differences between two graphs.

    Compares calculated values for corresponding nodes and periods between
    two graphs, identifying cells where numerical values differ beyond the
    specified tolerance threshold.

    Args:
        graph_a: Base graph for comparison (left-hand side)
        graph_b: Target graph to compare against graph_a (right-hand side)
        periods: Explicit list of periods to compare. If None, uses the
            intersection of periods from both graphs
        atol: Absolute tolerance threshold. Differences smaller than this
            value are considered equal and excluded from results

    Returns:
        ValuesDiff containing:
            - changed_cells: Mapping of "node|period" to numerical delta (B - A)
            - max_delta: Largest absolute difference found (useful for summaries)

    Raises:
        ValueError: If no common periods exist and periods parameter is None

    Example:
        >>> from fin_statement_model.templates.diff import compare_values
        >>> 
        >>> # Compare values between base and modified graphs
        >>> values_diff = compare_values(
        ...     base_graph, 
        ...     modified_graph,
        ...     periods=["2024", "2025"],
        ...     atol=0.01  # Ignore differences < 1 cent
        ... )
        >>> 
        >>> # Show significant changes
        >>> for cell, delta in values_diff.changed_cells.items():
        ...     node, period = cell.split("|")
        ...     print(f"{node} {period}: ${delta:,.2f} change")
        >>> 
        >>> print(f"Largest change: ${values_diff.max_delta:,.2f}")

    Note:
        Only compares nodes that exist in both graphs. Calculation errors
        for individual cells are logged but don't stop the overall comparison.
        The function calls graph.calculate() for each node/period combination.
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
    """Perform comprehensive comparison between two financial statement graphs.

    Combines structural and optional value-level analysis into a single
    comprehensive diff result. This is the primary entry point for template
    comparison workflows.

    Args:
        graph_a: Base graph for comparison (left-hand side)
        graph_b: Target graph to compare against graph_a (right-hand side)
        include_values: Whether to include numerical value comparison in addition
            to structural analysis. Set to False for faster topology-only diffs
        periods: Explicit list of periods for value comparison. If None, uses
            intersection of periods from both graphs
        atol: Absolute tolerance for value comparison. Differences below this
            threshold are considered equal

    Returns:
        DiffResult containing:
            - structure: Structural differences (always included)
            - values: Value differences (only if include_values=True)

    Example:
        >>> from fin_statement_model.templates.diff import diff
        >>> 
        >>> # Full comparison with values
        >>> full_diff = diff(graph_a, graph_b, include_values=True)
        >>> 
        >>> # Structure-only comparison (faster)
        >>> structure_diff = diff(graph_a, graph_b, include_values=False)
        >>> 
        >>> # Custom period subset and tolerance
        >>> custom_diff = diff(
        ...     graph_a, 
        ...     graph_b,
        ...     periods=["2024", "2025"],
        ...     atol=1.0  # Ignore sub-dollar differences
        ... )
        >>> 
        >>> # Check for any changes
        >>> has_structural_changes = (
        ...     len(full_diff.structure.added_nodes) > 0 or
        ...     len(full_diff.structure.removed_nodes) > 0 or 
        ...     len(full_diff.structure.changed_nodes) > 0
        ... )
        >>> 
        >>> has_value_changes = (
        ...     full_diff.values is not None and 
        ...     len(full_diff.values.changed_cells) > 0
        ... )

    Note:
        The function always performs structural comparison as it's fast and
        essential for understanding template differences. Value comparison
        can be disabled via include_values=False when only topology matters.
    """
    structure = compare_structure(graph_a, graph_b)
    values = None
    if include_values:
        values = compare_values(graph_a, graph_b, periods=periods, atol=atol)

    return DiffResult(structure=structure, values=values)
