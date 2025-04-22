import pytest
from unittest.mock import MagicMock, patch, call
import logging
from typing import Optional, Dict, List  # Added Optional, Dict, List

# Assuming fin_statement_model is importable (adjust path if needed)
from fin_statement_model.core.calculation_engine import CalculationEngine
from fin_statement_model.core.nodes import Node, StrategyCalculationNode, MetricCalculationNode
from fin_statement_model.core.errors import NodeError, CalculationError, ConfigurationError
from fin_statement_model.core.metrics import MetricRegistry  # Import the class

# --- Mock Node Classes ---


class MockNode(Node):
    """Mock base node for testing."""

    def __init__(self, name: str, value: float = 0.0, deps: Optional[List[str]] = None):
        super().__init__(name)
        self._value = value
        self._deps = deps or []

    def calculate(self, period: str) -> float:
        # Simple calculation for testing
        if period == "error_period":
            raise ValueError("Simulated calculation error")
        return self._value + float(period.split("Q")[-1])  # e.g., 2023Q1 -> 1.0

    def get_dependencies(self) -> list[str]:
        return self._deps

    def set_value(self, value: float):
        self._value = value


class MockStrategyNode(StrategyCalculationNode):
    """Mock strategy node for testing."""

    def __init__(self, name: str, inputs: List[Node], strategy_name: str = "mock_strategy"):
        # Mock strategy object
        self.strategy = MagicMock()
        self.strategy.name = strategy_name
        self.inputs = inputs  # Need inputs attribute for change_strategy test logic
        super().__init__(name, inputs, self.strategy)  # Call super.__init__ correctly

    def calculate(self, period: str) -> float:
        if period == "error_period":
            raise ValueError("Simulated calculation error in strategy node")
        # Simulate calculation based on inputs and period
        input_sum = sum(inp.calculate(period) for inp in self.inputs)
        return input_sum * 2  # Example calculation

    def change_strategy(self, new_strategy_name: str, **kwargs):
        if new_strategy_name == "nonexistent_strategy":
            raise LookupError("Strategy not found")
        if new_strategy_name == "error_strategy":
            raise TypeError("Invalid kwargs for strategy")
        self.strategy.name = new_strategy_name
        # In a real scenario, a new strategy object would be created and assigned
        self.strategy = MagicMock()  # Replace with a new mock for the new strategy
        self.strategy.name = new_strategy_name
        print(f"Strategy changed to {new_strategy_name} with kwargs {kwargs}")  # For debugging

    def get_dependencies(self) -> list[str]:
        return [inp.name for inp in self.inputs]


class MockMetricNode(MetricCalculationNode):
    """Mock metric node for testing."""

    def __init__(self, name: str, metric_name: str, inputs: Dict[str, Node]):
        # Normally created via factory, simplifying here
        super().__init__(name, metric_name, inputs)
        # Store inputs for the mock calculate method
        self.inputs = inputs
        self.description = f"Metric for {metric_name}"

    def calculate(self, period: str) -> float:
        if period == "error_period":
            raise ValueError("Simulated calculation error in metric node")
        # Simplified calculation based on inputs
        input_sum = sum(inp.calculate(period) for inp in self.inputs.values())
        return input_sum + 10  # Example calculation

    def get_dependencies(self) -> list[str]:
        return list(self.inputs.keys())


# --- Fixtures ---


@pytest.fixture
def shared_nodes_registry():
    """Provides a fresh, empty dictionary for each test to use as the node registry."""
    return {}


@pytest.fixture
def mock_metric_registry(monkeypatch):
    """Provides a mock MetricRegistry instance with pre-populated metrics."""
    registry = MetricRegistry()

    # Directly populate the internal _metrics dictionary
    registry._metrics = {
        "valid_metric": {
            "name": "Valid Metric",
            "inputs": ["input_a", "input_b"],
            "formula": "a+b",
            "description": "Valid test metric",
        },
        "metric_no_formula": {
            "name": "No Formula Metric",
            "inputs": ["input_a"],
            "description": "Missing formula",
        },  # Missing formula field
        "metric_no_inputs": {
            "name": "No Input Metric",
            "formula": "1",
            "description": "Missing inputs",
        },  # Missing inputs field
        "metric_bad_inputs": {
            "name": "Bad Input Metric",
            "inputs": "not_a_list",
            "formula": "1",
            "description": "Inputs not list",
        },  # Invalid inputs type
        "factory_error_metric": {
            "name": "Factory Error",
            "inputs": ["input_a", "input_b"],
            "formula": "a/b",
            "description": "Metric for factory error test",
        },
        "metric_z": {
            "name": "Metric Z",
            "inputs": ["input_a"],
            "formula": "a",
            "description": "Z metric",
        },
        "metric_a": {
            "name": "Metric A",
            "inputs": ["input_b"],
            "formula": "b",
            "description": "A metric",
        },
    }
    # Add the 'name' field required by the registry's validation logic (if it were called)
    # Although load_metrics_from_directory isn't called, the CalculationEngine
    # might implicitly expect fields validated by it.

    # Patch the registry instance used by the calculation engine module
    # Patch it where it's imported and used (both calculation_engine and calculation_nodes)
    monkeypatch.setattr("fin_statement_model.core.calculation_engine.metric_registry", registry)
    monkeypatch.setattr(
        "fin_statement_model.core.nodes.calculation_nodes.metric_registry", registry, raising=False
    )
    return registry


