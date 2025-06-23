"""Graph component mix-ins.

This package houses focused mix-ins extracted from the original, monolithic
``graph.py`` implementation.  Each mix-in groups a coherent set of public and
private methods, keeping every file well below the 500 LOC guideline while
preserving the public behaviour of :class:`fin_statement_model.core.graph.graph.Graph`.

Each mix-in provides a distinct set of features for the Graph class:

| Mix-in            | Responsibility / Features                                      |
|-------------------|---------------------------------------------------------------|
| GraphBaseMixin    | Core state, constructor, and helpers shared by all mix-ins     |
| NodeOpsMixin      | Node creation, update, replacement, and value-setting          |
| CalcOpsMixin      | Calculation node helpers, metric management, calculation cache |
| AdjustmentMixin   | Discretionary adjustment API and helpers                      |
| MergeReprMixin    | Graph merging logic and developer-friendly __repr__            |
| TraversalMixin    | Read-only traversal, validation, and dependency inspection     |

These mix-ins are composed together in the main `Graph` class to provide a unified,
extensible API for financial statement graph modeling.
"""

from __future__ import annotations

from ._adjustment_ops import AdjustmentMixin
from ._base import GraphBaseMixin
from ._calc_ops import CalcOpsMixin
from ._merge_repr import MergeReprMixin
from ._node_ops import NodeOpsMixin
from ._traversal_ops import TraversalMixin

__all__: list[str] = [
    "AdjustmentMixin",
    "CalcOpsMixin",
    "GraphBaseMixin",
    "MergeReprMixin",
    "NodeOpsMixin",
    "TraversalMixin",
]
