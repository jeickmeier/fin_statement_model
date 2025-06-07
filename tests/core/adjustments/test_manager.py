"""Tests for the AdjustmentManager class."""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta, UTC
from typing import Any

from fin_statement_model.core.adjustments.manager import AdjustmentManager
from fin_statement_model.core.adjustments.models import (
    Adjustment,
    AdjustmentType,
    AdjustmentFilter,
    DEFAULT_SCENARIO,
)


# Helper to create adjustments
def create_adj(
    node_name: str = "NodeA",
    period: str = "P1",
    value: float = 10,
    scenario: str = DEFAULT_SCENARIO,
    **kwargs: Any,
) -> Adjustment:
    """Helper function to create an Adjustment for testing."""
    base_args = {
        "node_name": node_name,
        "period": period,
        "value": value,
        "reason": "reason",
        "scenario": scenario,
    }
    base_args.update(kwargs)
    return Adjustment(**base_args)


@pytest.fixture
def manager() -> AdjustmentManager:
    """Provides an empty AdjustmentManager instance for tests."""
    return AdjustmentManager()


# --- Test add_adjustment and get_adjustments ---


def test_add_and_get_adjustment(manager: AdjustmentManager) -> None:
    """Test adding a single adjustment and retrieving it."""
    adj1 = create_adj()
    manager.add_adjustment(adj1)

    # Get by exact location/scenario
    retrieved = manager.get_adjustments("NodeA", "P1")
    assert retrieved == [adj1]

    # Get by different location/scenario (should be empty)
    assert manager.get_adjustments("NodeB", "P1") == []
    assert manager.get_adjustments("NodeA", "P2") == []
    assert manager.get_adjustments("NodeA", "P1", scenario="Other") == []

    # Test get_all_adjustments
    assert manager.get_all_adjustments() == [adj1]


def test_add_multiple_adjustments_same_location(manager: AdjustmentManager) -> None:
    """Test adding multiple adjustments to the same location respects priority/time."""
    now = datetime.now(UTC)
    adj1 = create_adj(
        node_name="N",
        period="P",
        value=1,
        priority=1,
        timestamp=now - timedelta(seconds=10),
    )
    adj2 = create_adj(
        node_name="N",
        period="P",
        value=2,
        priority=0,
        timestamp=now - timedelta(seconds=5),
    )
    adj3 = create_adj(node_name="N", period="P", value=3, priority=1, timestamp=now)

    manager.add_adjustment(adj1)
    manager.add_adjustment(adj2)
    manager.add_adjustment(adj3)

    retrieved = manager.get_adjustments("N", "P")
    # Expected order: adj2 (priority 0), adj1 (priority 1, older), adj3 (priority 1, newer)
    assert retrieved == [adj2, adj1, adj3]
    assert manager.get_all_adjustments() == [adj1, adj2, adj3]  # Order might vary here


def test_add_adjustment_replace(manager: AdjustmentManager) -> None:
    """Test that adding an adjustment with an existing ID replaces the old one."""
    adj_id = uuid4()
    adj1 = create_adj(id=adj_id, value=10)
    adj2 = create_adj(id=adj_id, value=20, period="P2")  # Same ID, different details

    manager.add_adjustment(adj1)
    assert manager.get_adjustments("NodeA", "P1") == [adj1]
    assert manager.get_adjustments("NodeA", "P2") == []
    assert len(manager.get_all_adjustments()) == 1

    manager.add_adjustment(adj2)  # Replace adj1
    assert manager.get_adjustments("NodeA", "P1") == []  # Original location now empty
    assert manager.get_adjustments("NodeA", "P2") == [adj2]  # New location has adj2
    assert len(manager.get_all_adjustments()) == 1
    assert manager.get_all_adjustments()[0].value == 20  # Check it's the new value


# --- Test remove_adjustment ---


