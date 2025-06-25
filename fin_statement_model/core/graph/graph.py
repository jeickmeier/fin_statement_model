"""Public Graph class composed from specialised mix-ins.

The Graph class is the central orchestrator for constructing, mutating, traversing, and evaluating
directed graphs of financial statement items and calculations. It is composed from a set of focused
mix-ins, each providing a coherent set of features, including:

- Node creation, update, and removal
- Calculation node and metric management
- Discretionary adjustment support
- Graph merging and representation
- Read-only traversal, validation, and dependency inspection

Features:
    * Add and update financial statement items with time-series values
    * Define calculation nodes using built-in operations or custom formulas
    * Register and compute metrics from the registry (e.g., 'current_ratio')
    * Manage periods automatically (deduplication and sorting)
    * Apply and manage discretionary adjustments for scenario analysis
    * Mutate graph structure safely with automatic cache invalidation
    * Traverse and inspect graph structure: dependencies, successors, predecessors
    * Detect cycles and validate graph integrity
    * Perform topological sorts for ordered evaluations

Examples:
    >>> from fin_statement_model.core.graph import Graph
    >>> g = Graph(periods=["2023", "2024"])
    >>> _ = g.add_financial_statement_item("Revenue", {"2023": 100.0, "2024": 120.0})
    >>> _ = g.add_financial_statement_item("COGS", {"2023": 50.0, "2024": 60.0})
    >>> _ = g.add_calculation(
    ...     name="GrossProfit",
    ...     input_names=["Revenue", "COGS"],
    ...     operation_type="formula",
    ...     formula="input_0 - input_1",
    ...     formula_variable_names=["input_0", "input_1"],
    ... )
    >>> g.calculate("GrossProfit", "2023")
    50.0
    >>> g.manipulator.set_value("COGS", "2023", 55.0)
    >>> g.calculate("GrossProfit", "2023")
    45.0
    >>> g.traverser.get_dependencies("GrossProfit")
    ['Revenue', 'COGS']
    >>> g.traverser.validate()
    []

"""

from __future__ import annotations

import logging

from fin_statement_model.core.graph.components import (
    AdjustmentMixin,
    CalcOpsMixin,
    GraphBaseMixin,
    MergeReprMixin,
    NodeOpsMixin,
    TraversalMixin,
)

__all__: list[str] = ["Graph"]

logger = logging.getLogger(__name__)


class Graph(
    GraphBaseMixin,
    NodeOpsMixin,
    CalcOpsMixin,
    AdjustmentMixin,
    MergeReprMixin,
    TraversalMixin,
):
    """Unified directed-graph abstraction for financial-statement modelling.

    The Graph class exposes a high-level API for building, mutating, and evaluating
    financial statement calculation graphs. All functionality is provided by the mix-ins.

    See module docstring for a comprehensive feature list and usage example.
    """

    # All functionality is provided by the mix-ins.

    def clone(self, *, deep: bool = True) -> Graph:
        """Return a cloned copy of the current graph.

        Args:
            deep: If ``True`` (default) a *deep* copy containing **new** node
                instances and adjustment objects is returned. When ``False`` a
                shallow copy is produced which **shares** node objects with the
                original graph.  The shallow variant is primarily useful for
                quick read-only snapshots.

        Returns:
            Graph: A new :class:`Graph` instance replicating the structure and
            state of *self*.
        """
        # Lazy imports (avoid heavy IO modules during Graph import)
        import copy

        if not deep:
            return copy.copy(self)

        # ------------------------------------------------------------------
        # Deep clone via IO round-trip ensures a clean Graph reconstructor and
        # avoids the complexities of manually copying nested node references.
        # ------------------------------------------------------------------
        from fin_statement_model.io import read_data, write_data

        # Serialise to an in-memory graph-definition dictionary
        graph_def = write_data("graph_definition_dict", self, target=None)

        # Deserialise back into a *new* Graph instance
        cloned_graph = read_data("graph_definition_dict", graph_def)

        # Copy all adjustments (if any) - these are *not* included in the
        # serialized graph definition because they are stored separately on the
        # adjustment manager.  We simply deep-copy to preserve immutability.
        cloned_graph.adjustment_manager.load_adjustments([copy.deepcopy(a) for a in self.list_all_adjustments()])

        return cloned_graph