# Patch NodeFactory globally for most tests to avoid side effects and control node creation
@pytest.fixture(autouse=True)  # Apply automatically to all tests in this module
def mock_node_factory(monkeypatch):
    """Mocks the NodeFactory used by CalculationEngine."""
    mock_factory_instance = MagicMock()

    # Mock create_calculation_node
    def mock_create_calc(name, inputs, calculation_type, **kwargs):
        if calculation_type == "error_type":
            raise ValueError("Invalid calculation type")
        if calculation_type == "type_error_type":
            raise TypeError("Incorrect kwargs for type")
        # Return our mock strategy node
        return MockStrategyNode(name, inputs, strategy_name=calculation_type)

    mock_factory_instance.create_calculation_node.side_effect = mock_create_calc

    # Mock create_metric_node
    def mock_create_metric(name, metric_name, input_nodes):
        if metric_name == "factory_error_metric":
            raise ConfigurationError("Factory configuration error")
        return MockMetricNode(name, metric_name, input_nodes)

    mock_factory_instance.create_metric_node.side_effect = mock_create_metric

    # Mock _create_custom_node_from_callable (assuming it exists and works like this)
    def mock_create_custom(name, inputs, formula, description):
        if name == "factory_error_custom":
            raise ValueError("Factory error creating custom node")
        # Simulate a node created from a callable
        node = MockNode(name, deps=[inp.name for inp in inputs])  # Use MockNode for simplicity
        node.formula = formula
        node.description = description

        # Make calculate use the formula (simplified)
        def custom_calc(period: str) -> float:
            # Basic simulation: Call formula with dummy input values based on period
            mock_inputs = {inp.name: inp.calculate(period) for inp in inputs}
            try:
                return formula(period=period, inputs=mock_inputs)
            except Exception as e:
                raise CalculationError(f"Error in custom formula for {name}: {e}") from e

        node.calculate = custom_calc
        return node

    mock_factory_instance._create_custom_node_from_callable.side_effect = mock_create_custom

    # Mock get_available_operations
    mock_factory_instance.get_available_operations.return_value = {
        "addition": "Adds inputs",
        "subtraction": "Subtracts inputs",
    }

    # Patch the constructor of CalculationEngine to return this mock instance
    # Patching __init__ is tricky, instead patch the NodeFactory class itself
    # so when CalculationEngine creates its instance, it gets the mocked class
    mock_factory_class = MagicMock(return_value=mock_factory_instance)
    monkeypatch.setattr(
        "fin_statement_model.core.calculation_engine.NodeFactory", mock_factory_class
    )

    return mock_factory_instance  # Return the instance for potential direct assertions


@pytest.fixture
def engine(shared_nodes_registry):
    """Provides a CalculationEngine instance using the shared registry."""
    return CalculationEngine(shared_nodes_registry)


# --- Test Cases ---


def test_init(engine, shared_nodes_registry):
    """Test CalculationEngine initialization."""
    assert engine._nodes is shared_nodes_registry
    assert isinstance(engine._cache, dict)
    assert len(engine._cache) == 0
    assert isinstance(engine._metric_names, set)
    assert len(engine._metric_names) == 0
    # Check if the NodeFactory was instantiated (via the mock)
    assert engine._node_factory is not None
    assert engine._node_factory.mock_calls is not None  # Check it's a mock


def test_add_calculation_success(engine, shared_nodes_registry, mock_node_factory):
    """Test adding a valid calculation node."""
    input_a = MockNode("input_a", value=10)
    input_b = MockNode("input_b", value=5)
    shared_nodes_registry["input_a"] = input_a
    shared_nodes_registry["input_b"] = input_b

    node = engine.add_calculation("calc_sum", ["input_a", "input_b"], "addition")

    assert "calc_sum" in shared_nodes_registry
    assert shared_nodes_registry["calc_sum"] is node
    assert isinstance(node, MockStrategyNode)  # Check the type returned by the mocked factory
    assert node.name == "calc_sum"
    # Verify factory was called correctly
    mock_node_factory.create_calculation_node.assert_called_once_with(
        name="calc_sum", inputs=[input_a, input_b], calculation_type="addition"
    )
    assert (
        engine.calculate("calc_sum", "2023Q1") == (11.0 + 6.0) * 2
    )  # Based on MockStrategyNode.calculate


