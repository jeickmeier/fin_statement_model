"""Public Graph class composed from specialised mix-ins.

This file used to contain the full implementation (>1 000 LOC).  That logic has
been extracted into compact mix-ins under ``fin_statement_model.core.graph.components``.
Keeping this thin façade here preserves the public import path
``fin_statement_model.core.graph.graph.Graph`` while satisfying the < 500 LOC
requirement.
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
    """Unified directed-graph abstraction for financial-statement modelling."""

    # All functionality is provided by the mix-ins.
    pass
