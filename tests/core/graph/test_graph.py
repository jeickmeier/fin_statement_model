"""Tests for the core Graph class."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import logging

# Assuming Node and FinancialStatementItemNode are importable for type checking/isinstance
from fin_statement_model.core.nodes.base import Node
from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode

# Class under test
from fin_statement_model.core.graph.graph import Graph

# Mock targets
DATA_MANAGER_PATH = "fin_statement_model.core.graph.graph.DataManager"
CALC_ENGINE_PATH = "fin_statement_model.core.graph.graph.CalculationEngine"
LOGGER_PATH = "fin_statement_model.core.graph.graph.logger"

# --- Fixtures ---


@pytest.fixture
def mock_data_manager(monkeypatch) -> tuple[MagicMock, MagicMock]:
    """Provides a mock DataManager instance and patches its import."""
    mock = MagicMock()
    # Use PropertyMock for periods to allow setting in tests
    # However, simpler to just configure the return value directly
    type(mock).periods = PropertyMock(
        return_value=["2022", "2023"]
    )  # Make periods a settable property mock
    mock.add_periods.return_value = None
    mock.add_item.side_effect = lambda name, vals: FinancialStatementItemNode(name, vals)
    # Store call args for verification
    manager_class_mock = MagicMock(return_value=mock)
    monkeypatch.setattr(DATA_MANAGER_PATH, manager_class_mock)
    # Return the instance mock and the class mock for checking calls
    return mock, manager_class_mock


@pytest.fixture
def mock_calc_engine(monkeypatch) -> tuple[MagicMock, MagicMock]:
    """Provides a mock CalculationEngine instance and patches its import."""
    mock = MagicMock()
    mock.calculate.return_value = 123.45

    # Fix side effect to return a mock node with name attribute set
    def side_effect(name, inputs, op_type, **kwargs):
        m = MagicMock(spec=Node)  # Create mock
        m.name = name  # Set name attribute
        return m

    mock.add_calculation.side_effect = side_effect
    engine_class_mock = MagicMock(return_value=mock)
    monkeypatch.setattr(CALC_ENGINE_PATH, engine_class_mock)
    return mock, engine_class_mock


@pytest.fixture
def mock_logger(monkeypatch) -> MagicMock:
    """Provides a mock logger and patches its import."""
    mock = MagicMock(spec=logging.Logger)
    monkeypatch.setattr(LOGGER_PATH, mock)
    return mock


@pytest.fixture
def sample_node() -> Node:
    """Provides a basic Node instance."""

    # Using a concrete, simple Node implementation if available, or mock
    class SimpleNode(Node):
        _has_calc = False

        def calculate(self, period: str) -> float:
            return 0.0

        def has_calculation(self) -> bool:
            return self._has_calc

        def clear_cache(self) -> None:
            pass  # Mock has clear_cache

    return SimpleNode("SampleNode")


@pytest.fixture
def sample_calc_node() -> MagicMock:
    """Provides a basic calculation Node mock instance."""
    # Add get_dependencies to the spec list
    node = MagicMock(
        spec=Node, spec_set=["name", "has_calculation", "inputs", "clear_cache", "get_dependencies"]
    )
    node.name = "SampleCalcNode"
    node.has_calculation.return_value = True
    mock_input_a = MagicMock(spec=Node, name="InputA")
    mock_input_b = MagicMock(spec=Node, name="InputB")
    node.inputs = [mock_input_a, mock_input_b]
    # Configure get_dependencies side_effect (now valid)
    node.get_dependencies.side_effect = lambda: [i.name for i in node.inputs]
    node.clear_cache = MagicMock()
    return node


# --- Test Cases ---


def test_graph_init_no_periods(
    mock_data_manager: tuple[MagicMock, MagicMock], mock_calc_engine: tuple[MagicMock, MagicMock]
):
    """Test Graph initialization without initial periods."""
    instance_mock_dm, class_mock_dm = mock_data_manager
    instance_mock_ce, class_mock_ce = mock_calc_engine

    graph = Graph()
    assert isinstance(graph._nodes, dict)
    assert len(graph._nodes) == 0
    assert graph._data_manager == instance_mock_dm
    assert graph._calculation_engine == instance_mock_ce
    # Check managers received the shared node registry via constructor args
    class_mock_dm.assert_called_once_with(nodes_registry=graph._nodes)
    class_mock_ce.assert_called_once_with(nodes_registry=graph._nodes)
    # Ensure add_periods was not called on manager instance
    instance_mock_dm.add_periods.assert_not_called()


def test_graph_init_with_periods(
    mock_data_manager: tuple[MagicMock, MagicMock], mock_calc_engine: tuple[MagicMock, MagicMock]
):
    """Test Graph initialization with initial periods."""
    instance_mock_dm, _ = mock_data_manager
    initial_periods = ["2023", "2022"]
    graph = Graph(periods=initial_periods)
    assert graph._data_manager == instance_mock_dm
    # Check that add_periods was called on the manager instance
    instance_mock_dm.add_periods.assert_called_once_with(initial_periods)


def test_graph_init_invalid_periods_type():
    """Test Graph initialization raises TypeError for invalid periods type."""
    with pytest.raises(TypeError, match="Initial periods must be a list"):
        Graph(periods="not_a_list")


def test_graph_nodes_property(
    mock_data_manager: tuple[MagicMock, MagicMock],
    mock_calc_engine: tuple[MagicMock, MagicMock],
    sample_node: Node,
):
    """Test the `nodes` property returns the internal node registry."""
    graph = Graph()
    # Add a valid node
    test_node = sample_node  # Use the fixture
    test_node.name = "TestNode"  # Rename for clarity
    graph._nodes["TestNode"] = test_node
    assert graph.nodes == {"TestNode": test_node}
    assert graph.nodes is graph._nodes  # Should return the same object


def test_graph_periods_property(mock_data_manager: tuple[MagicMock, MagicMock]):
    """Test the `periods` property delegates to the DataManager."""
    instance_mock_dm, _ = mock_data_manager
    expected_periods = ["p1", "p2"]
    # Configure the mock property *before* Graph instantiation
    type(instance_mock_dm).periods = PropertyMock(return_value=expected_periods)
    graph = Graph()
    assert graph.periods == expected_periods


def test_graph_add_periods(mock_data_manager: tuple[MagicMock, MagicMock]):
    """Test `add_periods` delegates to the DataManager."""
    instance_mock_dm, _ = mock_data_manager
    graph = Graph()
    new_periods = ["2024", "2025"]
    graph.add_periods(new_periods)
    # Should call the manager's method (init call doesn't count here)
    instance_mock_dm.add_periods.assert_called_once_with(new_periods)


def test_graph_add_periods_invalid_type(mock_data_manager: tuple[MagicMock, MagicMock]):
    """Test `add_periods` delegates type validation (mocked here)."""
    instance_mock_dm, _ = mock_data_manager
    graph = Graph()
    instance_mock_dm.add_periods.side_effect = TypeError("Periods must be provided as a list.")
    with pytest.raises(TypeError, match="Periods must be provided as a list."):
        graph.add_periods("not_a_list")
    instance_mock_dm.add_periods.assert_called_once_with("not_a_list")


def test_graph_add_calculation(mock_calc_engine: tuple[MagicMock, MagicMock]):
    """Test `add_calculation` delegates to the CalculationEngine."""
    instance_mock_ce, _ = mock_calc_engine
    graph = Graph()
    node = graph.add_calculation("Calc1", ["InputA"], "addition", param1=10)
    instance_mock_ce.add_calculation.assert_called_once_with(
        "Calc1", ["InputA"], "addition", param1=10
    )
    # Check the name attribute exists and is correct
    assert node.name == "Calc1"
    assert isinstance(node, MagicMock)


def test_graph_calculate(mock_calc_engine: tuple[MagicMock, MagicMock]):
    """Test `calculate` delegates to the CalculationEngine."""
    instance_mock_ce, _ = mock_calc_engine
    graph = Graph()
    result = graph.calculate("NodeX", "2023")
    instance_mock_ce.calculate.assert_called_once_with("NodeX", "2023")
    assert result == 123.45  # Return value from mock engine


def test_graph_recalculate_all_no_periods(
    mock_calc_engine: tuple[MagicMock, MagicMock], mock_data_manager: tuple[MagicMock, MagicMock]
):
    """Test `recalculate_all` with no periods specified (uses all periods)."""
    instance_mock_ce, _ = mock_calc_engine
    graph = Graph()  # Uses mock_data_manager implicitly for periods
    with patch.object(graph, "clear_all_caches") as mock_clear:
        graph.recalculate_all()
        mock_clear.assert_called_once()
        instance_mock_ce.recalculate_all.assert_called_once_with(mock_data_manager[0].periods)


def test_graph_recalculate_all_single_period(mock_calc_engine: tuple[MagicMock, MagicMock]):
    """Test `recalculate_all` with a single period string."""
    instance_mock_ce, _ = mock_calc_engine
    graph = Graph()
    with patch.object(graph, "clear_all_caches") as mock_clear:
        graph.recalculate_all("2023")
        mock_clear.assert_called_once()
        instance_mock_ce.recalculate_all.assert_called_once_with(["2023"])


def test_graph_recalculate_all_list_periods(mock_calc_engine: tuple[MagicMock, MagicMock]):
    """Test `recalculate_all` with a list of periods."""
    instance_mock_ce, _ = mock_calc_engine
    graph = Graph()
    periods_list = ["2023", "2024"]
    with patch.object(graph, "clear_all_caches") as mock_clear:
        graph.recalculate_all(periods_list)
        mock_clear.assert_called_once()
        instance_mock_ce.recalculate_all.assert_called_once_with(periods_list)


def test_graph_recalculate_all_invalid_type(mock_calc_engine: tuple[MagicMock, MagicMock]):
    """Test `recalculate_all` raises TypeError for invalid periods type."""
    instance_mock_ce, _ = mock_calc_engine
    graph = Graph()
    with pytest.raises(
        TypeError, match="Periods must be a list of strings, a single string, or None."
    ):
        graph.recalculate_all(123)


def test_graph_clear_all_caches(
    mock_calc_engine: tuple[MagicMock, MagicMock],
    mock_logger: MagicMock,
    sample_node: Node,
    sample_calc_node: Node,
):
    """Test `clear_all_caches` calls clear_cache on nodes and engine."""
    graph = Graph()
    # Use mock nodes with clear_cache methods
    mock_node1 = MagicMock(spec=Node)
    mock_node1.name = "Node1"
    mock_node1.clear_cache.return_value = None
    mock_node2 = MagicMock(spec=Node)
    mock_node2.name = "Node2"
    mock_node2.clear_cache.side_effect = RuntimeError("Cache clear failed!")  # Simulate node error
    mock_node3_no_cache = MagicMock(spec=Node)
    mock_node3_no_cache.name = "Node3"
    # del mock_node3_no_cache.clear_cache # Ensure it doesn't have the method

    graph._nodes = {"N1": mock_node1, "N2": mock_node2, "N3": mock_node3_no_cache}

    # Mock the engine's clear_cache
    instance_mock_ce, _ = mock_calc_engine
    instance_mock_ce.clear_cache.return_value = None

    graph.clear_all_caches()

    mock_node1.clear_cache.assert_called_once()
    mock_node2.clear_cache.assert_called_once()
    # mock_node3_no_cache.clear_cache.assert_not_called() # Hard to check non-existence directly

    instance_mock_ce.clear_cache.assert_called_once()

    # Check warning log for Node2 failure
    mock_logger.warning.assert_any_call(
        "Failed to clear cache for node 'Node2': Cache clear failed!"
    )


def test_graph_clear_all_caches_engine_error(
    mock_calc_engine: tuple[MagicMock, MagicMock], mock_logger: MagicMock
):
    """Test `clear_all_caches` logs warning if engine clear_cache fails."""
    instance_mock_ce, _ = mock_calc_engine
    graph = Graph()
    instance_mock_ce.clear_cache.side_effect = RuntimeError("Engine cache clear failed!")

    graph.clear_all_caches()

    instance_mock_ce.clear_cache.assert_called_once()
    mock_logger.warning.assert_any_call(
        "Could not clear calculation engine cache: Engine cache clear failed!", exc_info=True
    )


def test_graph_add_financial_statement_item(mock_data_manager: tuple[MagicMock, MagicMock]):
    """Test `add_financial_statement_item` delegates to DataManager."""
    instance_mock_dm, _ = mock_data_manager
    graph = Graph()
    item_values = {"2023": 100.0}
    node = graph.add_financial_statement_item("Revenue", item_values)
    instance_mock_dm.add_item.assert_called_once_with("Revenue", item_values)
    # Check node returned is the one from the manager
    assert isinstance(node, FinancialStatementItemNode)
    assert node.name == "Revenue"


def test_graph_get_financial_statement_items(sample_node: Node, sample_calc_node: Node):
    """Test `get_financial_statement_items` filters correctly."""
    graph = Graph()
    item_node1 = FinancialStatementItemNode("Item1", {})
    item_node2 = FinancialStatementItemNode("Item2", {})
    graph._nodes = {
        "item1": item_node1,
        "calc1": sample_calc_node,
        "item2": item_node2,
        "other": sample_node,
    }

    fs_items = graph.get_financial_statement_items()
    assert len(fs_items) == 2
    assert item_node1 in fs_items
    assert item_node2 in fs_items
    assert sample_calc_node not in fs_items
    assert sample_node not in fs_items


def test_graph_repr_empty(mock_data_manager: tuple[MagicMock, MagicMock]):
    """Test __repr__ for an empty graph."""
    instance_mock_dm, _ = mock_data_manager
    # Configure the mock property directly
    type(instance_mock_dm).periods = PropertyMock(return_value=[])
    graph = Graph()
    expected = (
        "<Graph(Total Nodes: 0, FS Items: 0, Calculations: 0, Dependencies: 0, Periods: [None])>"
    )
    assert repr(graph) == expected


def test_graph_repr_with_nodes(
    mock_data_manager: tuple[MagicMock, MagicMock], sample_calc_node: MagicMock
):
    """Test __repr__ for a graph with various nodes."""
    instance_mock_dm, _ = mock_data_manager
    type(instance_mock_dm).periods = PropertyMock(return_value=["2023", "2024"])
    graph = Graph()
    item1 = FinancialStatementItemNode("Item1", {"2023": 1})
    item2 = FinancialStatementItemNode("Item2", {"2023": 2})

    # Configure calc node inputs *before* adding to graph._nodes for repr
    mock_input1 = MagicMock(name="Item1")
    sample_calc_node.inputs = [mock_input1]
    sample_calc_node.name = "Calc1"

    graph._nodes = {"Item1": item1, "Item2": item2, "Calc1": sample_calc_node}

    # Ensure get_dependencies reflects the change
    sample_calc_node.get_dependencies.side_effect = lambda: [
        i.name for i in sample_calc_node.inputs
    ]

    expected = "<Graph(Total Nodes: 3, FS Items: 2, Calculations: 1, Dependencies: 1, Periods: ['2023', '2024'])>"
    assert repr(graph) == expected