def test_add_calculation_missing_input(engine, shared_nodes_registry):
    """Test adding calculation with missing input nodes."""
    shared_nodes_registry["input_a"] = MockNode("input_a")
    with pytest.raises(NodeError, match="Missing required input nodes.*'missing_input'"):
        engine.add_calculation("calc_fail", ["input_a", "missing_input"], "addition")
    assert "calc_fail" not in shared_nodes_registry


def test_add_calculation_overwrite_warning(engine, shared_nodes_registry, caplog):
    """Test warning when overwriting an existing node."""
    shared_nodes_registry["existing_node"] = MockNode("existing_node")
    input_a = MockNode("input_a")
    shared_nodes_registry["input_a"] = input_a

    with caplog.at_level(logging.WARNING):
        engine.add_calculation("existing_node", ["input_a"], "subtraction")

    assert "Overwriting existing node" in caplog.text
    assert "existing_node" in shared_nodes_registry
    assert isinstance(
        shared_nodes_registry["existing_node"], MockStrategyNode
    )  # Check it was replaced


def test_add_calculation_factory_value_error(engine, shared_nodes_registry, mock_node_factory):
    """Test handling factory ValueError during calculation node creation."""
    input_a = MockNode("input_a")
    shared_nodes_registry["input_a"] = input_a

    with pytest.raises(ValueError, match="Invalid calculation type"):
        engine.add_calculation("calc_fail", ["input_a"], "error_type")
    assert "calc_fail" not in shared_nodes_registry


def test_add_calculation_factory_type_error(engine, shared_nodes_registry, mock_node_factory):
    """Test handling factory TypeError during calculation node creation."""
    input_a = MockNode("input_a")
    shared_nodes_registry["input_a"] = input_a

    with pytest.raises(TypeError, match="Incorrect kwargs for type"):
        engine.add_calculation("calc_fail", ["input_a"], "type_error_type")
    assert "calc_fail" not in shared_nodes_registry


# --- Tests for add_metric ---


def test_add_metric_success(engine, shared_nodes_registry, mock_metric_registry, mock_node_factory):
    """Test adding a valid metric node."""
    input_a = MockNode("input_a", value=100)
    input_b = MockNode("input_b", value=50)
    shared_nodes_registry["input_a"] = input_a
    shared_nodes_registry["input_b"] = input_b

    metric_node = engine.add_metric("valid_metric", "calculated_metric")

    assert "calculated_metric" in shared_nodes_registry
    assert shared_nodes_registry["calculated_metric"] is metric_node
    assert isinstance(metric_node, MockMetricNode)
    assert metric_node.name == "calculated_metric"
    assert "calculated_metric" in engine._metric_names

    # Verify factory call
    mock_node_factory.create_metric_node.assert_called_once_with(
        name="calculated_metric",
        metric_name="valid_metric",
        input_nodes={"input_a": input_a, "input_b": input_b},
    )
    # Test calculation
    assert (
        engine.calculate("calculated_metric", "2023Q2") == (102.0 + 52.0) + 10
    )  # MockMetricNode calc


def test_add_metric_node_name_conflict(engine, shared_nodes_registry, mock_metric_registry):
    """Test adding a metric when the node name already exists."""
    shared_nodes_registry["existing_node"] = MockNode("existing_node")
    shared_nodes_registry["input_a"] = MockNode("input_a")
    shared_nodes_registry["input_b"] = MockNode("input_b")

    with pytest.raises(ValueError, match="node with name 'existing_node' already exists"):
        engine.add_metric("valid_metric", "existing_node")
    assert "existing_node" not in engine._metric_names


def test_add_metric_missing_input(engine, shared_nodes_registry, mock_metric_registry):
    """Test adding a metric with missing input nodes."""
    shared_nodes_registry["input_a"] = MockNode("input_a")  # input_b is missing

    with pytest.raises(
        NodeError, match=r"Cannot create metric .* Missing required input nodes .* \['input_b'\]"
    ):
        engine.add_metric("valid_metric", "metric_fail")
    assert "metric_fail" not in shared_nodes_registry
    assert "metric_fail" not in engine._metric_names


def test_add_metric_unknown_metric_name(engine, shared_nodes_registry, mock_metric_registry):
    """Test adding a metric with an unknown metric definition name."""
    shared_nodes_registry["input_a"] = MockNode("input_a")
    shared_nodes_registry["input_b"] = MockNode("input_b")

    with pytest.raises(ConfigurationError, match="Unknown metric definition: 'unknown_metric'"):
        engine.add_metric("unknown_metric", "metric_fail")


def test_add_metric_invalid_definition_no_formula(
    engine, shared_nodes_registry, mock_metric_registry
):
    """Test adding a metric with definition missing 'formula'."""
    shared_nodes_registry["input_a"] = MockNode("input_a")
    with pytest.raises(ConfigurationError, match="missing 'formula'"):
        engine.add_metric("metric_no_formula", "metric_fail")


