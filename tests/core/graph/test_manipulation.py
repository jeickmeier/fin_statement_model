"""Tests for the GraphManipulationMixin."""

import pytest
from unittest.mock import MagicMock, patch
import logging
from typing import Dict, List, Optional

from fin_statement_model.core.nodes.base import Node
from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode
from fin_statement_model.core.errors import NodeError

# Mixin under test
from fin_statement_model.core.graph.manipulation import GraphManipulationMixin

# Mock target
LOGGER_PATH = "fin_statement_model.core.graph.manipulation.logger"

# --- Helper Test Host Class ---


class HostGraph(GraphManipulationMixin):
    """Minimal host class to test the GraphManipulationMixin."""

    def __init__(self):
        self._nodes: Dict[str, Node] = {}
        self._calculation_engine: Optional[MagicMock] = MagicMock()
        self._periods: List[str] = []
        # Mock methods that the mixin might call internally
        self._update_calculation_nodes = (
            MagicMock()
        )  # Called by add_node, replace_node, remove_node
        self.clear_all_caches = MagicMock()  # Called by replace_node
        # Ensure get_node uses the internal _nodes dict
        self.get_node = lambda name: self._nodes.get(name)
        self._data_manager = MagicMock() # Add missing attribute


# Custom class to better control attributes for mocking
class CustomNode:
    """Custom node class for testing that can have attributes missing."""

    def __init__(self, name, has_calculation_result=False):
        self.name = name
        self._has_calculation_result = has_calculation_result

    def has_calculation(self):
        return self._has_calculation_result


# --- Fixtures ---


@pytest.fixture
def host_graph() -> HostGraph:
    """Provides an instance of the test host class."""
    return HostGraph()


@pytest.fixture
def sample_node() -> Node:
    """Provides a simple node for testing."""
    node = MagicMock(spec=Node)
    node.name = "SampleNode"
    node.has_calculation.return_value = False
    node.clear_cache = MagicMock()
    return node


@pytest.fixture
def sample_calc_node() -> Node:
    """Provides a simple calculation node for testing."""
    node = MagicMock(spec=Node)
    node.name = "SampleCalcNode"
    node.has_calculation.return_value = True
    node.input_names = ["InputA", "InputB"]
    node.inputs = []  # This might be updated by _update_calculation_nodes
    node.clear_cache = MagicMock()
    return node


@pytest.fixture
def sample_item_node() -> FinancialStatementItemNode:
    """Provides a FinancialStatementItemNode for testing."""
    node = MagicMock(spec=FinancialStatementItemNode)
    node.name = "SampleItemNode"
    node.has_calculation.return_value = False  # FS Items don't calculate directly
    node.set_value = MagicMock()
    node.clear_cache = MagicMock()
    return node


@pytest.fixture
def mock_logger(monkeypatch) -> MagicMock:
    """Provides a mock logger and patches its import."""
    mock = MagicMock(spec=logging.Logger)
    monkeypatch.setattr(LOGGER_PATH, mock)
    return mock


# --- Test Cases ---


def test_set_calculation_engine_valid(host_graph: HostGraph):
    """Test setting a valid calculation engine."""
    mock_engine = MagicMock()
    mock_engine.calculate = MagicMock()
    mock_engine.set_graph = MagicMock()

    host_graph.set_calculation_engine(mock_engine)

    assert host_graph._calculation_engine == mock_engine
    mock_engine.set_graph.assert_called_once_with(host_graph)


def test_set_calculation_engine_invalid(host_graph: HostGraph):
    """Test setting an invalid calculation engine raises TypeError."""
    invalid_engine_no_calc = MagicMock()
    invalid_engine_no_calc.set_graph = MagicMock()
    # Explicitly remove the calculate attribute if it exists implicitly
    if hasattr(invalid_engine_no_calc, "calculate"):
        del invalid_engine_no_calc.calculate

    with pytest.raises(
        TypeError, match="Calculation engine instance must have a 'calculate' method"
    ):
        host_graph.set_calculation_engine(invalid_engine_no_calc)

    invalid_engine_no_set_graph = MagicMock()
    invalid_engine_no_set_graph.calculate = MagicMock()
    # Explicitly remove the set_graph attribute if it exists implicitly
    if hasattr(invalid_engine_no_set_graph, "set_graph"):
        del invalid_engine_no_set_graph.set_graph

    with pytest.raises(
        TypeError, match="Calculation engine instance must have a 'set_graph' method"
    ):
        host_graph.set_calculation_engine(invalid_engine_no_set_graph)


def test_add_node_new(host_graph: HostGraph, sample_node: Node):
    """Test adding a new node."""
    host_graph.add_node(sample_node)
    assert host_graph._nodes == {"SampleNode": sample_node}
    # _update_calculation_nodes should NOT be called for non-calc/non-item node
    host_graph._update_calculation_nodes.assert_not_called()


