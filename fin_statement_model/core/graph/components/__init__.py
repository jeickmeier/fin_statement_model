"""Graph component mix-ins.

This package houses focused mix-ins extracted from the original, monolithic
``graph.py`` implementation.  Each mix-in groups a coherent set of public and
private methods, keeping every file well below the 500 LOC guideline while
preserving the public behaviour of :class:`fin_statement_model.core.graph.graph.Graph`.
"""

from __future__ import annotations

from ._base import GraphBaseMixin
from ._node_ops import NodeOpsMixin
from ._calc_ops import CalcOpsMixin
from ._adjustment_ops import AdjustmentMixin
from ._merge_repr import MergeReprMixin
from ._traversal_ops import TraversalMixin

__all__: list[str] = [
    "GraphBaseMixin",
    "NodeOpsMixin",
    "CalcOpsMixin",
    "AdjustmentMixin",
    "MergeReprMixin",
    "TraversalMixin",
]
