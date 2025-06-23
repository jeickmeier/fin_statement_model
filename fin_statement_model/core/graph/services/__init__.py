"""Service layer package for `fin_statement_model.core.graph`.

This package contains isolated helper classes extracted from the monolithic ``Graph`` class. Each service
is designed to be independent of the Graph and reusable in other contexts (e.g., alternative graph implementations).

| Service Class         | Responsibility / Features                                 |
|----------------------|----------------------------------------------------------|
| CalculationEngine    | Orchestrates node calculations and manages calculation cache |
| PeriodService        | Manages unique, sorted periods and period validation      |
| AdjustmentService    | Encapsulates adjustment storage and application logic     |

These services are composed into the Graph to provide modular, testable, and extensible support for
calculation, period, and adjustment management.
"""

from __future__ import annotations

from .adjustment_service import AdjustmentService
from .calculation_engine import CalculationEngine
from .period_service import PeriodService

__all__: list[str] = [
    "AdjustmentService",
    "CalculationEngine",
    "PeriodService",
]
