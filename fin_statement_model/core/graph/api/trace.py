"""Light-weight calculation trace record returned by GraphFacade."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

__all__: list[str] = ["CalcTrace"]


@dataclass(slots=True)
class CalcTrace:
    """Single evaluation step for a node-period pair."""

    node: str
    period: str
    dependencies: List[str]
    duration_ns: int
    value: float
