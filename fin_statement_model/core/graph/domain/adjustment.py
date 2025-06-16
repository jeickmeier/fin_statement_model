"""Pure value objects for discretionary *adjustments*.

These classes are *immutable* and free of side-effects so that they can live in
shared state (e.g. inside :class:`GraphState`) without concurrency hazards.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional, Set, Union

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

    # ------------------------------------------------------------------
    # Backward-compat helpers (pydantic-like API)
    # ------------------------------------------------------------------
    def model_dump(
        self, *, exclude: set[str] | None = None, mode: str = "python"
    ) -> dict[str, Any]:
        """Return a **dict** representation mimicking *pydantic* ``model_dump``.

        The *mode* parameter is accepted for signature compatibility but has
        no effect – the returned mapping is always plain Python types that are
        JSON-serialisable.
        """

        from dataclasses import asdict

        data = asdict(self)
        if exclude:
            for key in exclude:
                data.pop(key, None)
        return data

    # ------------------------------------------------------------------
    @classmethod
    def model_validate(cls, data: dict[str, Any]) -> "Adjustment":
        """Create :class:`Adjustment` from *data* dict (legacy compat).

        Accepts both ``node`` and legacy ``node_name`` keys.  Additional keys
        are forwarded unchanged; unknown keys raise ``TypeError`` like normal
        dataclass construction would.
        """

        # Shallow copy to avoid mutating caller's dict
        params = dict(data)
        if "node" not in params and "node_name" in params:
            params["node"] = params.pop("node_name")
        return cls(**params)


# ---------------------------------------------------------------------------
# Helper utilities (ported from legacy v1 implementation)
# ---------------------------------------------------------------------------


def tag_matches(target_tags: set[str], prefixes: set[str]) -> bool:
    """Return *True* if any tag in *target_tags* starts with one of *prefixes*.

    Hierarchical tags use the conventional ``"/"`` separator so that the
    prefix ``"A/B"`` matches the concrete tag ``"A/B/C"``.
    """

    if not prefixes or not target_tags:
        return False
    return any(t.startswith(p) for t in target_tags for p in prefixes)


# ---------------------------------------------------------------------------
# Filtering helpers ---------------------------------------------------------
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class AdjustmentFilter:
    # Scenario Filtering ----------------------------------------------------
    include_scenarios: Optional[Set[str]] = None
    exclude_scenarios: Optional[Set[str]] = None

    # Tag Filtering ---------------------------------------------------------
    include_tags: Optional[Set[AdjustmentTag]] = None
    exclude_tags: Optional[Set[AdjustmentTag]] = None
    require_all_tags: Optional[Set[AdjustmentTag]] = None

    # Type Filtering --------------------------------------------------------
    include_types: Optional[Set[AdjustmentType]] = None
    exclude_types: Optional[Set[AdjustmentType]] = None

    # Period context for effective window checks (v2 only keeps *period*)
    period: Optional[str] = None

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def matches(self, adj: "Adjustment") -> bool:
        """Return *True* if *adj* satisfies **all** filter criteria."""

        # Start with optimistic assumption ---------------------------------
        is_match = True

        # Scenario ---------------------------------------------------------
        if (
            self.include_scenarios is not None
            and adj.scenario not in self.include_scenarios
        ):
            return False
        if (
            self.exclude_scenarios is not None
            and adj.scenario in self.exclude_scenarios
        ):
            return False

        # Tags -------------------------------------------------------------
        if self.include_tags is not None and not tag_matches(
            adj.tags, self.include_tags
        ):
            return False
        if self.exclude_tags is not None and tag_matches(adj.tags, self.exclude_tags):
            return False
        if self.require_all_tags is not None and not self.require_all_tags.issubset(
            adj.tags
        ):
            return False

        # Types ------------------------------------------------------------
        if self.include_types is not None and adj.type not in self.include_types:
            return False
        if self.exclude_types is not None and adj.type in self.exclude_types:
            return False

        # Period context – effective window check is not implemented in v2
        # because Adjustment currently stores only *period* without an
        # explicit start/end window.  We preserve parameter for compatibility
        # but skip the check here.

        return is_match

    # ------------------------------------------------------------------
    # Convenience helpers mimicking Pydantic model_copy behaviour --------
    # ------------------------------------------------------------------
    def model_copy(
        self, *, update: Optional[dict[str, Any]] = None
    ) -> "AdjustmentFilter":
        """Return a *shallow* copy optionally overriding selected fields."""

        if not update:
            return AdjustmentFilter(
                include_scenarios=(
                    set(self.include_scenarios) if self.include_scenarios else None
                ),
                exclude_scenarios=(
                    set(self.exclude_scenarios) if self.exclude_scenarios else None
                ),
                include_tags=set(self.include_tags) if self.include_tags else None,
                exclude_tags=set(self.exclude_tags) if self.exclude_tags else None,
                require_all_tags=(
                    set(self.require_all_tags) if self.require_all_tags else None
                ),
                include_types=set(self.include_types) if self.include_types else None,
                exclude_types=set(self.exclude_types) if self.exclude_types else None,
                period=self.period,
            )

        # Create copy then override fields supplied in *update* -------------
        params = self.__dict__.copy()
        params.update(update)
        return AdjustmentFilter(**params)


# Flexible filter input accepted by helpers ---------------------------------
AdjustmentFilterInput = Optional[
    Union[
        AdjustmentFilter,
        Set[AdjustmentTag],
        Callable[["Adjustment"], bool],
    ]
]

# Add new exports -----------------------------------------------------------
__all__.extend(["AdjustmentFilter", "AdjustmentFilterInput", "tag_matches"])
