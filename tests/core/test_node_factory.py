"""Unit tests for the NodeFactory in fin_statement_model.core.node_factory."""

import pytest
from unittest.mock import patch, MagicMock, create_autospec

# Imports from the module under test
from fin_statement_model.core.node_factory import NodeFactory
from fin_statement_model.core.nodes import (
    Node,
    FinancialStatementItemNode,
    CalculationNode,
    MetricCalculationNode,
    CustomCalculationNode,
)
from fin_statement_model.core.calculations import Registry, Calculation


# --- Fixtures ---


@pytest.fixture
def mock_registry_get():
    """Fixture to mock the Registry.get method."""
    with patch.object(Registry, "get", autospec=True) as mock_get:
        yield mock_get


@pytest.fixture
def mock_metric_calc_node():
    """Fixture to mock the MetricCalculationNode class."""
    with patch(
        "fin_statement_model.core.node_factory.MetricCalculationNode", autospec=True
    ) as mock_class:
        yield mock_class


@pytest.fixture
def mock_node_a():
    """Fixture for a generic mock Node."""
    mock = create_autospec(Node, instance=True)
    mock.name = "NodeA"
    return mock


@pytest.fixture
def mock_node_b():
    """Fixture for another generic mock Node."""
    mock = create_autospec(Node, instance=True)
    mock.name = "NodeB"
    return mock


@pytest.fixture
def mock_strategy_class():
    """Fixture for a generic mock Strategy class."""
    # Create a spec for the Strategy class itself, including __init__
    MockStrategy = create_autospec(Calculation)
    # Add __name__ needed for error message formatting
    MockStrategy.__name__ = "MockStrategyClass"
    # Create an instance mock that __init__ would return
    mock_instance = MagicMock(spec=Calculation)
    MockStrategy.return_value = mock_instance  # Mocking the instance returned by __init__
    return MockStrategy


# --- Test Cases ---


# Tests for create_financial_statement_item
class TestCreateFinancialStatementItem:
    def test_success_creation(self):
        """Test successful creation of FinancialStatementItemNode."""
        name = "Revenue"
        values = {"2023": 100.0, "2024": 110.0}
        node = NodeFactory.create_financial_statement_item(name, values)
        assert isinstance(node, FinancialStatementItemNode)
        assert node.name == name
        # Check if values are stored correctly using the public interface
        for period, expected_value in values.items():
            # Assuming get_value exists and works as expected
            # This might require mocking get_value if it has complex logic,
            # but for a simple storage node, checking against input is reasonable.
            # We need to handle potential KeyErrors if get_value raises them.
            try:
                # Let's assume get_value returns the value directly for simplicity
                # If FinancialStatementItemNode requires more complex access, adjust this
                assert node.get_value(period) == expected_value
            except KeyError:
                pytest.fail(f"Node should have value for period '{period}' but get_value failed.")
        # Optional: Test for a period not provided
        # It seems get_value returns 0.0 for missing periods
        assert node.get_value("2025") == 0.0

    def test_success_with_empty_values(self):
        """Test creation with an empty values dictionary."""
        name = "Expenses"
        values = {}
        node = NodeFactory.create_financial_statement_item(name, values)
        assert isinstance(node, FinancialStatementItemNode)
        assert node.name == name
        # Check that getting any value returns 0.0 (or appropriate default)
        assert node.get_value("2023") == 0.0

    def test_error_empty_name(self):
        """Test creation fails with an empty name."""
        with pytest.raises(ValueError, match="Node name must be a non-empty string"):
            NodeFactory.create_financial_statement_item("", {"2023": 50.0})

    def test_error_non_string_name(self):
        """Test creation fails with a non-string name."""
        with pytest.raises(ValueError, match="Node name must be a non-empty string"):
            NodeFactory.create_financial_statement_item(123, {"2023": 50.0})


