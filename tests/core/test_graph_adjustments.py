"""Tests for the integration of AdjustmentManager with the Graph class."""

import pytest
from uuid import uuid4
import pandas as pd
from fin_statement_model.core.graph import Graph
from fin_statement_model.core.adjustments import (
    Adjustment,
    AdjustmentFilter,
    AdjustmentType,
)
from fin_statement_model.core.errors import NodeError
from pytest_mock import MockerFixture
from unittest.mock import MagicMock


# Helper to create a basic graph with a couple of nodes
@pytest.fixture
def basic_graph() -> Graph:
    """Creates a simple Graph instance with two nodes and two periods."""
    graph = Graph(periods=["P1", "P2"])
    graph.add_financial_statement_item("NodeA", {"P1": 100, "P2": 110})
    graph.add_financial_statement_item("NodeB", {"P1": 50, "P2": 55})
    return graph


# --- Test Graph Adjustment Wrapper Methods ---


def test_graph_add_adjustment(basic_graph: Graph) -> None:
    """Test adding an adjustment via the Graph method."""
    adj_id = basic_graph.add_adjustment(
        node_name="NodeA", period="P1", value=10, reason="Test Add"
    )
    assert isinstance(adj_id, uuid4().__class__)  # Check type

    # Verify it was added to the manager via list_all_adjustments
    all_adjs = basic_graph.list_all_adjustments()
    assert len(all_adjs) == 1
    assert all_adjs[0].id == adj_id
    assert all_adjs[0].node_name == "NodeA"
    assert all_adjs[0].period == "P1"
    assert all_adjs[0].value == 10


def test_graph_add_adjustment_node_not_found(basic_graph: Graph) -> None:
    """Test error handling when adding adjustment to non-existent node."""
    with pytest.raises(NodeError, match="Node 'NonExistentNode' not found"):
        basic_graph.add_adjustment("NonExistentNode", "P1", 5, "reason")


def test_graph_remove_adjustment(basic_graph: Graph) -> None:
    """Test removing an adjustment via the Graph method."""
    adj_id = basic_graph.add_adjustment("NodeA", "P1", 10, "reason")
    assert len(basic_graph.list_all_adjustments()) == 1

    removed = basic_graph.remove_adjustment(adj_id)
    assert removed is True
    assert len(basic_graph.list_all_adjustments()) == 0

    removed_again = basic_graph.remove_adjustment(adj_id)
    assert removed_again is False


def test_graph_get_adjustments(basic_graph: Graph) -> None:
    """Test getting adjustments for a specific location via Graph method."""
    adj1_p1 = basic_graph.add_adjustment("NodeA", "P1", 10, "r1")
    adj2_p1 = basic_graph.add_adjustment("NodeA", "P1", 5, "r2", priority=1)
    adj3_p2 = basic_graph.add_adjustment("NodeA", "P2", 20, "r3")
    adj4_b_p1 = basic_graph.add_adjustment("NodeB", "P1", 30, "r4")

    # Get for NodeA, P1 (default scenario)
    node_a_p1_adjs = basic_graph.get_adjustments("NodeA", "P1")
    # Should be sorted by priority (adj1 then adj2)
    assert node_a_p1_adjs == [
        basic_graph.adjustment_manager._by_id[adj1_p1],
        basic_graph.adjustment_manager._by_id[adj2_p1],
    ]

    # Get for NodeA, P2
    node_a_p2_adjs = basic_graph.get_adjustments("NodeA", "P2")
    assert len(node_a_p2_adjs) == 1
    assert node_a_p2_adjs[0].id == adj3_p2

    # Get for NodeB, P1
    node_b_p1_adjs = basic_graph.get_adjustments("NodeB", "P1")
    assert len(node_b_p1_adjs) == 1
    assert node_b_p1_adjs[0].id == adj4_b_p1

    # Get for non-existent combo
    assert basic_graph.get_adjustments("NodeA", "P3") == []
    assert basic_graph.get_adjustments("NodeC", "P1") == []


# --- Test get_adjusted_value and was_adjusted ---


def test_get_adjusted_value_no_adjustments(basic_graph: Graph) -> None:
    """Test getting value when no adjustments exist."""
    val = basic_graph.get_adjusted_value("NodeA", "P1")
    assert val == 100.0
    val, flag = basic_graph.get_adjusted_value("NodeA", "P1", return_flag=True)
    assert val == 100.0
    assert flag is False
    assert basic_graph.was_adjusted("NodeA", "P1") is False


def test_get_adjusted_value_with_adjustment(basic_graph: Graph) -> None:
    """Test getting value with a simple additive adjustment."""
    basic_graph.add_adjustment("NodeA", "P1", 10, "reason")
    val = basic_graph.get_adjusted_value("NodeA", "P1")
    assert val == 110.0  # 100 + 10
    val, flag = basic_graph.get_adjusted_value("NodeA", "P1", return_flag=True)
    assert val == 110.0
    assert flag is True
    assert basic_graph.was_adjusted("NodeA", "P1") is True


def test_get_adjusted_value_multiple_adjustments(basic_graph: Graph) -> None:
    """Test applying multiple adjustments respecting priority."""
    basic_graph.add_adjustment("NodeA", "P1", 10, "r1", priority=1)
    basic_graph.add_adjustment(
        "NodeA", "P1", 5, "r2", adj_type=AdjustmentType.MULTIPLICATIVE, priority=0
    )  # Use adj_type

    val = basic_graph.get_adjusted_value("NodeA", "P1")
    # Expected: 100 * 5 -> 500 + 10 -> 510
    assert val == 510.0
    assert basic_graph.was_adjusted("NodeA", "P1") is True


