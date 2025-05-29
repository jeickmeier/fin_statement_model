"""Tests for Adjustment data models and filters."""

import pytest
from uuid import UUID
from datetime import datetime, timedelta, UTC
from typing import Any

from pydantic import ValidationError

from fin_statement_model.core.adjustments.models import (
    Adjustment,
    AdjustmentType,
    AdjustmentFilter,
    DEFAULT_SCENARIO,
)

# Assuming helpers is importable for tag matching tests

# --- Adjustment Model Tests ---


def test_adjustment_creation_defaults():
    """Test basic Adjustment creation and default values."""
    now = datetime.now(UTC)
    adj = Adjustment(node_name="Revenue", period="2023", value=100.0, reason="Test reason")

    assert isinstance(adj.id, UUID)
    assert adj.node_name == "Revenue"
    assert adj.period == "2023"
    assert adj.value == 100.0
    assert adj.reason == "Test reason"
    assert adj.type == AdjustmentType.ADDITIVE
    assert adj.scale == 1.0
    assert adj.priority == 0
    assert adj.tags == set()
    assert adj.scenario == DEFAULT_SCENARIO
    assert adj.user is None
    assert isinstance(adj.timestamp, datetime)
    # Make naive timestamp aware for comparison
    assert (
        now - timedelta(seconds=5) < adj.timestamp.replace(tzinfo=UTC) < now + timedelta(seconds=5)
    )
    assert adj.start_period is None
    assert adj.end_period is None
    assert adj.model_config.get("frozen") is True


def test_adjustment_creation_explicit():
    """Test Adjustment creation with explicitly set values."""
    ts = datetime(2023, 1, 1, 12, 0, 0)
    tags = {"proj_x", "manual"}
    adj = Adjustment(
        node_name="COGS",
        period="2023-Q1",
        value=50.0,
        reason="Manual override",
        type=AdjustmentType.REPLACEMENT,
        scale=0.5,  # Should be ignored for replacement, but check validation
        priority=-1,
        tags=tags,
        scenario="Stress Case",
        user="analyst1",
        timestamp=ts,
        start_period="2023-Q1",
        end_period="2023-Q4",
    )
    assert adj.node_name == "COGS"
    assert adj.period == "2023-Q1"
    assert adj.value == 50.0
    assert adj.reason == "Manual override"
    assert adj.type == AdjustmentType.REPLACEMENT
    assert adj.scale == 0.5  # Validation passes, usage depends on type
    assert adj.priority == -1
    assert adj.tags == tags
    assert adj.scenario == "Stress Case"
    assert adj.user == "analyst1"
    assert adj.timestamp == ts
    assert adj.start_period == "2023-Q1"
    assert adj.end_period == "2023-Q4"


@pytest.mark.parametrize("invalid_scale", [-0.1, 1.1])
def test_adjustment_invalid_scale(invalid_scale: float):
    """Test that invalid scale values raise ValidationError."""
    with pytest.raises(ValidationError, match="Scale must be between 0.0 and 1.0"):
        Adjustment(
            node_name="Revenue",
            period="2023",
            value=100.0,
            reason="Test invalid scale",
            scale=invalid_scale,
        )


# --- AdjustmentFilter Model Tests ---


def test_adjustment_filter_defaults():
    """Test AdjustmentFilter default values."""
    f = AdjustmentFilter()
    assert f.include_scenarios is None
    assert f.exclude_scenarios is None
    assert f.include_tags is None
    assert f.exclude_tags is None
    assert f.require_all_tags is None
    assert f.include_types is None
    assert f.exclude_types is None
    assert f.period is None


def test_adjustment_filter_explicit():
    """Test AdjustmentFilter with explicitly set values."""
    f = AdjustmentFilter(
        include_scenarios={"s1", "s2"},
        exclude_tags={"internal"},
        include_types={AdjustmentType.ADDITIVE},
        period="2024-Q1",
    )
    assert f.include_scenarios == {"s1", "s2"}
    assert f.exclude_tags == {"internal"}
    assert f.include_types == {AdjustmentType.ADDITIVE}
    assert f.period == "2024-Q1"


# --- AdjustmentFilter.matches() Tests ---


# Helper to create a basic adjustment for filter tests
def create_test_adj(**kwargs: Any) -> Adjustment:
    """Helper function to create an Adjustment instance with default values."""
    defaults = {
        "node_name": "TestNode",
        "period": "P1",  # Use simple period for base
        "value": 10,
        "reason": "-",
        "scenario": DEFAULT_SCENARIO,
        "tags": set(),
    }
    defaults.update(kwargs)
    return Adjustment(**defaults)


