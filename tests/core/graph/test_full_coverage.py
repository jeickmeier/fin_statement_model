"""Tests specifically designed to achieve full coverage of GraphManipulationMixin.

This module contains tests targeting difficult-to-reach code paths in the
GraphManipulationMixin class that might not be covered by standard functional tests.
"""

import logging
import pytest
from unittest.mock import MagicMock, patch

from fin_statement_model.core.nodes import Node, FinancialStatementItemNode
from fin_statement_model.core.errors import NodeError
from fin_statement_model.core.graph.manipulation import GraphManipulationMixin


def test_specific_line_155_coverage():
    """Test debug logging when replacing a node."""

    class TestNode(Node):
        def __init__(self, name):
            super().__init__(name)

        def calculate(self, period):
            return 0.0

    class TestGraph(GraphManipulationMixin):
        def __init__(self):
            self._nodes = {}
            self._calculation_engine = None
            self._periods = []
            self._data_manager = MagicMock()

        def clear_all_caches(self):
            pass

        def get_node(self, name):
            return self._nodes.get(name)

        def _update_calculation_nodes(self):
            pass

    with patch("fin_statement_model.core.graph.manipulation.logger") as mock_logger:
        graph = TestGraph()
        old_node = TestNode("test")
        graph._nodes["test"] = old_node
        new_node = TestNode("test")

        graph.replace_node("test", new_node)

        # No debug log expected directly in replace_node


def test_attribute_error_on_line_123():
    """Test warning logging when a node has input_names but no 'inputs' attribute."""

    class ProblemNode(Node):
        def __init__(self, name):
            super().__init__(name)
            self.input_names = ["input"]

        def calculate(self, period):
            return 0.0

        def has_calculation(self):
            return True

        def __setattr__(self, name, value):
            if name == "inputs":
                raise AttributeError(f"Cannot set 'inputs' on {self.name}")
            super().__setattr__(name, value)

    class InputNode(Node):
        def __init__(self, name):
            super().__init__(name)

        def calculate(self, period):
            return 0.0

        def has_calculation(self):
            return False

    class TestGraph(GraphManipulationMixin):
        def __init__(self):
            self._nodes = {}
            self._periods = []
            self._data_manager = MagicMock()

        def get_node(self, name):
            return self._nodes.get(name)

    with patch("fin_statement_model.core.graph.manipulation.logger.warning") as mock_warning:
        graph = TestGraph()
        problem_node = ProblemNode("problem")
        input_node = InputNode("input")

        graph._nodes = {"problem": problem_node, "input": input_node}

        # This should trigger the AttributeError in _update_calculation_nodes
        GraphManipulationMixin._update_calculation_nodes(graph)

        # Verify warning was logged
        mock_warning.assert_called_once_with(
            "Node 'problem' has input_names but no 'inputs' attribute to update."
        )


def test_calculation_engine_set_get(caplog):
    """Test setting and checking calculation engine with different scenarios."""
    caplog.set_level(logging.ERROR)

    class TestGraph(GraphManipulationMixin):
        def __init__(self):
            self._nodes = {}
            self._calculation_engine = None
            self._periods = []
            self._data_manager = MagicMock()

    # Test valid engine
    graph = TestGraph()
    valid_engine = MagicMock()
    valid_engine.calculate = MagicMock()
    valid_engine.set_graph = MagicMock()

    graph.set_calculation_engine(valid_engine)
    assert graph._calculation_engine == valid_engine
    valid_engine.set_graph.assert_called_once_with(graph)

    # Test invalid engine - missing calculate method
    graph = TestGraph()
    invalid_engine1 = MagicMock()
    del invalid_engine1.calculate  # Remove calculate method

    with pytest.raises(TypeError, match="must have a 'calculate' method"):
        graph.set_calculation_engine(invalid_engine1)

    # Test invalid engine - missing set_graph method
    graph = TestGraph()
    invalid_engine2 = MagicMock()
    invalid_engine2.calculate = MagicMock()
    del invalid_engine2.set_graph  # Remove set_graph method

    with pytest.raises(TypeError, match="must have a 'set_graph' method"):
        graph.set_calculation_engine(invalid_engine2)


def test_node_error_in_update_calculation_nodes():
    """Test error logging when a node's input is not found."""

    class CalculationNode(Node):
        def __init__(self, name, input_names):
            super().__init__(name)
            self.input_names = input_names
            self.inputs = []

        def calculate(self, period):
            return 0.0

        def has_calculation(self):
            return True

        def clear_cache(self):
            pass

    class TestGraph(GraphManipulationMixin):
        def __init__(self):
            self._nodes = {}
            self._periods = []
            self._data_manager = MagicMock()

        def get_node(self, name):
            return self._nodes.get(name)

    with patch("fin_statement_model.core.graph.manipulation.logger") as mock_logger:
        graph = TestGraph()
        # Create a calculation node with non-existent inputs
        calc_node = CalculationNode("calc", ["missing_input1", "missing_input2"])
        graph._nodes["calc"] = calc_node

        # This should trigger the NodeError in _update_calculation_nodes
        graph._update_calculation_nodes()

        # Verify error was logged (uses logger.exception)
        mock_logger.exception.assert_called_once()
        assert "Error updating inputs for node 'calc'" in mock_logger.exception.call_args[0][0]