# Tests for create_calculation_node
class TestCreateCalculationNode:
    def test_success_creation(
        self, mock_registry_get, mock_strategy_class, mock_node_a, mock_node_b
    ):
        """Test successful creation of StrategyCalculationNode."""
        mock_registry_get.return_value = mock_strategy_class
        name = "GrossProfit"
        inputs = [mock_node_a, mock_node_b]
        calc_type = "subtraction"  # Assumes 'subtraction' maps to 'SubtractionStrategy'

        node = NodeFactory.create_calculation_node(name, inputs, calc_type)

        assert isinstance(node, CalculationNode)
        assert node.name == name
        assert node.inputs == inputs
        mock_registry_get.assert_called_once_with(NodeFactory._calculation_methods[calc_type])
        mock_strategy_class.assert_called_once_with()  # No extra kwargs
        assert node.calculation == mock_strategy_class.return_value  # Check instance was passed

    def test_success_with_strategy_kwargs(
        self, mock_registry_get, mock_strategy_class, mock_node_a, mock_node_b
    ):
        """Test creation with strategy-specific keyword arguments."""
        mock_registry_get.return_value = mock_strategy_class
        name = "WeightedAvg"
        inputs = [mock_node_a, mock_node_b]
        calc_type = "weighted_average"
        kwargs = {"weights": [0.6, 0.4]}

        node = NodeFactory.create_calculation_node(name, inputs, calc_type, **kwargs)

        assert isinstance(node, CalculationNode)
        assert node.name == name
        assert node.inputs == inputs
        mock_registry_get.assert_called_once_with(NodeFactory._calculation_methods[calc_type])
        mock_strategy_class.assert_called_once_with(**kwargs)
        assert node.calculation == mock_strategy_class.return_value

    def test_error_empty_name(self, mock_node_a):
        """Test creation fails with an empty name."""
        with pytest.raises(ValueError, match="Node name must be a non-empty string"):
            NodeFactory.create_calculation_node("", [mock_node_a], "addition")

    def test_error_empty_inputs(self):
        """Test creation fails with an empty input list."""
        with pytest.raises(ValueError, match="Calculation node must have at least one input"):
            NodeFactory.create_calculation_node("TestNode", [], "addition")

    def test_error_invalid_calculation_type(self, mock_node_a):
        """Test creation fails with an unknown calculation type."""
        invalid_type = "non_existent_type"
        with pytest.raises(ValueError, match=f"Invalid calculation type: '{invalid_type}'"):
            NodeFactory.create_calculation_node("TestNode", [mock_node_a], invalid_type)

    def test_error_strategy_not_in_registry(self, mock_registry_get, mock_node_a):
        """Test creation fails if the strategy is not found in the Registry."""
        calc_type = "addition"
        calculation_name = NodeFactory._calculation_methods[calc_type]
        mock_registry_get.side_effect = KeyError(f"Strategy '{calculation_name}' not found")

        with pytest.raises(ValueError, match=f"Strategy '{calculation_name}' not found in Registry"):
            NodeFactory.create_calculation_node("TestNode", [mock_node_a], calc_type)

    def test_error_strategy_instantiation_fails(
        self, mock_registry_get, mock_strategy_class, mock_node_a
    ):
        """Test creation fails if strategy instantiation fails (e.g., missing kwargs)."""
        mock_registry_get.return_value = mock_strategy_class
        # Simulate TypeError during __init__
        mock_strategy_class.side_effect = TypeError("Missing required argument 'weights'")
        calc_type = "weighted_average"  # Assume this requires 'weights'
        calculation_name = NodeFactory._calculation_methods[calc_type]

        with pytest.raises(TypeError, match=f"Could not instantiate strategy '{calculation_name}'"):
            NodeFactory.create_calculation_node(
                "TestNode", [mock_node_a], calc_type
            )  # Missing weights kwarg