def test_add_metric_invalid_definition_no_inputs(
    engine, shared_nodes_registry, mock_metric_registry
):
    """Test adding a metric with definition missing 'inputs'."""
    with pytest.raises(ConfigurationError, match="missing or invalid 'inputs' list"):
        engine.add_metric("metric_no_inputs", "metric_fail")


def test_add_metric_invalid_definition_bad_inputs(
    engine, shared_nodes_registry, mock_metric_registry
):
    """Test adding a metric with definition having invalid 'inputs' type."""
    with pytest.raises(ConfigurationError, match="missing or invalid 'inputs' list"):
        engine.add_metric("metric_bad_inputs", "metric_fail")


def test_add_metric_invalid_node_name_type(engine, mock_metric_registry):
    """Test adding a metric with non-string or empty node name."""
    with pytest.raises(TypeError, match="Metric node name must be a non-empty string"):
        engine.add_metric("valid_metric", "")
    with pytest.raises(TypeError, match="Metric node name must be a non-empty string"):
        engine.add_metric("valid_metric", None)
    with pytest.raises(TypeError, match="Metric node name must be a non-empty string"):
        engine.add_metric("valid_metric", 123)


def test_add_metric_factory_error(
    engine, shared_nodes_registry, mock_metric_registry, mock_node_factory
):
    """Test handling error during metric node creation in the factory."""
    shared_nodes_registry["input_a"] = MockNode("input_a")
    shared_nodes_registry["input_b"] = MockNode("input_b")
    # No longer need to call mock_metric_registry.add here
    # mock_metric_registry.add("factory_error_metric", {"inputs": ["input_a", "input_b"], "formula": "a/b"})

    with pytest.raises(ConfigurationError, match="Factory configuration error"):
        engine.add_metric("factory_error_metric", "metric_factory_fail")
    assert "metric_factory_fail" not in shared_nodes_registry
    assert "metric_factory_fail" not in engine._metric_names


# --- Tests for calculate ---


def test_calculate_success_cache_miss(engine, shared_nodes_registry):
    """Test successful calculation and caching."""
    node = MockNode("node_a", value=10)
    shared_nodes_registry["node_a"] = node

    assert "node_a" not in engine._cache

    value = engine.calculate("node_a", "2023Q1")
    assert value == 11.0  # 10 + 1.0 from period
    assert "node_a" in engine._cache
    assert engine._cache["node_a"]["2023Q1"] == 11.0


def test_calculate_success_cache_hit(engine, shared_nodes_registry):
    """Test calculation cache hit."""
    node = MockNode("node_a", value=10)
    shared_nodes_registry["node_a"] = node

    # Pre-populate cache
    engine._cache["node_a"] = {"2023Q1": 99.9}

    # Mock the node's calculate to ensure it's NOT called
    node.calculate = MagicMock(return_value=11.0)

    value = engine.calculate("node_a", "2023Q1")
    assert value == 99.9  # Should return cached value
    node.calculate.assert_not_called()  # Verify calculate wasn't called


def test_calculate_node_not_found(engine):
    """Test calculation when node is not in the registry."""
    with pytest.raises(NodeError, match="Node 'nonexistent' not found"):
        engine.calculate("nonexistent", "2023Q1")


def test_calculate_node_calculation_error(engine, shared_nodes_registry):
    """Test calculation wrapping node's calculation error."""
    node = MockNode("error_node", value=10)
    shared_nodes_registry["error_node"] = node

    with pytest.raises(CalculationError, match="Failed to calculate node 'error_node'") as exc_info:
        engine.calculate("error_node", "error_period")  # MockNode raises ValueError here

    # Check if the original error is wrapped correctly (optional but good practice)
    assert isinstance(exc_info.value.__cause__, ValueError)
    assert "Simulated calculation error" in str(exc_info.value.__cause__)
    assert exc_info.value.node_id == "error_node"
    assert exc_info.value.period == "error_period"

    # Ensure error result is not cached
    assert "error_node" not in engine._cache


def test_calculate_node_missing_calculate_method(engine, shared_nodes_registry):
    """Test calculation if node object lacks a calculate method."""

    class NodeWithoutCalculate:
        name = "no_calc_node"

    node = NodeWithoutCalculate()
    shared_nodes_registry["no_calc_node"] = node

    with pytest.raises(TypeError, match="does not have a callable calculate method"):
        engine.calculate("no_calc_node", "2023Q1")


# --- Tests for recalculate_all ---


