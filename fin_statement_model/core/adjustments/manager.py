"""Manages the storage, retrieval, and application of adjustments."""

from __future__ import annotations

import logging
import inspect
from collections import defaultdict
from typing import Optional
from uuid import UUID
import math

from .models import (
    Adjustment,
    AdjustmentFilter,
    AdjustmentFilterInput,
    AdjustmentType,
    DEFAULT_SCENARIO,
)

# Core errors
from fin_statement_model.core.errors import AdjustmentError


logger = logging.getLogger(__name__)


class AdjustmentManager:
    """Handle storage, retrieval, and application of adjustments.

    This class provides methods to add, remove, filter, and apply adjustments
    to base values.

    Methods:
        add_adjustment: Add an adjustment, replacing any existing one with the same ID.
        remove_adjustment: Remove an adjustment by ID.
        apply_adjustments: Apply a series of adjustments to a base value.
        get_adjustments: Retrieve adjustments for a node and period.
        get_filtered_adjustments: Retrieve adjustments matching filter criteria.
        get_all_adjustments: List all adjustments.
        clear_all: Remove all adjustments.
        load_adjustments: Load a new list of adjustments.
    """

    def __init__(self, *, strict: bool = False) -> None:
        """Initialize the adjustment manager.

        Args:
            strict: When *True*, invalid or overflow adjustments raise
                :class:`~fin_statement_model.core.errors.AdjustmentError` instead of
                being silently ignored. Defaults to *False* for backwards-compatible
                behaviour.
        """
        # Toggle for error handling strategy
        self.strict = strict

        # Primary index: (scenario, node_name, period) -> list[Adjustment]
        self._by_location: dict[tuple[str, str, str], list[Adjustment]] = defaultdict(
            list
        )
        # Secondary index for quick lookup and removal by ID
        self._by_id: dict[UUID, Adjustment] = {}

    def add_adjustment(self, adj: Adjustment) -> None:
        """Add an adjustment to the manager.

        If an adjustment with the same ID already exists, it is replaced.

        Args:
            adj: The Adjustment object to add.

        Returns:
            None
        """
        # If an adjustment with the same ID already exists, remove it first
        if adj.id in self._by_id:
            self.remove_adjustment(adj.id)

        self._by_id[adj.id] = adj
        key = (adj.scenario, adj.node_name, adj.period)
        self._by_location[key].append(adj)
        # Keep the list sorted by priority, then timestamp for consistent application order
        self._by_location[key].sort(key=lambda x: (x.priority, x.timestamp))

    def remove_adjustment(self, adj_id: UUID) -> bool:
        """Remove an adjustment by its ID.

        Args:
            adj_id: The UUID of the adjustment to remove.

        Returns:
            True if the adjustment was found and removed, False otherwise.
        """
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
        """Apply a single adjustment based on its type and scale.

        Args:
            base_value: The original numeric value.
            adj: The Adjustment object to apply.

        Returns:
            The adjusted value as a float.
        """
        if adj.type == AdjustmentType.ADDITIVE:
            # Ensuring result is float
            return float(base_value + adj.value * adj.scale)
        elif adj.type == AdjustmentType.MULTIPLICATIVE:
            # Guard against complex results when the base is non-positive and the
            # exponent (``scale``) is fractional.
            if base_value <= 0 and 0 < adj.scale < 1:
                msg = (
                    "Invalid multiplicative adjustment on non-positive base with a "
                    "fractional scale; returning base value unchanged."
                )
                logger.warning(msg)
                if self.strict:
                    raise AdjustmentError(msg)
                return base_value

            try:
                # ``math.pow`` provides better error signalling (raises ValueError on
                # negative bases with fractional exponents) and handles huge
                # exponents consistently across platforms.
                result = base_value * math.pow(adj.value, adj.scale)
                if math.isfinite(result):
                    return float(result)
                logger.error("Adjustment produced non-finite result (inf/nan)")
                if self.strict:
                    raise AdjustmentError("Adjustment resulted in non-finite value")
                return base_value
            except (OverflowError, ValueError) as exc:
                logger.error("Adjustment overflow/invalid: %s", exc)
                if self.strict:
                    raise AdjustmentError(str(exc)) from exc
                return base_value
        elif adj.type == AdjustmentType.REPLACEMENT:
            # Scale is ignored for replacement type as per spec
            # Cast to float to satisfy return type
            return float(adj.value)
        else:
            # Should not happen with Enum, but defensively return base value
            return base_value  # pragma: no cover

    def apply_adjustments(
        self, base_value: float, adjustments: list[Adjustment]
    ) -> tuple[float, bool]:
        """Apply a list of adjustments sequentially to a base value.

        Adjustments are applied in order of priority (lower first), then timestamp.

        Args:
            base_value: The starting value before adjustments.
            adjustments: A list of Adjustment objects to apply.

        Returns:
            A tuple of (final adjusted value, boolean indicating if any adjustment was applied).
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
            new_value = self._apply_one(current_value, adj)
            # Only mark as applied if the adjustment actually changed the value.
            if new_value != current_value:
                applied_flag = True
            current_value = new_value

        return current_value, applied_flag

    def get_adjustments(
        self, node_name: str, period: str, *, scenario: str = DEFAULT_SCENARIO
    ) -> list[Adjustment]:
        """Retrieve all adjustments for a specific node, period, and scenario.

        Args:
            node_name: The name of the target node.
            period: The period to retrieve adjustments for.
            scenario: The scenario name to filter adjustments by.

        Returns:
            A list of Adjustment objects for the specified node, period, and scenario.
        """
        key = (scenario, node_name, period)
        # Return a copy to prevent external modification of the internal list
        return list(self._by_location.get(key, []))

    def _normalize_filter(
        self, filter_input: AdjustmentFilterInput, period: Optional[str] = None
    ) -> AdjustmentFilter:
        """Convert flexible filter input into a baseline AdjustmentFilter instance.

        Args:
            filter_input: Criteria for selecting adjustments. Can be:
                - None: use default filter (only default scenario).
                - AdjustmentFilter: existing filter instance.
                - set of tags: shorthand for include_tags filter.
                - Callable[..., bool]: predicate accepting one or two args
                  (Adjustment[, period]).
            period: The period context for the filter (optional).

        Returns:
            A baseline AdjustmentFilter object for scenario and period checks.
        """
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
            # For callable predicates we still construct a baseline AdjustmentFilter so
            # that core scenario / period checks remain in place. The callable itself
            # will be evaluated later in `get_filtered_adjustments`. We purposefully do
            # not restrict `include_scenarios` here – the caller can implement any
            # scenario logic inside the predicate if desired.
            return AdjustmentFilter(period=period)
        else:
            raise TypeError(f"Invalid filter_input type: {type(filter_input)}")

    def get_filtered_adjustments(
        self, node_name: str, period: str, filter_input: AdjustmentFilterInput = None
    ) -> list[Adjustment]:
        """Retrieve adjustments for a node and period that match given filter criteria.

        Args:
            node_name: The target node name.
            period: The period to retrieve adjustments for.
            filter_input: Criteria for selecting adjustments. Can be:
                - None: applies default filter (default scenario, all adjustments).
                - AdjustmentFilter: filter by scenarios, tags, types, and period window.
                - set of tags: shorthand for include_tags filter.
                - Callable[[Adjustment], bool] or Callable[[Adjustment, str], bool]:
                    predicate to select adjustments. Two-arg predicates receive
                    the current period as the second argument.

        Returns:
            A list of matching Adjustment objects sorted by priority and timestamp.
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
            # Determine how many positional arguments the predicate expects. If it
            # accepts two parameters we pass the current period as contextual
            # information. This allows users to write filters that combine
            # adjustment attributes with the calculation period in their logic.
            try:
                param_count = len(inspect.signature(filter_input).parameters)
            except (TypeError, ValueError):
                # Fallback in case the predicate is not introspectable (e.g., built-ins)
                param_count = 1

            if param_count == 1:
                matching_adjustments = [
                    adj
                    for adj in candidate_adjustments
                    if filter_input(adj) and normalized_filter.matches(adj)
                ]
            elif param_count == 2:
                matching_adjustments = [
                    adj
                    for adj in candidate_adjustments
                    if filter_input(adj, period) and normalized_filter.matches(adj)
                ]
            else:
                raise TypeError(
                    "Callable adjustment filter must accept one or two positional arguments"
                )
        else:
            # Apply the normalized AdjustmentFilter's matches method
            matching_adjustments = [
                adj for adj in candidate_adjustments if normalized_filter.matches(adj)
            ]

        # Return sorted list (sorting might be redundant if fetched lists are pre-sorted
        # and filtering maintains order, but ensures correctness)
        return sorted(matching_adjustments, key=lambda x: (x.priority, x.timestamp))

    def get_all_adjustments(self) -> list[Adjustment]:
        """List all adjustments stored in the manager.

        Returns:
            A list of all Adjustment objects currently stored.
        """
        # Return a copy to prevent external modification
        return list(self._by_id.values())

    def clear_all(self) -> None:
        """Remove all adjustments from the manager.

        Clears all internal storage.

        Returns:
            None
        """
        self._by_location.clear()
        self._by_id.clear()

    def load_adjustments(self, adjustments: list[Adjustment]) -> None:
        """Clear existing adjustments and load a new list of adjustments.

        Args:
            adjustments: A list of Adjustment objects to load into the manager.

        Returns:
            None
        """
        self.clear_all()
        for adj in adjustments:
            self.add_adjustment(adj)
