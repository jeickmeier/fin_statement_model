"""Tests for the FinancialStatementItemNode."""

import pytest
from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode


# --- Fixtures ---


@pytest.fixture
def sample_values() -> dict[str, float]:
    """Provides sample period-value data."""
    return {"2022": 100.0, "2023": 150.5, "2024": -50.0}


@pytest.fixture
def item_node(sample_values: dict[str, float]) -> FinancialStatementItemNode:
    """Provides a FinancialStatementItemNode instance for testing."""
    return FinancialStatementItemNode(name="Revenue", values=sample_values.copy())


# --- Test Cases ---


def test_item_node_init(item_node: FinancialStatementItemNode, sample_values: dict[str, float]):
    """Test successful initialization of FinancialStatementItemNode."""
    assert item_node.name == "Revenue"
    assert item_node.values == sample_values
    # Check if Node base class init was implicitly called (if it expects name)
    # This depends on the base class implementation, but name should be set.
    assert hasattr(item_node, "name")


def test_item_node_calculate_existing_period(item_node: FinancialStatementItemNode):
    """Test calculate method retrieves value for an existing period."""
    assert item_node.calculate("2023") == 150.5
    assert item_node.calculate("2024") == -50.0


def test_item_node_calculate_non_existing_period(item_node: FinancialStatementItemNode):
    """Test calculate method returns 0.0 for a non-existing period."""
    assert item_node.calculate("2021") == 0.0


def test_item_node_get_value_existing_period(item_node: FinancialStatementItemNode):
    """Test get_value method retrieves value for an existing period."""
    assert item_node.get_value("2022") == 100.0
    assert item_node.get_value("2023") == 150.5


def test_item_node_get_value_non_existing_period(item_node: FinancialStatementItemNode):
    """Test get_value method returns 0.0 for a non-existing period."""
    assert item_node.get_value("2020") == 0.0


def test_item_node_has_value_existing_period(item_node: FinancialStatementItemNode):
    """Test has_value returns True for an existing period."""
    assert item_node.has_value("2022") is True
    assert item_node.has_value("2024") is True


def test_item_node_has_value_non_existing_period(item_node: FinancialStatementItemNode):
    """Test has_value returns False for a non-existing period."""
    assert item_node.has_value("2021") is False


def test_item_node_set_value_new_period(item_node: FinancialStatementItemNode):
    """Test set_value adds a value for a new period."""
    assert not item_node.has_value("2025")
    item_node.set_value("2025", 200.0)
    assert item_node.has_value("2025") is True
    assert item_node.get_value("2025") == 200.0
    assert item_node.calculate("2025") == 200.0


def test_item_node_set_value_existing_period(item_node: FinancialStatementItemNode):
    """Test set_value updates the value for an existing period."""
    assert item_node.get_value("2022") == 100.0
    item_node.set_value("2022", 110.0)
    assert item_node.get_value("2022") == 110.0
    assert item_node.calculate("2022") == 110.0


def test_item_node_has_calculation_override(item_node: FinancialStatementItemNode):
    """Test that FinancialStatementItemNode overrides has_calculation (implicitly via calculate)."""
    # While FinancialStatementItemNode doesn't explicitly override has_calculation to True,
    # its purpose is tied to providing values through calculate().
    # The base Node.has_calculation defaults to False. Let's check if this node
    # behaves as expected (provides value via calculate, might not need override).
    # Revisit if a specific `has_calculation=True` is needed for this type.
    assert item_node.has_calculation() is False  # Default from Base


# Add tests for edge cases if necessary, e.g., empty initial values dict.
def test_item_node_init_empty_values():
    """Test initialization with an empty values dictionary."""
    node = FinancialStatementItemNode(name="EmptyNode", values={})
    assert node.name == "EmptyNode"
    assert node.values == {}
    assert node.has_value("2023") is False
    assert node.get_value("2023") == 0.0
    assert node.calculate("2023") == 0.0