def test_get_adjusted_value_with_filter(basic_graph: Graph) -> None:
    """Test filtering adjustments during calculation."""
    basic_graph.add_adjustment("NodeA", "P1", 10, "r1", tags={"Actual"}, scenario="s1")
    basic_graph.add_adjustment("NodeA", "P1", 20, "r2", tags={"Budget"}, scenario="s2")

    # Default filter (None) should use default scenario -> no adjustments applied
    val_default = basic_graph.get_adjusted_value("NodeA", "P1", filter_input=None)
    assert val_default == 100.0

    # Filter for scenario s1
    filt_s1 = AdjustmentFilter(include_scenarios={"s1"})
    val_s1 = basic_graph.get_adjusted_value("NodeA", "P1", filter_input=filt_s1)
    assert val_s1 == 110.0  # 100 + 10

    # Filter for Budget tag (shorthand)
    val_budget = basic_graph.get_adjusted_value("NodeA", "P1", filter_input={"Budget"})
    # Shorthand defaults to default scenario, so no match
    assert val_budget == 100.0

    # Filter for Budget tag across all scenarios (won't work with shorthand, need Filter object)
    AdjustmentFilter(
        include_tags={"Budget"}, include_scenarios=None
    )  # How to signify all scenarios?
    # Let's test filtering for a specific scenario + tag
    filt_s2_budget = AdjustmentFilter(include_scenarios={"s2"}, include_tags={"Budget"})
    val_s2_budget = basic_graph.get_adjusted_value(
        "NodeA", "P1", filter_input=filt_s2_budget
    )
    assert val_s2_budget == 120.0  # 100 + 20

    # Test was_adjusted with filter
    assert basic_graph.was_adjusted("NodeA", "P1", filter_input=None) is False
    assert basic_graph.was_adjusted("NodeA", "P1", filter_input=filt_s1) is True
    assert basic_graph.was_adjusted("NodeA", "P1", filter_input=filt_s2_budget) is True


def test_get_adjusted_value_node_not_found(basic_graph: Graph) -> None:
    """Test error when getting adjusted value for non-existent node."""
    with pytest.raises(NodeError, match="Node 'NodeC' not found"):
        basic_graph.get_adjusted_value("NodeC", "P1")
    with pytest.raises(NodeError, match="Node 'NodeC' not found"):
        basic_graph.was_adjusted("NodeC", "P1")


# --- Test Excel Convenience Methods (Mocked IO) ---


@pytest.fixture
def mock_excel_io(mocker: MockerFixture) -> tuple[MagicMock, MagicMock]:
    """Mocks the read_excel and write_excel functions."""
    mock_read = mocker.patch("fin_statement_model.io.adjustments_excel.read_excel")
    mock_write = mocker.patch("fin_statement_model.io.adjustments_excel.write_excel")
    # Mock read_excel to return some valid adjustments and an empty error df
    adj1 = Adjustment(id=uuid4(), node_name="NodeA", period="P1", value=1, reason="r")
    adj2 = Adjustment(id=uuid4(), node_name="NodeB", period="P2", value=2, reason="r")
    mock_read.return_value = ([adj1, adj2], pd.DataFrame())
    return mock_read, mock_write


def test_graph_load_adjustments_from_excel(
    basic_graph: Graph, mock_excel_io: tuple[MagicMock, MagicMock]
) -> None:
    """Test the graph's load_adjustments_from_excel method."""
    mock_read, _ = mock_excel_io
    filepath = "dummy/path/adjustments.xlsx"

    # Test loading without replace
    basic_graph.add_adjustment("NodeA", "P2", 99, "existing")  # Add one manually first
    assert len(basic_graph.list_all_adjustments()) == 1

    error_df = basic_graph.load_adjustments_from_excel(filepath, replace=False)

    mock_read.assert_called_once_with(filepath)
    assert error_df.empty
    # Should have existing + 2 loaded
    assert len(basic_graph.list_all_adjustments()) == 3
    # Check one of the loaded adjustments is present
    loaded_ids = {a.id for a in mock_read.return_value[0]}
    assert any(adj.id in loaded_ids for adj in basic_graph.list_all_adjustments())

    # Test loading with replace
    error_df_replace = basic_graph.load_adjustments_from_excel(filepath, replace=True)

    assert mock_read.call_count == 2
    assert error_df_replace.empty
    # Should have only the 2 loaded adjustments
    assert len(basic_graph.list_all_adjustments()) == 2
    manager_ids = {a.id for a in basic_graph.list_all_adjustments()}
    assert manager_ids == loaded_ids  # Check IDs match exactly


def test_graph_export_adjustments_to_excel(
    basic_graph: Graph, mock_excel_io: tuple[MagicMock, MagicMock]
) -> None:
    """Test the graph's export_adjustments_to_excel method."""
    _, mock_write = mock_excel_io
    filepath = "dummy/path/export.xlsx"

    basic_graph.add_adjustment("NodeA", "P1", 10, "r1")
    basic_graph.add_adjustment("NodeB", "P1", 20, "r2")
    adjustments_in_graph = basic_graph.list_all_adjustments()

    basic_graph.export_adjustments_to_excel(filepath)

    mock_write.assert_called_once_with(adjustments_in_graph, filepath)