def test_recalculate_all_with_periods(engine, shared_nodes_registry):
    """Test recalculate_all forces calculation for specified periods."""
    node_a = MockNode("node_a", value=10)
    node_b = MockNode("node_b", value=20)
    shared_nodes_registry["node_a"] = node_a
    shared_nodes_registry["node_b"] = node_b

    # Pre-populate cache with old values
    engine._cache = {"node_a": {"2023Q1": 99.0}, "node_b": {"2023Q1": 199.0, "2023Q2": 299.0}}

    # Mock calculate methods to track calls
    node_a.calculate = MagicMock(side_effect=lambda p: 10 + float(p.split("Q")[-1]))
    node_b.calculate = MagicMock(side_effect=lambda p: 20 + float(p.split("Q")[-1]))

    periods_to_recalc = ["2023Q1", "2023Q2"]
    engine.recalculate_all(periods=periods_to_recalc)

    # Assert cache is cleared and repopulated with correct values
    assert engine._cache["node_a"]["2023Q1"] == 11.0
    assert engine._cache["node_a"]["2023Q2"] == 12.0
    assert engine._cache["node_b"]["2023Q1"] == 21.0
    assert engine._cache["node_b"]["2023Q2"] == 22.0

    # Assert calculate was called for all nodes and periods
    expected_calls_a = [call("2023Q1"), call("2023Q2")]
    expected_calls_b = [call("2023Q1"), call("2023Q2")]
    node_a.calculate.assert_has_calls(expected_calls_a, any_order=True)
    node_b.calculate.assert_has_calls(expected_calls_b, any_order=True)
    assert node_a.calculate.call_count == len(periods_to_recalc)
    assert node_b.calculate.call_count == len(periods_to_recalc)


def test_recalculate_all_no_periods(engine, shared_nodes_registry):
    """Test recalculate_all with no periods just clears the cache."""
    shared_nodes_registry["node_a"] = MockNode("node_a", value=10)
    engine._cache["node_a"] = {"2023Q1": 99.0}  # Pre-populate cache

    engine.recalculate_all(periods=None)

    assert len(engine._cache) == 0  # Cache should be empty


def test_recalculate_all_continues_on_error(engine, shared_nodes_registry, caplog):
    """Test recalculate_all logs warning and continues if one node fails."""
    node_a = MockNode("node_a", value=10)
    error_node = MockNode("error_node", value=20)
    shared_nodes_registry["node_a"] = node_a
    shared_nodes_registry["error_node"] = error_node

    # Make error_node fail calculation for Q2
    original_calc = error_node.calculate

    def erroring_calculate(period):
        if period == "2023Q2":
            raise ValueError("Calculation failed for Q2")
        return original_calc(period)

    error_node.calculate = erroring_calculate  # type: ignore

    periods = ["2023Q1", "2023Q2"]
    with caplog.at_level(logging.WARNING):
        engine.recalculate_all(periods=periods)

    # Check warning log
    assert "Error recalculating node 'error_node' for period '2023Q2'" in caplog.text

    # Check that the working node was still calculated for both periods
    assert "node_a" in engine._cache
    assert engine._cache["node_a"]["2023Q1"] == 11.0
    assert engine._cache["node_a"]["2023Q2"] == 12.0

    # Check that the failing node was calculated where possible
    assert "error_node" in engine._cache
    assert engine._cache["error_node"]["2023Q1"] == 21.0
    assert "2023Q2" not in engine._cache.get("error_node", {})  # Q2 failed


# --- Tests for get_available_operations ---


def test_get_available_operations(engine, mock_node_factory):
    """Test retrieving available operations from the factory."""
    ops = engine.get_available_operations()
    assert ops == {
        "addition": "Adds inputs",
        "subtraction": "Subtracts inputs",
    }
    mock_node_factory.get_available_operations.assert_called_once()


# --- Tests for change_calculation_strategy ---


def test_change_calculation_strategy_success(engine, shared_nodes_registry):
    """Test successfully changing a node's strategy."""
    input_a = MockNode("input_a")
    input_b = MockNode("input_b")
    shared_nodes_registry["input_a"] = input_a
    shared_nodes_registry["input_b"] = input_b
    # Use the *real* add_calculation which uses the mocked factory
    calc_node = engine.add_calculation("calc_node", ["input_a", "input_b"], "addition")

    assert isinstance(calc_node, MockStrategyNode)  # Ensure it's the mock node
    assert calc_node.strategy.name == "addition"

    # Add something to cache
    engine._cache["calc_node"] = {"2023Q1": 123.0}

    engine.change_calculation_strategy("calc_node", "subtraction", extra_arg="test")

    # Check node in registry was updated (strategy name change)
    updated_node = shared_nodes_registry["calc_node"]
    assert isinstance(updated_node, MockStrategyNode)
    assert updated_node.strategy.name == "subtraction"

    # Check cache for this node was cleared
    assert "calc_node" not in engine._cache


@patch.object(MockStrategyNode, "change_strategy")  # Mock the method on the class
def test_change_calculation_strategy_node_method_called(
    mock_change_strat_method, engine, shared_nodes_registry
):
    """Verify the node's change_strategy method is called."""
    # Setup a MockStrategyNode directly in the registry for this test
    mock_node = MockStrategyNode("strategy_node", [])
    shared_nodes_registry["strategy_node"] = mock_node

    engine.change_calculation_strategy("strategy_node", "new_strat", key="value")

    # Assert the node's method was called with correct args
    mock_change_strat_method.assert_called_once_with("new_strat", key="value")


