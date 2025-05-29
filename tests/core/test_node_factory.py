"""Unit tests for the NodeFactory in fin_statement_model.core.node_factory."""

import pytest
from unittest.mock import patch, MagicMock, create_autospec
import re

# Imports from the module under test
from fin_statement_model.core.node_factory import NodeFactory
from fin_statement_model.core.nodes import (
    Node,
    FinancialStatementItemNode,
    CalculationNode,
    CustomCalculationNode,
)
from fin_statement_model.core.calculations import Registry, Calculation

# Import calculation classes to ensure registration


# --- Fixtures ---


@pytest.fixture
def mock_registry_get() -> MagicMock:
    """Fixture to mock the Registry.get method."""
    with patch.object(Registry, "get", autospec=True) as mock_get:
        yield mock_get


@pytest.fixture
def mock_node_a() -> Node:
    """Fixture for a generic mock Node."""
    mock = create_autospec(Node, instance=True)
    mock.name = "NodeA"
    return mock


@pytest.fixture
def mock_node_b() -> Node:
    """Fixture for another generic mock Node."""
    mock = create_autospec(Node, instance=True)
    mock.name = "NodeB"
    return mock


@pytest.fixture
def mock_strategy_class() -> MagicMock:
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
    """Tests the `NodeFactory.create_financial_statement_item` method."""

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
    """Tests the `NodeFactory.create_calculation_node` method."""

    def test_success_creation(
        self,
        mock_registry_get: MagicMock,
        mock_strategy_class: MagicMock,
        mock_node_a: Node,
        mock_node_b: Node,
    ) -> None:
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
        self,
        mock_registry_get: MagicMock,
        mock_strategy_class: MagicMock,
        mock_node_a: Node,
        mock_node_b: Node,
    ) -> None:
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

    def test_error_empty_name(self, mock_node_a: Node) -> None:
        """Test creation fails with an empty name."""
        with pytest.raises(ValueError, match="Node name must be a non-empty string"):
            NodeFactory.create_calculation_node("", [mock_node_a], "addition")

    def test_error_empty_inputs(self):
        """Test creation fails with an empty input list."""
        with pytest.raises(ValueError, match="Calculation node must have at least one input"):
            NodeFactory.create_calculation_node("TestNode", [], "addition")

    def test_error_invalid_calculation_type(self, mock_node_a: Node) -> None:
        """Test creation fails with an unknown calculation type."""
        invalid_type = "non_existent_type"
        with pytest.raises(ValueError, match=f"Invalid calculation type: '{invalid_type}'"):
            NodeFactory.create_calculation_node("TestNode", [mock_node_a], invalid_type)

    def test_error_strategy_not_in_registry(
        self, mock_registry_get: MagicMock, mock_node_a: Node
    ) -> None:
        """Test creation fails if the strategy is not found in the Registry."""
        calc_type = "addition"
        calculation_name = NodeFactory._calculation_methods[calc_type]
        mock_registry_get.side_effect = KeyError(f"Strategy '{calculation_name}' not found")

        with pytest.raises(
            ValueError,
            match=re.escape(
                f"Calculation class '{calculation_name}' (for type '{calc_type}') not found in Registry."
            ),
        ):
            NodeFactory.create_calculation_node("TestNode", [mock_node_a], calc_type)

    def test_error_strategy_instantiation_fails(
        self,
        mock_registry_get: MagicMock,
        mock_strategy_class: MagicMock,
        mock_node_a: Node,
    ) -> None:
        """Test creation fails if strategy instantiation fails (e.g., missing kwargs)."""
        mock_registry_get.return_value = mock_strategy_class
        # Simulate TypeError during __init__
        mock_strategy_class.side_effect = TypeError("Missing required argument 'weights'")
        calc_type = "weighted_average"  # Assume this requires 'weights'
        calculation_name = NodeFactory._calculation_methods[calc_type]

        # Match the more detailed error message from NodeFactory
        expected_match = (
            f"Could not instantiate calculation '{calculation_name}' for node 'TestNode'. "
            rf"Check required arguments for .*\. Provided kwargs: {{}}"
        )
        with pytest.raises(TypeError, match=expected_match):
            NodeFactory.create_calculation_node("TestNode", [mock_node_a], calc_type)


# Tests for _create_custom_node_from_callable (treating as semi-public for testing)
class TestCreateCustomNodeFromCallable:
    """Tests the `NodeFactory._create_custom_node_from_callable` helper method."""

    def test_success_creation(self, mock_node_a: Node, mock_node_b: Node):
        """Test successful creation of CustomCalculationNode."""
        name = "CustomTax"
        inputs = [mock_node_a, mock_node_b]

        def formula(a: float, b: float) -> float:
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

        def formula() -> float:
            return 100.0  # Formula takes no arguments

        node = NodeFactory._create_custom_node_from_callable(name, inputs, formula)
        assert isinstance(node, CustomCalculationNode)
        assert node.name == name
        assert node.inputs == inputs
        # We don't need to assert node.formula() == 100.0
        # Verification that the formula works should be in calculation engine/node tests.

    def test_success_no_description(self, mock_node_a: Node):
        """Test successful creation without an explicit description."""
        name = "SimpleRatio"
        inputs = [mock_node_a]

        def formula(x: float) -> float:
            return x * 2

        node = NodeFactory._create_custom_node_from_callable(name, inputs, formula)
        assert isinstance(node, CustomCalculationNode)
        assert node.name == name
        assert node.description is None  # Default should be None

    def test_error_empty_name(self, mock_node_a: Node):
        """Test creation fails with an empty name."""
        with pytest.raises(ValueError, match="Node name must be a non-empty string"):
            NodeFactory._create_custom_node_from_callable("", [mock_node_a], lambda x: x)

    def test_error_formula_not_callable(self, mock_node_a: Node):
        """Test creation fails if formula is not callable."""
        with pytest.raises(TypeError, match="Formula must be a callable function"):
            NodeFactory._create_custom_node_from_callable(
                "TestNode", [mock_node_a], "not_a_function"
            )

    def test_error_inputs_contain_non_node(self, mock_node_a: Node):
        """Test creation fails if inputs list contains non-Node objects."""
        with pytest.raises(TypeError, match="All items in inputs must be Node instances"):
            NodeFactory._create_custom_node_from_callable(
                "TestNode", [mock_node_a, "not_a_node"], lambda x, y: x
            )