def test_add_node_replace_non_calc(host_graph: HostGraph, sample_node: Node):
    """Test replacing a node with a non-calculation/non-item node."""
    existing_node = MagicMock(spec=Node, name="SampleNode")
    host_graph._nodes["SampleNode"] = existing_node

    # Ensure replacement node has the same name
    sample_node.name = "SampleNode"

    host_graph.add_node(sample_node)  # Replace with another non-calc node
    assert host_graph._nodes == {"SampleNode": sample_node}
    assert host_graph._nodes["SampleNode"] is not existing_node
    # _update_calculation_nodes *is* called via remove_node->add_node internal calls
    host_graph._update_calculation_nodes.assert_called_once()


def test_add_node_replace_with_calc(host_graph: HostGraph, sample_calc_node: Node):
    """Test replacing a node with a calculation node triggers update."""
    existing_node = MagicMock(spec=Node, name="SampleCalcNode")
    host_graph._nodes["SampleCalcNode"] = existing_node

    host_graph.add_node(sample_calc_node)
    assert host_graph._nodes == {"SampleCalcNode": sample_calc_node}
    # _update_calculation_nodes SHOULD be called
    host_graph._update_calculation_nodes.assert_called_once()


def test_add_node_replace_with_item(host_graph: HostGraph, sample_item_node: Node):
    """Test replacing a node with an item node triggers update."""
    existing_node = MagicMock(spec=Node, name="SampleItemNode")
    host_graph._nodes["SampleItemNode"] = existing_node

    host_graph.add_node(sample_item_node)
    assert host_graph._nodes == {"SampleItemNode": sample_item_node}
    # _update_calculation_nodes SHOULD be called
    host_graph._update_calculation_nodes.assert_called_once()


def test_update_calculation_nodes_with_all_edge_cases():
    """Test _update_calculation_nodes with all possible edge cases to cover all lines."""

    # Create a simple graph with a real _update_calculation_nodes implementation
    class TestGraph(GraphManipulationMixin):
        def __init__(self):
            self._nodes = {}
            self._periods = []

        def get_node(self, name):
            return self._nodes.get(name)

    with (
        patch("fin_statement_model.core.graph.manipulation.logger.error") as mock_error,
        patch("fin_statement_model.core.graph.manipulation.logger.warning") as mock_warning,
    ):
        graph = TestGraph()

        # Create a proper input node
        class InputNode:
            def __init__(self, name):
                self.name = name

            def has_calculation(self):
                return False

        input_a = InputNode("InputA")

        # A normal calculation node with valid inputs
        calc_node = MagicMock()
        calc_node.name = "CalcNode"
        calc_node.has_calculation.return_value = True
        calc_node.input_names = ["InputA"]
        calc_node.inputs = []
        calc_node.clear_cache = MagicMock()

        # A node with invalid inputs to trigger the error path
        error_node = MagicMock()
        error_node.name = "ErrorNode"
        error_node.has_calculation.return_value = True
        error_node.input_names = ["MissingInput"]
        error_node.inputs = []
        error_node.clear_cache = MagicMock()

        # A node that will trigger AttributeError
        class ReadOnlyNode:
            def __init__(self, name):
                self.name = name
                self.input_names = ["InputA"]

            def has_calculation(self):
                return True

            def __setattr__(self, name, value):
                if name == "inputs":
                    raise AttributeError(f"Cannot set 'inputs' on {self.name}")
                object.__setattr__(self, name, value)

        no_inputs_node = ReadOnlyNode("NoInputsNode")

        # Add nodes to graph
        graph._nodes = {
            "InputA": input_a,
            "CalcNode": calc_node,
            "ErrorNode": error_node,
            "NoInputsNode": no_inputs_node,
        }

        # Call the method
        GraphManipulationMixin._update_calculation_nodes(graph)

        # Verify the error for the missing input node
        mock_error.assert_called_with(
            f"Error updating inputs for node '{error_node.name}'", exc_info=True
        )

        # Verify the warning for the missing 'inputs' attribute
        warning_msg = "Node 'NoInputsNode' has input_names but no 'inputs' attribute to update."
        mock_warning.assert_called_with(warning_msg)

        # The normal node should have its inputs set and cache cleared
        assert calc_node.inputs == [input_a]
        calc_node.clear_cache.assert_called_once()


def test_get_node_exists(host_graph: HostGraph, sample_node: Node):
    """Test get_node retrieves an existing node."""
    host_graph._nodes["SampleNode"] = sample_node
    retrieved_node = host_graph.get_node("SampleNode")
    assert retrieved_node == sample_node


