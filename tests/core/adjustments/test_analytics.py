"""Tests for adjustment analytics functions."""

import pytest
import pandas as pd
from typing import Optional, Any

from fin_statement_model.core.adjustments.manager import AdjustmentManager
from fin_statement_model.core.adjustments.models import (
    Adjustment,
    AdjustmentType,
    AdjustmentFilter,
)
from fin_statement_model.core.adjustments.analytics import summary, list_by_tag


# Helper to create adjustments
def create_adj(
    node_name: str = "NodeA",
    period: str = "P1",
    value: float = 10,
    scenario: str = "default",
    type: AdjustmentType = AdjustmentType.ADDITIVE,
    tags: Optional[set[str]] = None,
    **kwargs: Any,
) -> Adjustment:
    """Helper function to create an Adjustment for testing."""
    base_args = {
        "node_name": node_name,
        "period": period,
        "value": value,
        "reason": "reason",
        "scenario": scenario,
        "type": type,
        "tags": tags or set(),
    }
    base_args.update(kwargs)
    return Adjustment(**base_args)


@pytest.fixture
def populated_manager() -> AdjustmentManager:
    """Provides an AdjustmentManager populated with diverse adjustments."""
    manager = AdjustmentManager()
    manager.add_adjustment(
        create_adj(node_name="Revenue", period="P1", value=100, tags={"Actual", "Region/NA"})
    )
    manager.add_adjustment(
        create_adj(node_name="Revenue", period="P2", value=120, tags={"Actual", "Region/NA"})
    )
    manager.add_adjustment(
        create_adj(
            node_name="COGS",
            period="P1",
            value=-50,
            tags={"Actual", "Region/NA"},
            type=AdjustmentType.ADDITIVE,
        )
    )
    manager.add_adjustment(
        create_adj(
            node_name="COGS", period="P1", value=5, scenario="Budget", tags={"Budget", "Region/NA"}
        )
    )  # Budget scenario
    manager.add_adjustment(
        create_adj(node_name="Opex", period="P1", value=-20, tags={"Actual", "Type/Recurring"})
    )
    manager.add_adjustment(
        create_adj(node_name="Opex", period="P1", value=-5, tags={"Actual", "Type/NonRecurring"})
    )  # NonRecurring tag
    manager.add_adjustment(
        create_adj(
            node_name="Revenue",
            period="P1",
            value=-10,
            scenario="default",
            tags={"ManualOverride"},
            priority=-1,
        )
    )  # Override with high priority
    return manager


# --- Test summary() ---


def test_summary_default_grouping(populated_manager: AdjustmentManager) -> None:
    """Test summary with default grouping [period, node_name]."""
    summary_df = summary(populated_manager)

    assert isinstance(summary_df, pd.DataFrame)
    assert summary_df.index.names == ["period", "node_name"]
    assert len(summary_df) == 4  # (P1,Revenue), (P2,Revenue), (P1,COGS), (P1,Opex)

    # Check values for a specific group (P1, Revenue) - has 100 and -10 adjustments
    p1_rev = summary_df.loc[("P1", "Revenue")]
    assert p1_rev["count"] == 2
    assert p1_rev["sum_value"] == pytest.approx(90.0)  # 100 - 10
    assert p1_rev["mean_abs_value"] == pytest.approx(55.0)  # (100+10)/2

    # Check (P1, Opex) - has -20 and -5 adjustments
    p1_opex = summary_df.loc[("P1", "Opex")]
    assert p1_opex["count"] == 2
    assert p1_opex["sum_value"] == pytest.approx(-25.0)
    assert p1_opex["mean_abs_value"] == pytest.approx(12.5)  # (20+5)/2


def test_summary_group_by_scenario(populated_manager: AdjustmentManager) -> None:
    """Test summary grouping by scenario."""
    summary_df = summary(populated_manager, group_by=["scenario"])
    assert isinstance(summary_df, pd.DataFrame)
    assert summary_df.index.name == "scenario"
    assert len(summary_df) == 2  # default, Budget

    default_summary = summary_df.loc["default"]
    budget_summary = summary_df.loc["Budget"]

    assert default_summary["count"] == 6  # 6 adjustments in default scenario
    assert budget_summary["count"] == 1
    assert budget_summary["sum_value"] == 5.0


def test_summary_group_by_type(populated_manager: AdjustmentManager) -> None:
    """Test summary grouping by type."""
    # All adjustments are ADDITIVE in this fixture
    summary_df = summary(populated_manager, group_by=["type"])
    assert len(summary_df) == 1
    assert summary_df.index[0] == str(AdjustmentType.ADDITIVE)
    assert summary_df.iloc[0]["count"] == 7  # All 7 are additive