def test_change_calculation_strategy_node_not_found(engine):
    """Test changing strategy for a non-existent node."""
    with pytest.raises(ValueError, match="Node 'nonexistent' not found"):
        engine.change_calculation_strategy("nonexistent", "new_strategy")


def test_change_calculation_strategy_node_not_strategy_type(engine, shared_nodes_registry):
    """Test changing strategy for a node that isn't a StrategyCalculationNode."""
    shared_nodes_registry["not_strategy"] = MockNode("not_strategy")
    with pytest.raises(ValueError, match="not a strategy calculation node"):
        engine.change_calculation_strategy("not_strategy", "new_strategy")


def test_change_calculation_strategy_lookup_error(engine, shared_nodes_registry):
    """Test changing to a strategy that causes a LookupError on the node."""
    calc_node = MockStrategyNode("calc_node", [])
    shared_nodes_registry["calc_node"] = calc_node
    # Mock the node's method to raise LookupError
    calc_node.change_strategy = MagicMock(side_effect=LookupError("Strategy not found"))

    with pytest.raises(LookupError, match="Strategy not found"):
        engine.change_calculation_strategy("calc_node", "nonexistent_strategy")


def test_change_calculation_strategy_type_error(engine, shared_nodes_registry):
    """Test changing to a strategy that causes a TypeError on the node."""
    calc_node = MockStrategyNode("calc_node", [])
    shared_nodes_registry["calc_node"] = calc_node
    # Mock the node's method to raise TypeError
    calc_node.change_strategy = MagicMock(side_effect=TypeError("Invalid kwargs"))

    with pytest.raises(TypeError, match="Invalid kwargs"):
        engine.change_calculation_strategy("calc_node", "error_strategy", invalid="kwarg")


# --- Tests for add_custom_calculation ---


def test_add_custom_calculation_success(engine, shared_nodes_registry, mock_node_factory):
    """Test adding a valid custom calculation node."""

    def my_formula(period: str, inputs: Dict[str, float]) -> float:
        return inputs.get("in_a", 0) * float(period.split("Q")[-1])

    input_a = MockNode("in_a", value=5)
    shared_nodes_registry["in_a"] = input_a

    custom_node = engine.add_custom_calculation(
        name="custom_calc",
        calculation_func=my_formula,
        inputs=["in_a"],
        description="My custom formula",
    )

    assert "custom_calc" in shared_nodes_registry
    assert shared_nodes_registry["custom_calc"] is custom_node
    # Check the mock factory was called correctly
    mock_node_factory._create_custom_node_from_callable.assert_called_once_with(
        name="custom_calc", inputs=[input_a], formula=my_formula, description="My custom formula"
    )
    # Check if calculation works via the engine (uses the mocked node's patched calculate)
    assert (
        engine.calculate("custom_calc", "2023Q2") == 7.0 * 2.0
    )  # in_a value 5 + period 2 = 7. Formula * period = 7*2=14
    # ^^ The mock formula simulation is basic, let's re-check based on the mock implementation
    # MockNode('in_a', value=5).calculate('2023Q2') -> 5 + 2.0 = 7.0
    # custom_calc calls my_formula(period='2023Q2', inputs={'in_a': 7.0})
    # my_formula returns inputs['in_a'] * float(period.split('Q')[-1]) -> 7.0 * 2.0 = 14.0
    assert engine.calculate("custom_calc", "2023Q2") == 14.0


def test_add_custom_calculation_no_inputs(engine, shared_nodes_registry, mock_node_factory):
    """Test adding custom calculation with no inputs."""

    def no_input_formula(period: str, inputs: Dict[str, float]) -> float:
        return 42.0

    engine.add_custom_calculation("const_val", no_input_formula)
    assert "const_val" in shared_nodes_registry
    mock_node_factory._create_custom_node_from_callable.assert_called_once_with(
        name="const_val", inputs=[], formula=no_input_formula, description=""
    )
    assert engine.calculate("const_val", "2023Q1") == 42.0


def test_add_custom_calculation_missing_input(engine, shared_nodes_registry):
    """Test adding custom calculation with missing input node."""

    def my_formula(period: str, inputs: Dict[str, float]) -> float:
        return 1.0

    shared_nodes_registry["in_a"] = MockNode("in_a")

    with pytest.raises(
        NodeError,
        match=r"Cannot create custom calculation node .* Missing required input nodes: \['missing_in'\]",
    ):
        engine.add_custom_calculation("custom_fail", my_formula, inputs=["in_a", "missing_in"])
    assert "custom_fail" not in shared_nodes_registry