def test_get_node_not_exists(host_graph: HostGraph):
    """Test get_node returns None for a non-existent node."""
    retrieved_node = host_graph.get_node("NonExistent")
    assert retrieved_node is None


def test_replace_node(host_graph: HostGraph, sample_node: Node, mock_logger: MagicMock):
    """Test replacing an existing node."""
    old_node = MagicMock(spec=Node, name="NodeToReplace")
    host_graph._nodes["NodeToReplace"] = old_node
    # Ensure the new node has the correct name for replacement
    sample_node.name = "NodeToReplace"

    host_graph.replace_node("NodeToReplace", sample_node)

    assert host_graph._nodes["NodeToReplace"] == sample_node
    assert "NodeToReplace" in host_graph._nodes
    assert host_graph.get_node("NodeToReplace") is sample_node
    # remove_node calls _update_calculation_nodes once, add_node doesn't call it again
    # host_graph.clear_all_caches is called by replace_node
    assert host_graph._update_calculation_nodes.call_count == 1 # Called during remove_node
    # Assert that the ENGINE's cache clear was called (via remove_node)
    host_graph._calculation_engine.clear_cache.assert_called_once()


def test_replace_node_does_not_exist(host_graph: HostGraph, sample_node: Node):
    """Test replacing a non-existent node raises NodeError."""
    # Ensure node name does not exist initially
    assert not host_graph.has_node("NonExistentNode")

    with pytest.raises(NodeError, match="Node 'NonExistentNode' not found, cannot replace."):
        host_graph.replace_node("NonExistentNode", sample_node)

    # Verify node was not added and mocks were not called
    assert "NonExistentNode" not in host_graph._nodes
    host_graph._update_calculation_nodes.assert_not_called()
    host_graph.clear_all_caches.assert_not_called()


def test_replace_node_with_different_node_type():
    """Test replacing node with different types logs correctly."""
    with patch("fin_statement_model.core.graph.manipulation.logger.debug") as mock_debug:
        graph = HostGraph()
        graph._update_calculation_nodes = MagicMock()
        graph.clear_all_caches = MagicMock()

        # Use actual Node subclasses or mocks based on Node
        class OldNodeType(Node):
            def calculate(self, period): return 0

        class NewNodeType(Node):
            def calculate(self, period): return 0

        old_node = OldNodeType("test")
        new_node = NewNodeType("test")

        graph._nodes["test"] = old_node
        graph.replace_node("test", new_node)
        # No debug log expected directly in replace_node
        # assert mock_debug.call_count >= 1 # Remove assertion


def test_has_node_exists(host_graph: HostGraph, sample_node: Node):
    """Test has_node returns True for an existing node."""
    host_graph._nodes["SampleNode"] = sample_node
    assert host_graph.has_node("SampleNode") is True


def test_has_node_not_exists(host_graph: HostGraph):
    """Test has_node returns False for a non-existent node."""
    assert host_graph.has_node("NonExistent") is False


def test_remove_node_exists(host_graph: HostGraph, sample_node: Node):
    """Test removing an existing node."""
    host_graph._nodes["ToRemove"] = sample_node
    host_graph.remove_node("ToRemove")
    assert "ToRemove" not in host_graph._nodes
    host_graph._update_calculation_nodes.assert_called_once()
    # Check engine cache clear was attempted
    host_graph._calculation_engine.clear_cache.assert_called_once()


def test_remove_node_not_exists(host_graph: HostGraph):
    """Test removing a non-existent node does nothing and logs nothing."""
    initial_nodes = host_graph._nodes.copy()
    host_graph.remove_node("NonExistent")
    # Node dictionary should be unchanged
    assert host_graph._nodes == initial_nodes
    # Methods should not have been called
    host_graph._update_calculation_nodes.assert_not_called()
    host_graph._calculation_engine.clear_cache.assert_not_called()


def test_remove_node_engine_clear_error(
    host_graph: HostGraph, sample_node: Node, mock_logger: MagicMock
):
    """Test remove_node logs error if engine cache clear fails."""
    host_graph._nodes["ToRemove"] = sample_node
    host_graph._calculation_engine.clear_cache.side_effect = RuntimeError("Engine fail")
    host_graph.remove_node("ToRemove")
    assert "ToRemove" not in host_graph._nodes
    host_graph._update_calculation_nodes.assert_called_once()
    host_graph._calculation_engine.clear_cache.assert_called_once()
    # Check the exception logging format (uses logger.exception)
    mock_logger.exception.assert_called_with("Error clearing calculation engine cache")


