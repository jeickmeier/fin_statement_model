"""Adjustment data models and related types."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Final, Optional
from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, Field, field_validator
import logging

from .helpers import tag_matches

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------
# Core Types and Constants
# --------------------------------------------------------------------


class AdjustmentType(Enum):
    """Defines how an adjustment modifies a base value."""

    ADDITIVE = "additive"  # base + (value * scale)
    MULTIPLICATIVE = "multiplicative"  # base * (value ** scale)
    REPLACEMENT = "replacement"  # use value (scale ignored)


AdjustmentTag = str  # Slash (/) separates hierarchy levels in tags
DEFAULT_SCENARIO: Final[str] = "default"

# --------------------------------------------------------------------
# Adjustment Model
# --------------------------------------------------------------------


class Adjustment(BaseModel):
    """Immutable record describing a discretionary adjustment to a node's value.

    Attributes:
        id: Unique identifier for the adjustment.
        node_name: The name of the target node.
        period: The primary period the adjustment applies to.
        start_period: The first period the adjustment is effective (inclusive, Phase 2).
        end_period: The last period the adjustment is effective (inclusive, Phase 2).
        value: The numeric value of the adjustment.
        type: How the adjustment combines with the base value.
        scale: Attenuation factor for the adjustment (0.0 to 1.0, Phase 2).
        priority: Tie-breaker for applying multiple adjustments (lower number applied first).
        tags: Set of descriptive tags for filtering and analysis.
        scenario: The named scenario this adjustment belongs to (Phase 2).
        reason: Text description of why the adjustment was made.
        user: Identifier for the user who created the adjustment.
        timestamp: UTC timestamp when the adjustment was created.
    """

    # Target
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    node_name: str
    period: str  # Primary target period
    start_period: Optional[str] = None  # Phase 2 - effective range start (inclusive)
    end_period: Optional[str] = None  # Phase 2 - effective range end (inclusive)

    # Behaviour
    value: float
    type: AdjustmentType = AdjustmentType.ADDITIVE
    scale: float = 1.0  # Phase 2 - 0.0 <= scale <= 1.0
    priority: int = 0  # Lower value means higher priority (applied first)

    # Classification
    tags: set[AdjustmentTag] = Field(default_factory=set)
    scenario: str = DEFAULT_SCENARIO  # Phase 2 - Scenario grouping

    # Metadata
    reason: str
    user: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(frozen=True)

    @field_validator("scale")
    @classmethod
    def _scale_bounds(cls, v: float) -> float:
        """Validate that the scale factor is between 0.0 and 1.0."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Scale must be between 0.0 and 1.0 (inclusive)")
        return v


# --------------------------------------------------------------------
# Adjustment Filtering
# --------------------------------------------------------------------


class AdjustmentFilter(BaseModel):
    """Defines criteria for selecting adjustments.

    Attributes:
        include_scenarios: Only include adjustments from these scenarios.
        exclude_scenarios: Exclude adjustments from these scenarios.
        include_tags: Include adjustments matching any of these tag prefixes.
        exclude_tags: Exclude adjustments matching any of these tag prefixes.
        require_all_tags: Include only adjustments having *all* these exact tags.
        include_types: Only include adjustments of these types.
        exclude_types: Exclude adjustments of these types.
        period: The specific period context for effective window checks.
    """

    # Scenario Filtering
    include_scenarios: Optional[set[str]] = None
    exclude_scenarios: Optional[set[str]] = None

    # Tag Filtering (supports hierarchical matching via helpers.tag_matches)
    # Need to import the helper function first.
    # Let's assume it will be imported at the top level of the module later.

    include_tags: Optional[set[AdjustmentTag]] = None
    exclude_tags: Optional[set[AdjustmentTag]] = None
    require_all_tags: Optional[set[AdjustmentTag]] = None  # Exact match required

    # Type Filtering
    include_types: Optional[set[AdjustmentType]] = None
    exclude_types: Optional[set[AdjustmentType]] = None

    # Context for Effective Window Checks (Phase 2)
    period: Optional[str] = None  # The current period being calculated/viewed

    def matches(self, adj: Adjustment) -> bool:
        """Check if a given adjustment meets the filter criteria."""
        # Need to import the helper function here to avoid circular dependency issues at module level

        # Start assuming it matches, then progressively set to False if any check fails.
        is_match = True

        # --- Scenario Checks ---
        if (self.include_scenarios is not None and adj.scenario not in self.include_scenarios) or (
            self.exclude_scenarios is not None and adj.scenario in self.exclude_scenarios
        ):
            is_match = False

        # --- Tag Checks ---
        # Only check if still potentially a match
        if is_match and (
            (self.include_tags is not None and not tag_matches(adj.tags, self.include_tags))
            or (self.exclude_tags is not None and tag_matches(adj.tags, self.exclude_tags))
            or (self.require_all_tags is not None and not self.require_all_tags.issubset(adj.tags))
        ):
            is_match = False

        # --- Type Checks ---
        # Only check if still potentially a match
        if is_match and (
            (self.include_types is not None and adj.type not in self.include_types)
            or (self.exclude_types is not None and adj.type in self.exclude_types)
        ):
            is_match = False

        # --- Effective Window Check (Phase 2) ---
        # Assumes periods are sortable strings (e.g., 'YYYY-MM' or 'Q1-2023')
        if is_match and self.period is not None:  # Only check if still potentially a match
            logger.debug(
                f"Period check: FilterPeriod={self.period}, AdjStart={adj.start_period}, AdjEnd={adj.end_period}"
            )
            period_match = True  # Assume period is ok unless proven otherwise
            if adj.start_period is not None and self.period < adj.start_period:
                logger.debug("Period check failed: FilterPeriod < AdjStart")
                period_match = False
            # Use 'if period_match' to avoid unnecessary log if start check already failed
            if period_match and adj.end_period is not None and self.period > adj.end_period:
                logger.debug("Period check failed: FilterPeriod > AdjEnd")
                period_match = False

            if period_match:
                logger.debug("Period check passed.")
            else:
                is_match = False  # Period check failed
        # else: # Optional log if period check was skipped
        #     if self.period is not None:
        #         logger.debug("Period check skipped because is_match was already False")
        #     else:
        #         logger.debug("Period check skipped: Filter has no period context.")

        return is_match


# Type alias for flexible filter input
AdjustmentFilterInput = Optional[
    AdjustmentFilter | set[AdjustmentTag] | Callable[[Adjustment], bool]
]