def test_add_custom_calculation_overwrite(engine, shared_nodes_registry, caplog):
    """Test adding custom calculation that overwrites an existing node."""
    shared_nodes_registry["existing"] = MockNode("existing")

    def my_formula(period: str, inputs: Dict[str, float]) -> float:
        return 1.0

    with caplog.at_level(logging.WARNING):
        engine.add_custom_calculation("existing", my_formula)

    assert "Overwriting existing node" in caplog.text
    assert "existing" in shared_nodes_registry
    # Check it's the new node type (mocked)
    assert hasattr(shared_nodes_registry["existing"], "formula")


def test_add_custom_calculation_factory_error(engine, shared_nodes_registry, mock_node_factory):
    """Test factory error during custom calculation node creation."""

    def my_formula(period: str, inputs: Dict[str, float]) -> float:
        return 1.0

    with pytest.raises(ValueError, match="Factory error creating custom node"):
        engine.add_custom_calculation("factory_error_custom", my_formula)
    assert "factory_error_custom" not in shared_nodes_registry


# --- Tests for add_calculation_node ---


def test_add_calculation_node_success(engine, shared_nodes_registry):
    """Test adding a pre-constructed node."""
    prebuilt_node = MockNode("prebuilt", value=99)
    engine.add_calculation_node(prebuilt_node)

    assert "prebuilt" in shared_nodes_registry
    assert shared_nodes_registry["prebuilt"] is prebuilt_node
    assert engine.calculate("prebuilt", "2023Q1") == 100.0  # 99 + 1.0


def test_add_calculation_node_overwrite(engine, shared_nodes_registry, caplog):
    """Test adding pre-constructed node overwriting existing."""
    shared_nodes_registry["existing"] = MockNode("existing", value=1)
    new_node = MockNode("existing", value=100)

    with caplog.at_level(logging.WARNING):
        engine.add_calculation_node(new_node)

    assert "Overwriting existing node" in caplog.text
    assert shared_nodes_registry["existing"] is new_node
    assert engine.calculate("existing", "2023Q1") == 101.0


# --- Tests for get_metric ---


def test_get_metric_success(engine, shared_nodes_registry, mock_metric_registry):
    """Test retrieving a node that was registered as a metric."""
    input_a = MockNode("input_a")
    input_b = MockNode("input_b")
    shared_nodes_registry["input_a"] = input_a
    shared_nodes_registry["input_b"] = input_b
    metric_node = engine.add_metric("valid_metric", "my_metric_node")

    retrieved_node = engine.get_metric("my_metric_node")
    assert retrieved_node is metric_node


def test_get_metric_node_exists_not_metric(engine, shared_nodes_registry):
    """Test get_metric for a node name that exists but wasn't added via add_metric."""
    shared_nodes_registry["not_a_metric"] = MockNode("not_a_metric")

    retrieved_node = engine.get_metric("not_a_metric")
    assert retrieved_node is None


def test_get_metric_node_not_found(engine):
    """Test get_metric for a non-existent node name."""
    retrieved_node = engine.get_metric("nonexistent_metric")
    assert retrieved_node is None


# --- Tests for get_available_metrics ---


def test_get_available_metrics_empty(engine):
    """Test get_available_metrics when no metrics have been added."""
    assert engine.get_available_metrics() == []


def test_get_available_metrics_populated(engine, shared_nodes_registry, mock_metric_registry):
    """Test get_available_metrics returns sorted list of added metric node names."""
    # Add necessary inputs first
    shared_nodes_registry["input_a"] = MockNode("input_a")
    shared_nodes_registry["input_b"] = MockNode("input_b")
    # No longer need to call mock_metric_registry.add here, it's done in the fixture
    # mock_metric_registry.add("metric_z", {"inputs": ["input_a"], "formula": "a"})
    # mock_metric_registry.add("metric_a", {"inputs": ["input_b"], "formula": "b"})

    engine.add_metric("metric_z", "node_z")
    engine.add_metric("valid_metric", "node_valid")
    engine.add_metric("metric_a", "node_a")

    # Add a non-metric node
    engine.add_calculation_node(MockNode("not_metric"))

    metrics = engine.get_available_metrics()
    assert metrics == ["node_a", "node_valid", "node_z"]  # Should be sorted alphabetically


# --- Tests for get_metric_info ---


def test_get_metric_info_success(engine, shared_nodes_registry, mock_metric_registry):
    """Test getting information for a valid metric node."""
    input_a = MockNode("input_a")
    input_b = MockNode("input_b")
    shared_nodes_registry["input_a"] = input_a
    shared_nodes_registry["input_b"] = input_b
    # Need to actually add the metric node to the engine registry
    engine.add_metric("valid_metric", "my_metric")  # MockMetricNode has deps ['a', 'b']

    # Query the added metric node name
    info = engine.get_metric_info("my_metric")

    assert info == {
        "name": "my_metric",  # Check against the node name added
        "description": "Metric for valid_metric",  # From MockMetricNode
        "inputs": ["input_a", "input_b"],  # From MockMetricNode.get_dependencies
    }


