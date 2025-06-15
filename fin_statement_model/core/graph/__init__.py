"""Expose the public graph API for *fin_statement_model*.

This module re-exports the most frequently used classes for working with the
graph layer so end-users can write concise import statements without digging
into the sub-package layout.

Specifically, it makes the following symbols directly available:

* `Graph` – central orchestrator that builds and evaluates calculation graphs.

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

from typing import TypeAlias

from fin_statement_model.core.graph.api.facade import GraphFacade as GraphFacade

# Keep historical alias `Graph` for backward compatibility, pointing to v2 facade
Graph: TypeAlias = GraphFacade

__all__ = [
    "GraphFacade",
    "Graph",
    # API is intentionally minimal – only Graph & GraphFacade are public.
]
