"""Expose the public graph API for *fin_statement_model*.

This module re-exports the most frequently used classes for working with the
graph layer so end-users can write concise import statements without digging
into the sub-package layout.

Specifically, it makes the following symbols directly available:

* `Graph` - central orchestrator that builds and evaluates calculation graphs.
* `GraphManipulator` - helper for structural mutations (add/remove/replace
  nodes, set values, etc.).
* `GraphTraverser` - read-only utilities for traversal, validation, and cycle
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

from fin_statement_model.core.graph.graph import Graph
from fin_statement_model.core.graph.manipulator import GraphManipulator
from fin_statement_model.core.graph.traverser import GraphTraverser

__all__ = ["Graph", "GraphManipulator", "GraphTraverser"]
