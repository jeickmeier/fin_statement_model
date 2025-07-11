"""Define core adjustment data models and related types.

This module provides the Adjustment and AdjustmentFilter Pydantic models,
as well as related constants and enums for representing and filtering
adjustments in financial statement models.

Examples:
    >>> from fin_statement_model.core.adjustments.models import Adjustment, AdjustmentType
    >>> adj = Adjustment(node_name="Revenue", period="2023-01", value=100.0, reason="Manual update")
    >>> adj.type == AdjustmentType.ADDITIVE
    True
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from enum import Enum
import logging
from typing import Final
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .helpers import tag_matches

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------
# Core Types and Constants
# --------------------------------------------------------------------


class AdjustmentType(Enum):
    """Defines how an adjustment modifies a base value.

    ADDITIVE: base + (value * scale)
    MULTIPLICATIVE: base * (value ** scale)
    REPLACEMENT: use value (scale ignored)

    Examples:
        >>> AdjustmentType.ADDITIVE.value
        'additive'
    """

    ADDITIVE = "additive"
    MULTIPLICATIVE = "multiplicative"
    REPLACEMENT = "replacement"


AdjustmentTag = str  # Slash (/) separates hierarchy levels in tags
DEFAULT_SCENARIO: Final[str] = "default"

# --------------------------------------------------------------------
# Adjustment Model
# --------------------------------------------------------------------


class Adjustment(BaseModel):
    """Immutable record describing a discretionary adjustment to a node's value.

    Each adjustment can modify a base value by addition, multiplication, or replacement.

    Attributes:
        id: Unique identifier for the adjustment.
        node_name: Name of the target node.
        period: Primary period the adjustment applies to.
        start_period: Optional start of the effective period range.
        end_period: Optional end of the effective period range.
        value: Numeric value of the adjustment.
        type: AdjustmentType defining how the adjustment is applied.
        scale: Attenuation factor between 0.0 and 1.0.
        priority: Tie-breaker for multiple adjustments (lower first).
        tags: Set of tags for filtering and analysis.
        scenario: Scenario name grouping the adjustment.
        reason: Description of the adjustment.
        user: Identifier of the user who created the adjustment.
        timestamp: UTC timestamp when the adjustment was created.

    Examples:
        >>> from fin_statement_model.core.adjustments.models import Adjustment, AdjustmentType
        >>> adj = Adjustment(node_name="Revenue", period="2023-01", value=100.0, reason="Manual update")
        >>> adj.type == AdjustmentType.ADDITIVE
        True
    """

    # Target
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    node_name: str
    period: str  # Primary target period
    start_period: str | None = None  # Phase 2 - effective range start (inclusive)
    end_period: str | None = None  # Phase 2 - effective range end (inclusive)

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
    user: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(frozen=True)

    @field_validator("scale")
    @classmethod
    def _scale_bounds(cls, v: float) -> float:
        """Validate that the scale factor is between 0.0 and 1.0.

        Args:
            v: The scale value to validate.

        Returns:
            The validated scale value.

        Raises:
            ValueError: If the scale is not between 0.0 and 1.0.

        Examples:
            >>> Adjustment(node_name="A", period="2023", value=1.0, reason="r", scale=0.5).scale
            0.5
        """
        if not 0.0 <= v <= 1.0:
            raise ValueError("Scale must be between 0.0 and 1.0 (inclusive)")
        return v


# --------------------------------------------------------------------
# Adjustment Filtering
# --------------------------------------------------------------------


class AdjustmentFilter(BaseModel):
    """Define criteria for selecting adjustments.

    Attributes:
        include_scenarios: Set of scenarios to include.
        exclude_scenarios: Set of scenarios to exclude.
        include_tags: Set of tag prefixes to include.
        exclude_tags: Set of tag prefixes to exclude.
        require_all_tags: Set of tags that must all be present.
        include_types: Set of AdjustmentType to include.
        exclude_types: Set of AdjustmentType to exclude.
        period: Optional period for effective window checks.

    Examples:
        >>> from fin_statement_model.core.adjustments.models import AdjustmentFilter, AdjustmentType
        >>> filt = AdjustmentFilter(include_types={AdjustmentType.ADDITIVE})
        >>> isinstance(filt, AdjustmentFilter)
        True
    """

    # Scenario Filtering
    include_scenarios: set[str] | None = None
    exclude_scenarios: set[str] | None = None

    # Tag Filtering (supports hierarchical matching via helpers.tag_matches)
    # Need to import the helper function first.
    # Let's assume it will be imported at the top level of the module later.

    include_tags: set[AdjustmentTag] | None = None
    exclude_tags: set[AdjustmentTag] | None = None
    require_all_tags: set[AdjustmentTag] | None = None  # Exact match required

    # Type Filtering
    include_types: set[AdjustmentType] | None = None
    exclude_types: set[AdjustmentType] | None = None

    # Context for Effective Window Checks (Phase 2)
    period: str | None = None  # The current period being calculated/viewed

    def matches(self, adj: Adjustment) -> bool:
        """Check whether a given adjustment meets the filter criteria.

        Args:
            adj: The Adjustment instance to test.

        Returns:
            True if the adjustment matches all criteria, False otherwise.

        Examples:
            >>> from fin_statement_model.core.adjustments.models import Adjustment, AdjustmentFilter, AdjustmentType
            >>> adj = Adjustment(node_name="A", period="2023", value=1.0, reason="r", type=AdjustmentType.ADDITIVE)
            >>> filt = AdjustmentFilter(include_types={AdjustmentType.ADDITIVE})
            >>> filt.matches(adj)
            True
        """
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
                "Period check: FilterPeriod=%s, AdjStart=%s, AdjEnd=%s",
                self.period,
                adj.start_period,
                adj.end_period,
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

        return is_match


# Accept callables that take one or two positional arguments. Using Callable[..., bool]
# allows flexible predicates while keeping type safety at a reasonable level.
AdjustmentFilterInput = AdjustmentFilter | set[AdjustmentTag] | Callable[..., bool] | None