def test_remove_adjustment_exists(manager: AdjustmentManager) -> None:
    """Test removing an adjustment that exists."""
    adj1 = create_adj()
    adj2 = create_adj(period="P2")
    manager.add_adjustment(adj1)
    manager.add_adjustment(adj2)

    assert len(manager.get_all_adjustments()) == 2
    removed = manager.remove_adjustment(adj1.id)

    assert removed is True
    assert len(manager.get_all_adjustments()) == 1
    assert manager.get_all_adjustments() == [adj2]
    assert manager.get_adjustments("NodeA", "P1") == []
    assert manager.get_adjustments("NodeA", "P2") == [adj2]


def test_remove_adjustment_not_exists(manager: AdjustmentManager) -> None:
    """Test removing an adjustment that does not exist."""
    adj1 = create_adj()
    manager.add_adjustment(adj1)

    non_existent_id = uuid4()
    removed = manager.remove_adjustment(non_existent_id)

    assert removed is False
    assert len(manager.get_all_adjustments()) == 1
    assert manager.get_adjustments("NodeA", "P1") == [adj1]


# --- Test apply_adjustments ---


def test_apply_adjustments_empty(manager: AdjustmentManager) -> None:
    """Test applying adjustments when the list is empty."""
    value, flag = manager.apply_adjustments(100.0, [])
    assert value == 100.0
    assert flag is False


def test_apply_adjustments_additive(manager: AdjustmentManager) -> None:
    """Test applying additive adjustments."""
    adj1 = create_adj(value=10, priority=0)
    adj2 = create_adj(value=5, priority=1)
    value, flag = manager.apply_adjustments(100.0, [adj1, adj2])
    # Expected: 100 + 10 (adj1) + 5 (adj2) = 115
    assert value == 115.0
    assert flag is True


def test_apply_adjustments_multiplicative(manager: AdjustmentManager) -> None:
    """Test applying multiplicative adjustments."""
    adj1 = create_adj(value=1.2, type=AdjustmentType.MULTIPLICATIVE, priority=0)
    adj2 = create_adj(value=0.5, type=AdjustmentType.MULTIPLICATIVE, priority=1)
    value, flag = manager.apply_adjustments(100.0, [adj1, adj2])
    # Expected: 100 * 1.2 (adj1) * 0.5 (adj2) = 60
    assert value == pytest.approx(60.0)
    assert flag is True


def test_apply_adjustments_replacement(manager: AdjustmentManager) -> None:
    """Test applying replacement adjustments."""
    adj1 = create_adj(value=50, type=AdjustmentType.ADDITIVE, priority=0)
    adj2 = create_adj(value=75, type=AdjustmentType.REPLACEMENT, priority=1)
    value, flag = manager.apply_adjustments(100.0, [adj1, adj2])
    # Expected: 100 + 50 (adj1) -> 150. Then replaced by 75 (adj2).
    assert value == 75.0
    assert flag is True


def test_apply_adjustments_mixed_types_priority(manager: AdjustmentManager) -> None:
    """Test applying mixed adjustment types respecting priority."""
    adj_add = create_adj(value=10, type=AdjustmentType.ADDITIVE, priority=1)
    adj_mul = create_adj(
        value=2, type=AdjustmentType.MULTIPLICATIVE, priority=0
    )  # Applied first
    adj_rep = create_adj(value=500, type=AdjustmentType.REPLACEMENT, priority=2)

    value, flag = manager.apply_adjustments(100.0, [adj_add, adj_mul, adj_rep])
    # Expected: 100 * 2 (adj_mul) -> 200 + 10 (adj_add) -> 210. Replaced by 500 (adj_rep).
    assert value == 500.0
    assert flag is True


def test_apply_adjustments_scaling_additive(manager: AdjustmentManager) -> None:
    """Test scaling with additive adjustments."""
    adj1 = create_adj(value=20, scale=0.5)
    value, flag = manager.apply_adjustments(100.0, [adj1])
    # Expected: 100 + (20 * 0.5) = 110
    assert value == 110.0
    assert flag is True


