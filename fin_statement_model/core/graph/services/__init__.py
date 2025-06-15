"""Service layer for `fin_statement_model.core.graph`.

This sub-package groups **graph-agnostic utilities** that are reused by the
high-level `Graph` façade but do **not** depend on its concrete implementation.
Keeping stateful concerns (period management, calculation caching, etc.) in
dedicated services improves testability, maintainability, and allows future
graphs or pipelines to compose only the pieces they need.
"""

from __future__ import annotations

from .adjustment_service import AdjustmentService
from .calculation_engine import CalculationEngine
from .data_item_service import DataItemService
from .introspector import GraphIntrospector
from .merge_service import MergeService
from .node_registry import NodeRegistryService
from .period_service import PeriodService

__all__: list[str] = [
    "CalculationEngine",
    "PeriodService",
    "AdjustmentService",
    "DataItemService",
    "MergeService",
    "GraphIntrospector",
    "NodeRegistryService",
]
