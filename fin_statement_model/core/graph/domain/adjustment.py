"""Pure value objects for discretionary *adjustments*.

These classes are *immutable* and free of side-effects so that they can live in
shared state (e.g. inside :class:`GraphState`) without concurrency hazards.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Set

__all__: list[str] = ["AdjustmentType", "Adjustment"]


class AdjustmentType(str, Enum):
    """Enumeration of modification semantics applied to a base value."""

    ADDITIVE = "additive"  # base + (value * scale)
    MULTIPLICATIVE = "multiplicative"  # base * (value ** scale)
    REPLACEMENT = "replacement"  # use *value* directly, ignore scale

    def apply(self, base: float, value: float, scale: float = 1.0) -> float:
        """Return the adjusted value given *base*, *value*, *scale*."""
        if self is AdjustmentType.ADDITIVE:
            return float(base + (value * scale))
        if self is AdjustmentType.MULTIPLICATIVE:
            return float(base * (value**scale))
        # Replacement by default (ignore scale)
        return float(value)


AdjustmentTag = str  # simple alias – hierarchical tags use '/'


@dataclass(frozen=True, slots=True)
class Adjustment:
    """Describe a discretionary change to a node/period value.

    Attributes
    ----------
    id:
        Stable UUID generated at creation – used as primary identifier.
    node:
        Target node *code* this adjustment applies to.
    period:
        Period string compatible with :class:`Period.parse` (kept as str to
        avoid import cycle).  The engine will resolve lazily.
    value:
        Numeric value used by the adjustment (see :class:`AdjustmentType`).
    type:
        Adjustment behaviour (add, multiply, replace).  Defaults to *additive*.
    scale:
        Attenuation factor ``0.0 ≤ scale ≤ 1.0`` for additive / multiplicative.
    priority:
        Lower values are applied first if multiple adjustments affect the same
        node/period.
    tags:
        Arbitrary label set for filtering (hierarchical separated by '/').
    scenario:
        Scenario grouping identifier – ``"default"`` if unspecified.
    reason:
        Free-text description shown in audit & trace outputs.
    user:
        User identifier (if applicable) – e.g. email or username.
    timestamp:
        UTC timestamp captured at creation (immutable).
    """

    node: str
    period: str
    value: float
    reason: str
    # Optional / secondary ----------------------------------------------------
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    type: AdjustmentType = AdjustmentType.ADDITIVE
    scale: float = 1.0
    priority: int = 0
    tags: Set[AdjustmentTag] = field(default_factory=set)
    scenario: str = "default"
    user: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # ------------------------------------------------------------------
    # Validation hooks (post-init since dataclass is frozen)
    # ------------------------------------------------------------------
    def __post_init__(self) -> None:
        if not 0.0 <= self.scale <= 1.0:
            raise ValueError("scale must be between 0.0 and 1.0 inclusive")

    # ------------------------------------------------------------------
    # Behaviour helpers
    # ------------------------------------------------------------------
    def apply_to(self, base: float) -> float:
        """Return the *adjusted* value based on *base*."""
        return self.type.apply(base, self.value, self.scale)
