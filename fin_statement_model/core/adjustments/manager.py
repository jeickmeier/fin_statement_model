"""Manages the storage, retrieval, and application of adjustments."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Optional
from uuid import UUID

from .models import (
    Adjustment,
    AdjustmentFilter,
    AdjustmentFilterInput,
    AdjustmentType,
    DEFAULT_SCENARIO,
)


logger = logging.getLogger(__name__)


class AdjustmentManager:
    """Handles the lifecycle and application of Adjustment objects.

    Provides methods for adding, removing, filtering, and applying adjustments
    to base values.
    """

    def __init__(self) -> None:
        """Initializes the AdjustmentManager with empty storage."""
        # Primary index: (scenario, node_name, period) -> list[Adjustment]
        self._by_location: dict[tuple[str, str, str], list[Adjustment]] = defaultdict(
            list
        )
        # Secondary index for quick lookup and removal by ID
        self._by_id: dict[UUID, Adjustment] = {}

    def add_adjustment(self, adj: Adjustment) -> None:
        """Adds an adjustment to the manager, replacing if ID exists."""
        # If an adjustment with the same ID already exists, remove it first
        if adj.id in self._by_id:
            self.remove_adjustment(adj.id)

        self._by_id[adj.id] = adj
        key = (adj.scenario, adj.node_name, adj.period)
        self._by_location[key].append(adj)
        # Keep the list sorted by priority, then timestamp for consistent application order
        self._by_location[key].sort(key=lambda x: (x.priority, x.timestamp))

    def remove_adjustment(self, adj_id: UUID) -> bool:
        """Removes an adjustment by its ID. Returns True if found, False otherwise."""
        if adj_id not in self._by_id:
            return False

        adj_to_remove = self._by_id.pop(adj_id)
        key = (adj_to_remove.scenario, adj_to_remove.node_name, adj_to_remove.period)

        if key in self._by_location:
            # Filter out the specific adjustment object instance
            self._by_location[key] = [
                a for a in self._by_location[key] if a.id != adj_id
            ]
            # If the list becomes empty, remove the key
            if not self._by_location[key]:
                del self._by_location[key]
        return True

    def _apply_one(self, base_value: float, adj: Adjustment) -> float:
        """Applies a single adjustment to a value based on its type and scale."""
        if adj.type == AdjustmentType.ADDITIVE:
            return base_value + adj.value * adj.scale
        elif adj.type == AdjustmentType.MULTIPLICATIVE:
            # Ensure base_value is not zero to avoid issues with 0**(negative scale)
            # If base is 0, multiplicative adjustment usually results in 0 unless value is 0.
            # We also need to handle potential complex numbers if base is negative and scale is fractional.
            # For simplicity, let's assume standard financial contexts where this is less common
            # or handle it by convention (e.g., multiplicative doesn't apply to zero/negative base).
            # Let's default to returning 0 if base is 0 for multiplicative.
            if base_value == 0:
                return 0.0
            # Consider adding checks or specific handling for negative base + fractional scale if needed.
            return base_value * (adj.value**adj.scale)
        elif adj.type == AdjustmentType.REPLACEMENT:
            # Scale is ignored for replacement type as per spec
            return adj.value
        else:
            # Should not happen with Enum, but defensively return base value
            return base_value  # pragma: no cover

    def apply_adjustments(
        self, base_value: float, adjustments: list[Adjustment]
    ) -> tuple[float, bool]:
        """Applies a list of adjustments sequentially to a base value.

        Adjustments are applied in order of priority (lower first), then timestamp.

        Args:
            base_value: The starting value before adjustments.
            adjustments: A list of Adjustment objects to apply.

        Returns:
            A tuple containing: (final adjusted value, boolean indicating if any adjustment was applied).
        """
        if not adjustments:
            return base_value, False

        current_value = base_value
        applied_flag = False

        # Sort by priority (ascending), then timestamp (ascending) as per spec
        # Note: add_adjustment already sorts the list in _by_location, but
        # this ensures correctness if an unsorted list is passed directly.
        sorted_adjustments = sorted(
            adjustments, key=lambda x: (x.priority, x.timestamp)
        )

        for adj in sorted_adjustments:
            current_value = self._apply_one(current_value, adj)
            applied_flag = True

        return current_value, applied_flag

    def get_adjustments(
        self, node_name: str, period: str, *, scenario: str = DEFAULT_SCENARIO
    ) -> list[Adjustment]:
        """Retrieves all adjustments for a specific node, period, and scenario."""
        key = (scenario, node_name, period)
        # Return a copy to prevent external modification of the internal list
        return list(self._by_location.get(key, []))

    def _normalize_filter(
        self, filter_input: AdjustmentFilterInput, period: Optional[str] = None
    ) -> AdjustmentFilter:
        """Converts flexible filter input into a standard AdjustmentFilter instance."""
        if filter_input is None:
            # Default filter includes only the default scenario and sets the period context
            return AdjustmentFilter(include_scenarios={DEFAULT_SCENARIO}, period=period)
        elif isinstance(filter_input, AdjustmentFilter):
            # If period context wasn't set on the filter, set it now
            if filter_input.period is None:
                return filter_input.model_copy(update={"period": period})
            return filter_input
        elif isinstance(filter_input, set):
            # Shorthand for include_tags filter
            # Assume shorthand applies only to DEFAULT_SCENARIO unless specified otherwise?
            # Let's keep it simple: Shorthand applies to DEFAULT_SCENARIO only.
            return AdjustmentFilter(
                include_tags=filter_input,
                include_scenarios={DEFAULT_SCENARIO},
                period=period,
            )
        elif callable(filter_input):
            # This case is complex as the callable doesn't inherently know the period.
            # We wrap the callable in a filter, but the effective window check might not work
            # as expected unless the callable itself uses the period.
            # For simplicity, we create a default filter and rely on the callable for matching.
            # The manager will still filter by callable *after* potentially getting adjustments.
            # A more robust solution might involve passing period to the callable.
            # Let's just return a base filter for now and handle callable later.
            # TODO: Revisit handling of callable filters if period context is critical.
            logger.warning(
                "Callable filter used; period context for effective window check might be ignored."
            )
            # Apply callable, but filter to default scenario like other shorthand.
            return AdjustmentFilter(
                include_scenarios={DEFAULT_SCENARIO}, period=period
            )  # Base filter, callable applied later
        else:
            raise TypeError(f"Invalid filter_input type: {type(filter_input)}")

    def get_filtered_adjustments(
        self, node_name: str, period: str, filter_input: AdjustmentFilterInput = None
    ) -> list[Adjustment]:
        """Retrieves adjustments for a node/period that match the given filter criteria.

        Args:
            node_name: The target node name.
            period: The target period.
            filter_input: The filter criteria (AdjustmentFilter, set of tags, callable, or None).

        Returns:
            A list of matching Adjustment objects, sorted by priority and timestamp.
        """
        normalized_filter = self._normalize_filter(filter_input, period)

        candidate_adjustments: list[Adjustment] = []

        # Determine which scenarios to check based on the filter
        scenarios_to_check: set[str]
        if normalized_filter.include_scenarios is not None:
            scenarios_to_check = (
                normalized_filter.include_scenarios.copy()
            )  # Work on a copy
            if normalized_filter.exclude_scenarios is not None:
                scenarios_to_check -= normalized_filter.exclude_scenarios
        elif normalized_filter.exclude_scenarios is not None:
            # Get all scenarios currently known to the manager
            all_known_scenarios = {adj.scenario for adj in self._by_id.values()}
            scenarios_to_check = (
                all_known_scenarios - normalized_filter.exclude_scenarios
            )
        else:
            # No include/exclude specified: check all scenarios relevant for this node/period
            # This requires checking keys in _by_location
            scenarios_to_check = {
                key[0]
                for key in self._by_location
                if key[1] == node_name and key[2] == period
            }
            # If no specific adjustments exist for this node/period, we might check default?
            # Let's assume we only check scenarios that *have* adjustments for this location.
            if not scenarios_to_check:
                # Maybe return empty list early if no scenarios found for location?
                # Or should it behave differently? For now, proceed with empty set.
                pass

        # Gather candidates from relevant locations
        for scenario in scenarios_to_check:
            key = (scenario, node_name, period)
            candidate_adjustments.extend(self._by_location.get(key, []))

        # Apply the filter logic
        matching_adjustments: list[Adjustment] = []
        if callable(filter_input):
            # Apply the callable filter directly
            matching_adjustments = [
                adj for adj in candidate_adjustments if filter_input(adj)
            ]
        else:
            # Apply the normalized AdjustmentFilter's matches method
            matching_adjustments = [
                adj for adj in candidate_adjustments if normalized_filter.matches(adj)
            ]

        # Return sorted list (sorting might be redundant if fetched lists are pre-sorted
        # and filtering maintains order, but ensures correctness)
        return sorted(matching_adjustments, key=lambda x: (x.priority, x.timestamp))

    def get_all_adjustments(self) -> list[Adjustment]:
        """Returns a list of all adjustments currently stored in the manager."""
        # Return a copy to prevent external modification
        return list(self._by_id.values())

    def clear_all(self) -> None:
        """Removes all adjustments from the manager."""
        self._by_location.clear()
        self._by_id.clear()

    def load_adjustments(self, adjustments: list[Adjustment]) -> None:
        """Clears existing adjustments and loads a new list."""
        self.clear_all()
        for adj in adjustments:
            self.add_adjustment(adj)