def test_apply_adjustments_scaling_multiplicative(manager: AdjustmentManager) -> None:
    """Test scaling with multiplicative adjustments."""
    adj1 = create_adj(value=4, type=AdjustmentType.MULTIPLICATIVE, scale=0.5)
    value, flag = manager.apply_adjustments(100.0, [adj1])
    # Expected: 100 * (4 ** 0.5) = 100 * 2 = 200
    assert value == pytest.approx(200.0)
    assert flag is True


def test_apply_adjustments_scaling_replacement(manager: AdjustmentManager) -> None:
    """Test that scaling is ignored for replacement adjustments."""
    adj1 = create_adj(value=75, type=AdjustmentType.REPLACEMENT, scale=0.1)
    value, flag = manager.apply_adjustments(100.0, [adj1])
    # Expected: 75 (scale ignored)
    assert value == 75.0
    assert flag is True


# --- Test get_filtered_adjustments (Basic) ---
# More complex filter normalization tests might be needed later


def test_get_filtered_adjustments_no_filter(manager: AdjustmentManager) -> None:
    """Test get_filtered_adjustments with filter=None (default scenario)."""
    adj1_default = create_adj(scenario=DEFAULT_SCENARIO)
    adj2_other = create_adj(scenario="OtherScenario")
    manager.add_adjustment(adj1_default)
    manager.add_adjustment(adj2_other)

    filtered = manager.get_filtered_adjustments("NodeA", "P1", filter_input=None)
    assert filtered == [adj1_default]


def test_get_filtered_adjustments_by_scenario(manager: AdjustmentManager) -> None:
    """Test filtering by include_scenarios."""
    adj1_default = create_adj(scenario=DEFAULT_SCENARIO)
    adj2_s1 = create_adj(scenario="S1")
    adj3_s2 = create_adj(scenario="S2")
    manager.add_adjustment(adj1_default)
    manager.add_adjustment(adj2_s1)
    manager.add_adjustment(adj3_s2)

    filt = AdjustmentFilter(include_scenarios={"S1", "S2"})
    filtered = manager.get_filtered_adjustments("NodeA", "P1", filter_input=filt)
    # Order depends on internal sorting (priority/timestamp)
    assert set(adj.id for adj in filtered) == {adj2_s1.id, adj3_s2.id}


def test_get_filtered_adjustments_by_tags_shorthand(manager: AdjustmentManager) -> None:
    """Test filtering using the set[str] shorthand for include_tags."""
    adj1_a = create_adj(tags={"A/B"})
    adj2_b = create_adj(tags={"B/C"})
    manager.add_adjustment(adj1_a)
    manager.add_adjustment(adj2_b)

    filtered = manager.get_filtered_adjustments("NodeA", "P1", filter_input={"A"})
    assert filtered == [adj1_a]


# --- Test clear_all and load_adjustments ---


def test_clear_all(manager: AdjustmentManager) -> None:
    """Test clearing all adjustments."""
    adj1 = create_adj()
    adj2 = create_adj(period="P2")
    manager.add_adjustment(adj1)
    manager.add_adjustment(adj2)

    assert len(manager.get_all_adjustments()) == 2
    manager.clear_all()
    assert len(manager.get_all_adjustments()) == 0
    assert manager.get_adjustments("NodeA", "P1") == []


def test_load_adjustments(manager: AdjustmentManager) -> None:
    """Test loading a list of adjustments, replacing existing ones."""
    adj_old1 = create_adj(node_name="OldNode")
    manager.add_adjustment(adj_old1)

    adj_new1 = create_adj(node_name="NewNodeA", value=1)
    adj_new2 = create_adj(node_name="NewNodeB", value=2)
    new_list = [adj_new1, adj_new2]

    manager.load_adjustments(new_list)

    assert len(manager.get_all_adjustments()) == 2
    assert manager.get_adjustments("OldNode", "P1") == []
    # Order might vary, check content
    assert set(adj.id for adj in manager.get_all_adjustments()) == {
        adj_new1.id,
        adj_new2.id,
    }
