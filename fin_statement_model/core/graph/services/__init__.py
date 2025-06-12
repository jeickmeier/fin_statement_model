"""Service layer package for `fin_statement_model.core.graph`.

Contains isolated helper classes extracted from the monolithic ``Graph`` class.
At the end of the refactor each class here should be *independent of* ``Graph``
and reusable in other contexts (e.g., alternative graph implementations).
"""

from __future__ import annotations

from .calculation_engine import CalculationEngine
from .period_service import PeriodService
from .adjustment_service import AdjustmentService
from .data_item_service import DataItemService
from .merge_service import MergeService

__all__: list[str] = [
    "CalculationEngine",
    "PeriodService",
    "AdjustmentService",
    "DataItemService",
    "MergeService",
]