def test_summary_with_filter_tags(populated_manager: AdjustmentManager) -> None:
    """Test summary applying a tag filter (shorthand)."""
    # Filter for only 'Actual' tags
    # Use the parent tag "Actual" - should match 5 adjustments via tag_matches
    summary_df = summary(populated_manager, filter_input={"Actual"})
    # Should match 5 adjustments across 3 groups: (P1,Revenue), (P1,COGS), (P1,Opex), (P2,Revenue)
    # Note: ManualOverride adj for (P1, Revenue) does NOT have "Actual" tag.
    # Correction: The high-prio Rev adj doesn't have "Actual", so 5 tags match.
    # (P1, Rev) -> 1, (P2, Rev) -> 1, (P1, COGS) -> 1, (P1, Opex) -> 2 = 5 adjustments
    # Groups: (P1, Revenue), (P2, Revenue), (P1, COGS), (P1, Opex) -> 4 groups
    assert len(summary_df) == 4
    # Check total count across groups
    assert summary_df["count"].sum() == 5  # 5 adjustments have 'Actual' tag


def test_summary_with_filter_adjustment_filter(populated_manager: AdjustmentManager) -> None:
    """Test summary applying an AdjustmentFilter object."""
    # Filter for default scenario and Opex node
    # Update filter: AdjustmentFilter doesn't support node_names directly in .matches()
    # Let's filter by tag instead for this test case.
    # Filter for the "Type/Recurring" tag (should match only the -20 Opex adj)
    test_filter = AdjustmentFilter(include_tags={"Type/Recurring"})
    summary_df = summary(populated_manager, filter_input=test_filter)
    # Expected result: One group (P1, Opex)
    assert len(summary_df) == 1
    assert summary_df.index[0] == ("P1", "Opex") # Default grouping is (period, node_name)
    assert summary_df.iloc[0]["count"] == 1
    assert summary_df.iloc[0]["sum_value"] == -20.0


def test_summary_empty(populated_manager: AdjustmentManager) -> None:
    """Test summary when the filter results in no adjustments."""
    summary_df = summary(populated_manager, filter_input={"NonExistentTag"})
    assert isinstance(summary_df, pd.DataFrame)
    assert summary_df.empty
    # Check columns and index are set correctly for empty df
    assert summary_df.index.names == ["period", "node_name"]
    assert list(summary_df.columns) == ["count", "sum_value", "mean_abs_value"]


# --- Test list_by_tag() ---


def test_list_by_tag_simple_prefix(populated_manager: AdjustmentManager) -> None:
    """Test listing adjustments by a simple tag prefix."""
    results = list_by_tag(populated_manager, "Region/")
    assert len(results) == 4  # Rev P1, Rev P2, COGS P1 (Actual), COGS P1 (Budget)
    assert all("Region/NA" in adj.tags for adj in results)


def test_list_by_tag_specific_prefix(populated_manager: AdjustmentManager) -> None:
    """Test listing adjustments by a more specific prefix."""
    results = list_by_tag(populated_manager, "Type/NonRecurring")
    assert len(results) == 1
    assert results[0].node_name == "Opex"
    assert results[0].value == -5


def test_list_by_tag_no_match(populated_manager: AdjustmentManager) -> None:
    """Test listing when no tags match the prefix."""
    results = list_by_tag(populated_manager, "UnknownPrefix")
    assert len(results) == 0


def test_list_by_tag_with_additional_filter(populated_manager: AdjustmentManager) -> None:
    """Test listing by tag prefix combined with another filter."""
    # List by Region/ prefix, but only include Budget scenario
    test_filter = AdjustmentFilter(include_scenarios={"Budget"})
    results = list_by_tag(populated_manager, "Region/", filter_input=test_filter)
    assert len(results) == 1
    assert results[0].node_name == "COGS"
    assert results[0].scenario == "Budget"


def test_list_by_tag_sorting(populated_manager: AdjustmentManager) -> None:
    """Test that list_by_tag results are sorted by priority, timestamp."""
    # Focus on P1, Revenue which has priority 0 and -1 adjustments
    # Filter for the plain "Actual" tag
    results = list_by_tag(populated_manager, "Actual")
    # The high priority one (-1) does *not* have the "Actual" tag in the fixture.
    # Let's check the priority 0 "Actual" Revenue adjustment vs others.
    actual_rev_p1 = next(a for a in results if a.node_name == "Revenue" and a.period == "P1" and a.scenario == "default")
    # Find COGS adjustments
    cogs_actual = next(a for a in results if a.node_name == "COGS" and a.scenario == "default")
    # cogs_budget does not have "Actual" tag

    # Check relative order based on timestamp (assuming default sorting for priority 0)
    assert results.index(actual_rev_p1) < results.index(cogs_actual)
    # Cannot reliably check further without controlling timestamps.
    # Timestamps would determine order between same-priority items if we controlled them
