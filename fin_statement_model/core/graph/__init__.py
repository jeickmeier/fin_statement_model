"""Expose the public graph API for *fin_statement_model*.

This module re-exports the most frequently used classes for working with the
graph layer so end-users can write concise import statements without digging
into the sub-package layout.

Specifically, it makes the following symbols directly available:

* `Graph` – central orchestrator that builds and evaluates calculation graphs.
* `GraphManipulator` – helper for structural mutations (add/remove/replace
  nodes, set values, etc.).
* `GraphTraverser` – read-only utilities for traversal, validation, and cycle
  detection.

Examples:
    Basic usage::

        >>> from fin_statement_model.core.graph import Graph
        >>> g = Graph(periods=["2023"])
        >>> _ = g.add_financial_statement_item("Revenue", {"2023": 100.0})
        >>> g.calculate("Revenue", "2023")
        100.0

Keeping these high-level classes here provides a stable import path should the
internal file structure change in future versions.
"""

# Public façade -----------------------------------------------------------
from fin_statement_model.core.graph.facade import GraphFacade as _GraphFacade

# Deprecation shim – keep old name alive ---------------------------------
import warnings

warnings.warn(
    "Importing 'Graph' from 'fin_statement_model.core.graph' is deprecated. "
    "Import 'GraphFacade' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Alias names ------------------------------------------------------------

GraphFacade = _GraphFacade  # new preferred name
Graph = _GraphFacade  # historical alias

# Import helper sub-APIs **after** aliases are in place to avoid circular imports.
# noqa comments suppress Ruff E402 (import not at top of file).
from fin_statement_model.core.graph.manipulator import GraphManipulator  # noqa: E402
from fin_statement_model.core.graph.traverser import GraphTraverser  # noqa: E402

# Update the public export list.
__all__ = [
    "GraphFacade",
    "Graph",
    "GraphManipulator",
    "GraphTraverser",
]