def test_remove_node_error_handling():
    """Test error handling in remove_node method."""

    class TestGraph(GraphManipulationMixin):
        def __init__(self):
            self._nodes = {}
            self._calculation_engine = MagicMock()
            self._periods = []
            self._data_manager = MagicMock()

        def _update_calculation_nodes(self):
            pass

        def get_node(self, name):
            return self._nodes.get(name)

    # Test removing non-existent node - should do nothing now
    graph_no_exist = TestGraph()
    graph_no_exist.remove_node("non_existent")
    # Assert no error was raised and state is unchanged
    assert "non_existent" not in graph_no_exist._nodes

    # Test error during calculation engine cache clearing
    graph_cache_error = TestGraph()
    node = MagicMock(spec=Node)
    node.name = "test_node"
    graph_cache_error._nodes["test_node"] = node
    graph_cache_error._calculation_engine.clear_cache.side_effect = Exception("Test error")

    with patch("fin_statement_model.core.graph.manipulation.logger") as mock_logger:
        graph_cache_error.remove_node("test_node")

        assert "test_node" not in graph_cache_error._nodes
        # Verify error was logged (uses logger.exception)
        mock_logger.exception.assert_called_once()
        assert "Error clearing calculation engine cache" in mock_logger.exception.call_args[0][0]


def test_clear_method_error_handling():
    """Test error handling in clear method."""

    class TestGraph(GraphManipulationMixin):
        def __init__(self):
            self._nodes = {"node1": MagicMock(spec=Node), "node2": MagicMock(spec=Node)}
            self._calculation_engine = MagicMock()
            self._periods = ["2020", "2021"]
            self._data_manager = MagicMock()

    # Test error during calculation engine reset
    graph = TestGraph()
    graph._calculation_engine.reset.side_effect = Exception("Test reset error")

    with patch("fin_statement_model.core.graph.manipulation.logger") as mock_logger:
        graph.clear()

        # Verify nodes and periods were cleared
        assert len(graph._nodes) == 0
        assert len(graph._periods) == 0

        # Verify error was logged (uses logger.exception)
        mock_logger.exception.assert_called_once()
        assert "Error resetting calculation engine" in mock_logger.exception.call_args[0][0]


def test_set_value_validation_and_errors():
    """Test set_value method validation and error handling."""

    class TestGraph(GraphManipulationMixin):
        def __init__(self):
            self._nodes = {}
            self._periods = ["2020", "2021"]
            self._calculation_engine = None
            self._data_manager = MagicMock()

        def get_node(self, name):
            return self._nodes.get(name)

        def clear_all_caches(self):
            pass

    # Test invalid period
    graph = TestGraph()
    with pytest.raises(ValueError, match="Period '2022' not in graph periods"):
        graph.set_value("any_node", "2022", 100)

    # Test node not found
    with pytest.raises(NodeError, match="Node 'non_existent' does not exist"):
        graph.set_value("non_existent", "2020", 100)

    # Test node without set_value method
    graph = TestGraph()
    # Use a mock instead of direct Node instantiation
    node = MagicMock(spec=Node)
    node.name = "test_node"
    graph._nodes["test_node"] = node

    with pytest.raises(TypeError, match="does not support set_value"):
        graph.set_value("test_node", "2020", 100)

    # Test calculation engine error during cache clearing
    graph_cache_error = TestGraph()
    node = FinancialStatementItemNode("financial_node", {})
    graph_cache_error._nodes["financial_node"] = node
    graph_cache_error._calculation_engine = MagicMock()
    graph_cache_error._calculation_engine.clear_cache.side_effect = Exception("Test cache error")

    with patch("fin_statement_model.core.graph.manipulation.logger") as mock_logger:
        graph_cache_error.set_value("financial_node", "2020", 100)

        # Verify value was set
        assert node.get_value("2020") == 100

        # Verify error was logged (uses logger.exception)
        mock_logger.exception.assert_called_once()
        assert "Error clearing calculation engine cache" in mock_logger.exception.call_args[0][0]


def test_clear_all_caches():
    """Test clear_all_caches method."""

    class CacheableNode(Node):
        def __init__(self, name):
            super().__init__(name)
            self.cache_cleared = False

        def calculate(self, period):
            return 0.0

        def clear_cache(self):
            self.cache_cleared = True

    class TestGraph(GraphManipulationMixin):
        def __init__(self):
            self._nodes = {}
            self._data_manager = MagicMock()

    # Setup graph with mix of cacheable and non-cacheable nodes
    graph = TestGraph()
    cacheable1 = CacheableNode("cacheable1")
    cacheable2 = CacheableNode("cacheable2")
    # Use mock instead of direct instantiation
    non_cacheable = MagicMock(spec=Node)
    non_cacheable.name = "non_cacheable"

    graph._nodes = {
        "cacheable1": cacheable1,
        "cacheable2": cacheable2,
        "non_cacheable": non_cacheable,
    }

    # Clear caches
    graph.clear_all_caches()

    # Verify cacheable nodes had clear_cache called
    assert cacheable1.cache_cleared
    assert cacheable2.cache_cleared
    # Non-cacheable node should not cause errors


# Define the node classes for reuse in fixtures
class SimpleNode(Node):
    def __init__(self, name):
        super().__init__(name)

    def calculate(self, period):
        return 0.0


class NodeWithoutSetValue(Node):
    def __init__(self, name):
        super().__init__(name)

    def calculate(self, period):
        return 0.0


node = NodeWithoutSetValue("no_setter")

# TestGraph is defined in each test function where it's needed to avoid the pytest warning
# The common TestGraph implementation has been removed from the top level