@pytest.mark.parametrize(
    ("filter_props", "adj_props", "expected_match"),
    [
        # Scenario Matching
        ({}, {}, True),  # Default filter matches default adjustment
        ({"include_scenarios": {"s1"}}, {"scenario": "s1"}, True),
        ({"include_scenarios": {"s1"}}, {"scenario": "s2"}, False),
        ({"exclude_scenarios": {"s1"}}, {"scenario": "s1"}, False),
        ({"exclude_scenarios": {"s1"}}, {"scenario": "s2"}, True),
        (
            {"include_scenarios": {"s1"}, "exclude_scenarios": {"s1"}},
            {"scenario": "s1"},
            False,
        ),  # Exclude wins
        # Type Matching
        (
            {"include_types": {AdjustmentType.ADDITIVE}},
            {"type": AdjustmentType.ADDITIVE},
            True,
        ),
        (
            {"include_types": {AdjustmentType.ADDITIVE}},
            {"type": AdjustmentType.REPLACEMENT},
            False,
        ),
        (
            {"exclude_types": {AdjustmentType.REPLACEMENT}},
            {"type": AdjustmentType.REPLACEMENT},
            False,
        ),
        (
            {"exclude_types": {AdjustmentType.REPLACEMENT}},
            {"type": AdjustmentType.ADDITIVE},
            True,
        ),
        # Tag Matching (relies on tag_matches helper)
        ({"include_tags": {"A"}}, {"tags": {"A/B"}}, True),  # Prefix match
        ({"include_tags": {"A"}}, {"tags": {"B/C"}}, False),
        (
            {"exclude_tags": {"Internal"}},
            {"tags": {"Internal/Audit"}},
            False,
        ),  # Exclude prefix
        ({"exclude_tags": {"Internal"}}, {"tags": {"External"}}, True),
        (
            {"require_all_tags": {"A", "B"}},
            {"tags": {"A", "B", "C"}},
            True,
        ),  # Subset exact match
        (
            {"require_all_tags": {"A", "B"}},
            {"tags": {"A", "C"}},
            False,
        ),  # Missing required
        (
            {"include_tags": {"A"}, "exclude_tags": {"A/Internal"}},
            {"tags": {"A/B"}},
            True,
        ),  # Include matches, exclude doesn't
        (
            {"include_tags": {"A"}, "exclude_tags": {"A/Internal"}},
            {"tags": {"A/Internal"}},
            False,
        ),  # Exclude overrides include
        # Period Matching (Effective Window) - Use sortable strings like PXX
        pytest.param({"period": "P06"}, {}, True, id="period_match_no_adj_limits"),
        pytest.param(
            {"period": "P06"},
            {"start_period": "P01"},
            True,
            id="period_match_after_start",
        ),
        pytest.param(
            {"period": "P06"},
            {"start_period": "P07"},
            False,
            id="period_match_before_start",
        ),
        pytest.param({"period": "P06"}, {"end_period": "P12"}, True, id="period_match_before_end"),
        pytest.param({"period": "P06"}, {"end_period": "P05"}, False, id="period_match_after_end"),
        pytest.param(
            {"period": "P06"},
            {"start_period": "P01", "end_period": "P12"},
            True,
            id="period_match_within_range",
        ),
        pytest.param(
            {"period": "P06"},
            {"start_period": "P07", "end_period": "P12"},
            False,
            id="period_match_outside_range_before",
        ),
        pytest.param(
            {"period": "P06"},
            {"start_period": "P01", "end_period": "P05"},
            False,
            id="period_match_outside_range_after",
        ),
        pytest.param(
            {},
            {"start_period": "P01"},
            True,
            id="period_match_no_filter_period",
        ),
        # Combinations
        (
            {"include_scenarios": {"s1"}, "include_types": {AdjustmentType.ADDITIVE}},
            {"scenario": "s1", "type": AdjustmentType.ADDITIVE},
            True,
        ),  # Both match
        (
            {"include_scenarios": {"s1"}, "include_types": {AdjustmentType.ADDITIVE}},
            {"scenario": "s1", "type": AdjustmentType.REPLACEMENT},
            False,
        ),  # Type mismatch
        (
            {"include_scenarios": {"s1"}, "include_types": {AdjustmentType.ADDITIVE}},
            {"scenario": "s2", "type": AdjustmentType.ADDITIVE},
            False,
        ),  # Scenario mismatch
    ],
)
def test_adjustment_filter_matches(
    filter_props: dict[str, Any], adj_props: dict[str, Any], expected_match: bool
) -> None:
    """Test the AdjustmentFilter.matches() method with various filter and adjustment properties."""
    test_filter = AdjustmentFilter(**filter_props)
    test_adj = create_test_adj(**adj_props)
    assert test_filter.matches(test_adj) == expected_match