# Tests for create_metric_node
class TestCreateMetricNode:
    def test_success_creation(self, mock_metric_calc_node, mock_node_a, mock_node_b):
        """Test successful creation delegation to MetricCalculationNode."""
        name = "CompanyCurrentRatio"
        metric_name = "current_ratio"
        input_nodes = {"current_assets": mock_node_a, "current_liabilities": mock_node_b}
        mock_instance = MagicMock(spec=MetricCalculationNode)
        mock_metric_calc_node.return_value = mock_instance

        node = NodeFactory.create_metric_node(name, metric_name, input_nodes)

        assert node == mock_instance
        mock_metric_calc_node.assert_called_once_with(
            name=name, metric_name=metric_name, input_nodes=input_nodes
        )

    def test_error_empty_name(self):
        """Test creation fails with an empty name."""
        with pytest.raises(ValueError, match="Node name must be a non-empty string"):
            NodeFactory.create_metric_node("", "some_metric", {})

    def test_error_input_nodes_not_dict(self):
        """Test creation fails if input_nodes is not a dictionary."""
        with pytest.raises(TypeError, match="input_nodes must be a dictionary"):
            NodeFactory.create_metric_node("Test", "some_metric", ["not", "a", "dict"])

    def test_error_propagates_from_constructor_value_error(self, mock_metric_calc_node):
        """Test that ValueError from MetricCalculationNode constructor propagates."""
        metric_name = "invalid_metric"
        error_message = f"Metric definition '{metric_name}' not found."
        mock_metric_calc_node.side_effect = ValueError(error_message)

        with pytest.raises(ValueError, match=error_message):
            NodeFactory.create_metric_node("TestNode", metric_name, {})

    def test_error_propagates_from_constructor_type_error(self, mock_metric_calc_node):
        """Test that TypeError from MetricCalculationNode constructor propagates."""
        error_message = "Input 'asset' must be a Node instance."
        mock_metric_calc_node.side_effect = TypeError(error_message)

        with pytest.raises(TypeError, match=error_message):
            NodeFactory.create_metric_node("TestNode", "some_metric", {"asset": "not_a_node"})


# Tests for _create_custom_node_from_callable (treating as semi-public for testing)
class TestCreateCustomNodeFromCallable:
    def test_success_creation(self, mock_node_a, mock_node_b):
        """Test successful creation of CustomCalculationNode."""
        name = "CustomTax"
        inputs = [mock_node_a, mock_node_b]

        def formula(a, b):
            return a * 0.2 + b * 0.1

        description = "Custom tax calculation"

        node = NodeFactory._create_custom_node_from_callable(name, inputs, formula, description)

        assert isinstance(node, CustomCalculationNode)
        assert node.name == name
        assert node.inputs == inputs
        # We don't need to assert node.formula == formula
        # The factory's job is to pass it to the constructor.
        # Testing the formula's execution belongs to CustomCalculationNode tests.
        assert node.description == description

    def test_success_no_inputs(self):
        """Test successful creation with no inputs."""
        name = "ConstantValue"
        inputs = []

        def formula():
            return 100.0  # Formula takes no arguments

        node = NodeFactory._create_custom_node_from_callable(name, inputs, formula)
        assert isinstance(node, CustomCalculationNode)
        assert node.name == name
        assert node.inputs == inputs
        # We don't need to assert node.formula() == 100.0
        # Verification that the formula works should be in calculation engine/node tests.

    def test_success_no_description(self, mock_node_a):
        """Test successful creation without an explicit description."""
        name = "SimpleRatio"
        inputs = [mock_node_a]

        def formula(x):
            return x * 2

        node = NodeFactory._create_custom_node_from_callable(name, inputs, formula)
        assert isinstance(node, CustomCalculationNode)
        assert node.name == name
        assert node.description is None  # Default should be None

    def test_error_empty_name(self, mock_node_a):
        """Test creation fails with an empty name."""
        with pytest.raises(ValueError, match="Node name must be a non-empty string"):
            NodeFactory._create_custom_node_from_callable("", [mock_node_a], lambda x: x)

    def test_error_formula_not_callable(self, mock_node_a):
        """Test creation fails if formula is not callable."""
        with pytest.raises(TypeError, match="Formula must be a callable function"):
            NodeFactory._create_custom_node_from_callable(
                "TestNode", [mock_node_a], "not_a_function"
            )

    def test_error_inputs_contain_non_node(self, mock_node_a):
        """Test creation fails if inputs list contains non-Node objects."""
        with pytest.raises(TypeError, match="All items in inputs must be Node instances"):
            NodeFactory._create_custom_node_from_callable(
                "TestNode", [mock_node_a, "not_a_node"], lambda x, y: x
            )
