"""Tests for the Node abstract base class."""

import pytest
from fin_statement_model.core.nodes.base import Node


# --- Fixtures ---
class ConcreteNode(Node):
    """Minimal concrete implementation for testing Node."""

    def calculate(self, period: str) -> float:
        """Simple calculation for testing."""
        # Example calculation, could be anything
        return float(len(self.name) + len(period))

    # Override methods that would otherwise raise NotImplementedError if needed
    # for specific tests, or provide default implementations.


@pytest.fixture
def concrete_node() -> ConcreteNode:
    """Provides a concrete node instance for testing."""
    return ConcreteNode(name="TestNode")


# --- Test Cases ---


def test_node_init_success(concrete_node: ConcreteNode):
    """Test successful initialization of a Node subclass."""
    assert concrete_node.name == "TestNode"


@pytest.mark.parametrize(
    "invalid_name",
    [
        "",  # Empty string
        None,  # None value
        123,  # Integer
        [],  # List
    ],
)
def test_node_init_invalid_name(invalid_name):
    """Test Node initialization raises ValueError for invalid names."""
    with pytest.raises(ValueError, match="Node name must be a non-empty string."):
        ConcreteNode(name=invalid_name)


def test_node_calculate(concrete_node: ConcreteNode):
    """Test the calculate method of the concrete implementation."""
    assert concrete_node.calculate(period="2023") == 12.0  # len("TestNode") + len("2023") = 8 + 4


def test_node_clear_cache(concrete_node: ConcreteNode):
    """Test the default clear_cache method runs without error."""
    try:
        concrete_node.clear_cache()
    except Exception as e:
        pytest.fail(f"clear_cache raised an unexpected exception: {e}")


def test_node_has_attribute(concrete_node: ConcreteNode):
    """Test the has_attribute method."""
    assert concrete_node.has_attribute("name") is True
    assert concrete_node.has_attribute("calculate") is True
    assert concrete_node.has_attribute("non_existent_attr") is False


def test_node_get_attribute(concrete_node: ConcreteNode):
    """Test the get_attribute method."""
    assert concrete_node.get_attribute("name") == "TestNode"
    assert callable(concrete_node.get_attribute("calculate"))


def test_node_get_attribute_error(concrete_node: ConcreteNode):
    """Test get_attribute raises AttributeError for non-existent attributes."""
    with pytest.raises(
        AttributeError, match="Node 'TestNode' has no attribute 'non_existent_attr'"
    ):
        concrete_node.get_attribute("non_existent_attr")


def test_node_has_value_default(concrete_node: ConcreteNode):
    """Test the default has_value method returns False."""
    assert concrete_node.has_value(period="2023") is False


def test_node_get_value_default(concrete_node: ConcreteNode):
    """Test the default get_value method raises NotImplementedError."""
    with pytest.raises(NotImplementedError, match="Node TestNode does not implement get_value"):
        concrete_node.get_value(period="2023")


def test_node_has_calculation_default(concrete_node: ConcreteNode):
    """Test the default has_calculation method returns False."""
    assert concrete_node.has_calculation() is False