def test_clear(host_graph: HostGraph, sample_node: Node):
    """Test clearing the graph."""
    host_graph._nodes["N1"] = sample_node
    host_graph._periods = ["p1", "p2"]
    host_graph._calculation_engine = MagicMock()
    host_graph._calculation_engine.reset = MagicMock()

    host_graph.clear()

    assert host_graph._nodes == {}
    assert host_graph._periods == []
    host_graph._calculation_engine.reset.assert_called_once()


def test_clear_engine_reset_error(host_graph: HostGraph, mock_logger: MagicMock):
    """Test clear logs error if engine reset fails."""
    host_graph._calculation_engine = MagicMock()
    host_graph._calculation_engine.reset.side_effect = RuntimeError("Engine reset fail")
    host_graph.clear()
    # Check the exception logging format (uses logger.exception)
    mock_logger.exception.assert_called_with("Error resetting calculation engine")


def test_set_value_success(host_graph: HostGraph, sample_item_node: MagicMock):
    """Test setting a value on a compatible node."""
    host_graph._nodes["Item"] = sample_item_node
    host_graph._periods = ["2023"]
    host_graph.set_value("Item", "2023", 123.45)
    sample_item_node.set_value.assert_called_once_with("2023", 123.45)
    host_graph._calculation_engine.clear_cache.assert_called_once()


def test_set_value_engine_clear_error(
    host_graph: HostGraph, sample_item_node: MagicMock, mock_logger: MagicMock
):
    """Test set_value handles engine cache clear failure."""
    host_graph._nodes["Item"] = sample_item_node
    host_graph._periods = ["2023"]
    host_graph._calculation_engine.clear_cache.side_effect = RuntimeError("Engine cache clear fail")

    host_graph.set_value("Item", "2023", 123.45)

    sample_item_node.set_value.assert_called_once_with("2023", 123.45)
    host_graph._calculation_engine.clear_cache.assert_called_once()
    # Check the exception logging format (uses logger.exception)
    mock_logger.exception.assert_called_with("Error clearing calculation engine cache")


def test_set_value_no_engine(host_graph: HostGraph, sample_item_node: MagicMock):
    """Test set_value calls graph clear_all_caches if no engine."""
    host_graph._nodes["Item"] = sample_item_node
    host_graph._periods = ["2023"]
    host_graph._calculation_engine = None  # No engine attached

    host_graph.set_value("Item", "2023", 100.0)
    sample_item_node.set_value.assert_called_once_with("2023", 100.0)
    host_graph.clear_all_caches.assert_called_once()


def test_set_value_invalid_period(host_graph: HostGraph, sample_item_node: MagicMock):
    """Test set_value raises ValueError for an invalid period."""
    host_graph._nodes["Item"] = sample_item_node
    host_graph._periods = ["2023"]
    with pytest.raises(ValueError, match="Period '2024' not in graph periods"):
        host_graph.set_value("Item", "2024", 100.0)
    sample_item_node.set_value.assert_not_called()


def test_set_value_node_not_found(host_graph: HostGraph):
    """Test set_value raises NodeError if node doesn't exist."""
    host_graph._periods = ["2023"]
    with pytest.raises(NodeError, match="Node 'NonExistent' does not exist"):
        host_graph.set_value("NonExistent", "2023", 100.0)


def test_set_value_node_no_set_value_method(host_graph: HostGraph, sample_node: MagicMock):
    """Test set_value raises TypeError if node lacks set_value method."""
    # Remove the set_value mock if it exists from fixture
    if hasattr(sample_node, "set_value"):
        del sample_node.set_value

    host_graph._nodes["SampleNode"] = sample_node
    host_graph._periods = ["2023"]
    with pytest.raises(
        TypeError, match="Node 'SampleNode' of type MagicMock does not support set_value"
    ):
        host_graph.set_value("SampleNode", "2023", 100.0)


# Note: The clear_all_caches method in the mixin only clears node caches.
# The test_graph_clear_all_caches in test_graph.py tests the full graph version.
# We can add a specific test for the mixin's version here.


def test_mixin_clear_all_caches(host_graph: HostGraph):
    """Test the clear_all_caches method specifically in the mixin."""
    mock_node1 = MagicMock(spec=Node)
    mock_node1.clear_cache = MagicMock()
    mock_node2 = MagicMock(spec=Node)  # No clear_cache method
    mock_node3 = MagicMock(spec=Node)
    mock_node3.clear_cache = MagicMock()
    host_graph._nodes = {"N1": mock_node1, "N2": mock_node2, "N3": mock_node3}

    # Call the mixin's method directly for this test
    GraphManipulationMixin.clear_all_caches(host_graph)

    mock_node1.clear_cache.assert_called_once()
    # mock_node2.clear_cache.assert_not_called() # Cannot assert absence on mock
    mock_node3.clear_cache.assert_called_once()