def test_get_metric_info_node_exists_not_metric(engine, shared_nodes_registry):
    """Test get_metric_info for a node that exists but isn't a metric."""
    shared_nodes_registry["not_metric"] = MockNode("not_metric")
    with pytest.raises(
        ValueError, match="Node 'not_metric' exists but was not registered as a metric"
    ):
        engine.get_metric_info("not_metric")


def test_get_metric_info_node_not_found(engine):
    """Test get_metric_info for a non-existent node."""
    with pytest.raises(ValueError, match="Metric with ID 'nonexistent' not found"):
        engine.get_metric_info("nonexistent")


def test_get_metric_info_node_no_dependencies_method(
    engine, shared_nodes_registry, mock_metric_registry, monkeypatch
):
    """Test get_metric_info for a metric node lacking get_dependencies but having inputs attr."""
    input_a = MockNode("input_a")
    shared_nodes_registry["input_a"] = input_a

    # Create a mock node type without get_dependencies but with list inputs
    class MetricWithoutDepsList(Node):  # Inherit from Node is enough
        def __init__(self, name, metric_name, inputs_list):
            Node.__init__(self, name)
            self.metric_name = metric_name
            self.inputs = inputs_list  # Store list of nodes
            self.description = "List inputs"

        def calculate(self, period):
            return 1.0

        # No get_dependencies method

    metric_node = MetricWithoutDepsList("metric_list_inputs", "metric_a", [input_a])
    engine.add_calculation_node(metric_node)  # Add directly
    engine._metric_names.add("metric_list_inputs")  # Manually register as metric

    info = engine.get_metric_info("metric_list_inputs")
    assert info["inputs"] == ["input_a"]


def test_get_metric_info_node_no_dependencies_method_dict(
    engine, shared_nodes_registry, mock_metric_registry, monkeypatch
):
    """Test get_metric_info for a metric node lacking get_dependencies but having dict inputs."""
    input_a = MockNode("input_a")
    input_b = MockNode("input_b")
    shared_nodes_registry["input_a"] = input_a
    shared_nodes_registry["input_b"] = input_b

    # Create a mock node type without get_dependencies but with dict inputs
    class MetricWithoutDepsDict(Node):  # Inherit from Node is enough
        def __init__(self, name, metric_name, inputs_dict):
            Node.__init__(self, name)
            self.metric_name = metric_name
            self.inputs = inputs_dict  # Store dict of nodes
            self.description = "Dict inputs"

        def calculate(self, period):
            return 1.0

        # No get_dependencies method

    metric_node = MetricWithoutDepsDict(
        "metric_dict_inputs", "metric_b", {"ia": input_a, "ib": input_b}
    )
    engine.add_calculation_node(metric_node)  # Add directly
    engine._metric_names.add("metric_dict_inputs")  # Manually register as metric

    info = engine.get_metric_info("metric_dict_inputs")
    # Note: The fallback logic extracts node names from the dict values
    assert info["inputs"] == sorted(
        ["input_a", "input_b"]
    )  # Expect node names, sorted for stability


def test_get_metric_info_node_no_dependencies_at_all(
    engine, shared_nodes_registry, mock_metric_registry
):
    """Test get_metric_info when node has neither get_dependencies nor inputs."""

    # Create a minimal node registered as a metric
    class MetricNoDepsAttr(Node):
        def __init__(self, name):
            super().__init__(name)
            self.description = "No deps info"

        def calculate(self, period):
            return 1.0

        # No get_dependencies, no inputs attribute

    metric_node = MetricNoDepsAttr("metric_no_deps")
    engine.add_calculation_node(metric_node)  # Add directly
    engine._metric_names.add("metric_no_deps")  # Manually register as metric

    info = engine.get_metric_info("metric_no_deps")
    assert info["inputs"] == []


# --- Tests for clear_cache ---


def test_clear_cache(engine):
    """Test clearing the calculation cache."""
    engine._cache = {"node_a": {"2023Q1": 1.0}, "node_b": {"2023Q1": 2.0}}
    assert len(engine._cache) == 2

    engine.clear_cache()
    assert len(engine._cache) == 0


# --- Tests for reset ---


def test_reset(engine, shared_nodes_registry):
    """Test resetting the engine state."""
    shared_nodes_registry["node_a"] = MockNode("node_a")  # Add node to shared registry
    engine._cache = {"node_a": {"2023Q1": 1.0}}
    engine._metric_names.add("some_metric")

    assert len(shared_nodes_registry) == 1
    assert len(engine._cache) == 1
    assert len(engine._metric_names) == 1

    engine.reset()

    # Check that cache and metric names are cleared
    assert len(engine._cache) == 0
    assert len(engine._metric_names) == 0

    # Check that the shared nodes registry is NOT cleared
    assert len(shared_nodes_registry) == 1
    assert "node_a" in shared_nodes_registry
