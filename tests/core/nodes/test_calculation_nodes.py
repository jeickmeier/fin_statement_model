"""Tests for various CalculationNode implementations."""

import pytest
from unittest.mock import MagicMock, patch

from fin_statement_model.core.nodes.base import Node
from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode
from fin_statement_model.core.nodes.calculation_nodes import (
    FormulaCalculationNode,
    StrategyCalculationNode,
    MetricCalculationNode,
    CustomCalculationNode,
)
from fin_statement_model.core.errors import CalculationError, ConfigurationError, MetricError

# --- Fixtures ---


@pytest.fixture
def node_a() -> FinancialStatementItemNode:
    """Provides a simple input node A."""
    return FinancialStatementItemNode(name="NodeA", values={"2023": 10.0, "2024": 12.0})


@pytest.fixture
def node_b() -> FinancialStatementItemNode:
    """Provides a simple input node B."""
    return FinancialStatementItemNode(name="NodeB", values={"2023": 5.0, "2024": 4.0})


@pytest.fixture
def node_c() -> FinancialStatementItemNode:
    """Provides a simple input node C."""
    return FinancialStatementItemNode(name="NodeC", values={"2023": 2.0, "2024": 3.0})


@pytest.fixture
def non_numeric_node() -> MagicMock:
    """Provides a mock node that returns non-numeric values."""
    mock_node = MagicMock(spec=Node)
    mock_node.name = "NonNumericNode"
    mock_node.calculate.return_value = "not a number"
    return mock_node


# --- FormulaCalculationNode Tests ---


def test_formula_init_success(node_a: Node, node_b: Node):
    """Test successful initialization of FormulaCalculationNode."""
    inputs = {"a": node_a, "b": node_b}
    formula = "a + b * 2"
    node = FormulaCalculationNode(name="TestFormula", inputs=inputs, formula=formula)
    assert node.name == "TestFormula"
    assert node.inputs == inputs
    assert node.formula == formula
    assert node.has_calculation() is True
    assert node.get_dependencies() == ["NodeA", "NodeB"]


def test_formula_init_invalid_inputs_type(node_a: Node):
    """Test TypeError if inputs is not a dict."""
    with pytest.raises(TypeError, match="inputs must be a dict of Node instances"):
        FormulaCalculationNode(name="TestFormula", inputs=[node_a], formula="a + 1")


def test_formula_init_invalid_input_value_type():
    """Test TypeError if inputs dict contains non-Node values."""
    with pytest.raises(TypeError, match="inputs must be a dict of Node instances"):
        FormulaCalculationNode(name="TestFormula", inputs={"a": 123}, formula="a + 1")


def test_formula_init_invalid_formula_syntax(node_a: Node):
    """Test ValueError for invalid formula syntax."""
    with pytest.raises(ValueError, match="Invalid formula syntax"):
        FormulaCalculationNode(name="TestFormula", inputs={"a": node_a}, formula="a +")


@pytest.mark.parametrize(
    "formula, period, expected",
    [
        ("a + b", "2023", 15.0),  # Addition
        ("a - b", "2023", 5.0),  # Subtraction
        ("a * b", "2023", 50.0),  # Multiplication
        ("a / c", "2023", 5.0),  # Division
        ("-a", "2023", -10.0),  # Unary minus
        ("a + b * c", "2023", 20.0),  # Precedence
        ("(a + b) * c", "2023", 30.0),  # Parentheses
        ("a + 5.5", "2023", 15.5),  # Constant
        ("a + b", "2024", 16.0),  # Different period
        ("a / c", "2024", 4.0),  # Different period division
    ],
)
def test_formula_calculate_success(
    node_a: Node, node_b: Node, node_c: Node, formula: str, period: str, expected: float
):
    """Test successful formula calculations for various scenarios."""
    inputs = {"a": node_a, "b": node_b, "c": node_c}
    calc_node = FormulaCalculationNode(name="TestCalc", inputs=inputs, formula=formula)
    assert calc_node.calculate(period) == pytest.approx(expected)


def test_formula_calculate_unknown_variable(node_a: Node):
    """Test CalculationError for unknown variable in formula."""
    calc_node = FormulaCalculationNode(name="TestCalc", inputs={"a": node_a}, formula="a + x")
    with pytest.raises(CalculationError) as exc_info:
        calc_node.calculate("2023")
    assert "Unknown variable 'x'" in str(exc_info.value)
    assert exc_info.value.node_id == "TestCalc"
    assert exc_info.value.period == "2023"


def test_formula_calculate_non_numeric_input(node_a: Node, non_numeric_node: MagicMock):
    """Test CalculationError if an input node returns non-numeric."""
    calc_node = FormulaCalculationNode(
        name="TestCalc", inputs={"a": node_a, "non_num": non_numeric_node}, formula="a + non_num"
    )
    with pytest.raises(CalculationError) as exc_info:
        calc_node.calculate("2023")
    assert "did not return a numeric value" in str(exc_info.value)
    assert "NonNumericNode" in str(exc_info.value)
    assert exc_info.value.node_id == "TestCalc"


def test_formula_calculate_division_by_zero(node_a: Node):
    """Test CalculationError for division by zero."""
    zero_node = FinancialStatementItemNode("ZeroNode", values={"2023": 0.0})
    calc_node = FormulaCalculationNode(
        name="TestCalc", inputs={"a": node_a, "zero": zero_node}, formula="a / zero"
    )
    with pytest.raises(CalculationError) as exc_info:
        calc_node.calculate("2023")
    # The exact error message for ZeroDivisionError might vary slightly
    assert (
        "division by zero" in str(exc_info.value).lower()
        or "float division by zero" in str(exc_info.value).lower()
    )
    assert exc_info.value.node_id == "TestCalc"


def test_formula_calculate_unsupported_operator(node_a: Node, node_b: Node):
    """Test CalculationError for unsupported operators."""
    calc_node = FormulaCalculationNode(
        name="TestCalc", inputs={"a": node_a, "b": node_b}, formula="a ** b"
    )  # Exponentiation not supported
    with pytest.raises(CalculationError) as exc_info:
        calc_node.calculate("2023")
    assert "Unsupported syntax node type 'BinOp'" in str(
        exc_info.value
    ) or "Unsupported binary operator" in str(exc_info.value)


def test_formula_calculate_non_numeric_constant(node_a: Node):
    """Test CalculationError for non-numeric constants in formula."""
    calc_node = FormulaCalculationNode(name="TestCalc", inputs={"a": node_a}, formula="a + 'hello'")
    with pytest.raises(CalculationError) as exc_info:
        calc_node.calculate("2023")
    assert "Unsupported constant type 'str'" in str(exc_info.value)


# --- Add tests for Strategy, Metric, Custom nodes below ---

# === StrategyCalculationNode Fixtures and Tests ===


class MockSumStrategy:
    """A simple strategy for testing that sums inputs."""

    def calculate(self, inputs: list[Node], period: str) -> float:
        return sum(node.calculate(period) for node in inputs)


class MockProductStrategy:
    """A simple strategy for testing that multiplies inputs."""

    def calculate(self, inputs: list[Node], period: str) -> float:
        result = 1.0
        for node in inputs:
            result *= node.calculate(period)
        return result


class MockErrorStrategy:
    """A strategy that always raises an error."""

    def calculate(self, inputs: list[Node], period: str) -> float:
        raise ValueError("Strategy failed!")


class MockNonNumericStrategy:
    """A strategy that returns a non-numeric value."""

    def calculate(self, inputs: list[Node], period: str) -> str:
        return "not a number"


@pytest.fixture
def sum_strategy() -> MockSumStrategy:
    return MockSumStrategy()


@pytest.fixture
def product_strategy() -> MockProductStrategy:
    return MockProductStrategy()


@pytest.fixture
def error_strategy() -> MockErrorStrategy:
    return MockErrorStrategy()


@pytest.fixture
def non_numeric_strategy() -> MockNonNumericStrategy:
    return MockNonNumericStrategy()


def test_strategy_init_success(node_a: Node, node_b: Node, sum_strategy: MockSumStrategy):
    """Test successful initialization of StrategyCalculationNode."""
    inputs = [node_a, node_b]
    node = StrategyCalculationNode(name="TestStrategy", inputs=inputs, strategy=sum_strategy)
    assert node.name == "TestStrategy"
    assert node.inputs == inputs
    assert node.strategy == sum_strategy
    assert node.has_calculation() is True
    assert node.get_dependencies() == ["NodeA", "NodeB"]


def test_strategy_init_invalid_inputs_type(node_a: Node, sum_strategy: MockSumStrategy):
    """Test TypeError if inputs is not a list."""
    with pytest.raises(TypeError, match="inputs must be a list of Node instances"):
        StrategyCalculationNode(name="TestStrategy", inputs={"a": node_a}, strategy=sum_strategy)


def test_strategy_init_invalid_input_value_type(sum_strategy: MockSumStrategy):
    """Test TypeError if inputs list contains non-Node values."""
    with pytest.raises(TypeError, match="inputs must be a list of Node instances"):
        StrategyCalculationNode(name="TestStrategy", inputs=[123], strategy=sum_strategy)


def test_strategy_init_invalid_strategy_no_calculate():
    """Test TypeError if strategy object lacks a calculate method."""
    invalid_strategy = object()  # Plain object lacks calculate
    with pytest.raises(TypeError, match="Strategy object must have a callable 'calculate' method"):
        StrategyCalculationNode(name="TestStrategy", inputs=[], strategy=invalid_strategy)


def test_strategy_init_invalid_strategy_non_callable_calculate():
    """Test TypeError if strategy's calculate attribute is not callable."""

    class InvalidStrategy:
        calculate = 123  # Not callable

    with pytest.raises(TypeError, match="Strategy object must have a callable 'calculate' method"):
        StrategyCalculationNode(name="TestStrategy", inputs=[], strategy=InvalidStrategy())


def test_strategy_calculate_success(node_a: Node, node_b: Node, sum_strategy: MockSumStrategy):
    """Test successful calculation using the strategy."""
    node = StrategyCalculationNode(name="TestSum", inputs=[node_a, node_b], strategy=sum_strategy)
    assert node.calculate("2023") == pytest.approx(15.0)  # 10.0 + 5.0
    assert node.calculate("2024") == pytest.approx(16.0)  # 12.0 + 4.0


def test_strategy_calculate_caching(node_a: Node, node_b: Node, sum_strategy: MockSumStrategy):
    """Test that results are cached after the first calculation."""
    mock_strategy = MagicMock(wraps=sum_strategy)
    node = StrategyCalculationNode(
        name="TestCache", inputs=[node_a, node_b], strategy=mock_strategy
    )

    # First call - should call strategy
    assert node.calculate("2023") == pytest.approx(15.0)
    mock_strategy.calculate.assert_called_once_with([node_a, node_b], "2023")

    # Second call - should use cache, not call strategy again
    mock_strategy.calculate.reset_mock()
    assert node.calculate("2023") == pytest.approx(15.0)
    mock_strategy.calculate.assert_not_called()


def test_strategy_clear_cache(node_a: Node, node_b: Node, sum_strategy: MockSumStrategy):
    """Test that clear_cache empties the cache."""
    mock_strategy = MagicMock(wraps=sum_strategy)
    node = StrategyCalculationNode(
        name="TestClearCache", inputs=[node_a, node_b], strategy=mock_strategy
    )

    # Calculate to populate cache
    node.calculate("2023")
    mock_strategy.calculate.assert_called_once()

    # Clear cache and calculate again - should call strategy again
    node.clear_cache()
    mock_strategy.calculate.reset_mock()
    assert node.calculate("2023") == pytest.approx(15.0)
    mock_strategy.calculate.assert_called_once_with([node_a, node_b], "2023")


def test_strategy_set_strategy(
    node_a: Node, node_b: Node, sum_strategy: MockSumStrategy, product_strategy: MockProductStrategy
):
    """Test changing the strategy and recalculating."""
    mock_sum_strategy = MagicMock(wraps=sum_strategy)
    mock_product_strategy = MagicMock(wraps=product_strategy)

    node = StrategyCalculationNode(
        name="TestSetStrategy", inputs=[node_a, node_b], strategy=mock_sum_strategy
    )

    # Calculate with sum strategy
    assert node.calculate("2023") == pytest.approx(15.0)
    mock_sum_strategy.calculate.assert_called_once()
    mock_product_strategy.calculate.assert_not_called()

    # Change strategy to product
    node.set_strategy(mock_product_strategy)
    assert node.strategy == mock_product_strategy

    # Recalculate - should use product strategy (cache was cleared)
    mock_sum_strategy.calculate.reset_mock()
    assert node.calculate("2023") == pytest.approx(50.0)  # 10.0 * 5.0
    mock_sum_strategy.calculate.assert_not_called()
    mock_product_strategy.calculate.assert_called_once_with([node_a, node_b], "2023")


def test_strategy_set_invalid_strategy(node_a: Node, node_b: Node, sum_strategy: MockSumStrategy):
    """Test TypeError when setting an invalid strategy."""
    node = StrategyCalculationNode(
        name="TestSetInvalid", inputs=[node_a, node_b], strategy=sum_strategy
    )
    invalid_strategy = object()
    with pytest.raises(
        TypeError, match="New strategy object must have a callable 'calculate' method"
    ):
        node.set_strategy(invalid_strategy)


def test_strategy_calculate_error_in_strategy(
    node_a: Node, node_b: Node, error_strategy: MockErrorStrategy
):
    """Test CalculationError when the strategy raises an exception."""
    node = StrategyCalculationNode(
        name="TestErrorStrategy", inputs=[node_a, node_b], strategy=error_strategy
    )
    with pytest.raises(CalculationError) as exc_info:
        node.calculate("2023")
    assert "Error during strategy calculation" in str(exc_info.value)
    assert "Strategy failed!" in str(exc_info.value)
    assert exc_info.value.node_id == "TestErrorStrategy"
    assert exc_info.value.period == "2023"


def test_strategy_calculate_non_numeric_return(
    node_a: Node, node_b: Node, non_numeric_strategy: MockNonNumericStrategy
):
    """Test CalculationError when the strategy returns a non-numeric value."""
    node = StrategyCalculationNode(
        name="TestNonNumericStrategy", inputs=[node_a, node_b], strategy=non_numeric_strategy
    )
    with pytest.raises(CalculationError) as exc_info:
        node.calculate("2023")
    assert "did not return a numeric value" in str(exc_info.value)
    assert "got str" in str(exc_info.value)
    assert exc_info.value.node_id == "TestNonNumericStrategy"
    assert exc_info.value.period == "2023"


# --- Add tests for Metric, Custom nodes below ---

# === MetricCalculationNode Fixtures and Tests ===


@pytest.fixture
def mock_metric_registry() -> MagicMock:
    """Provides a mock metric registry for testing."""
    registry = MagicMock()
    registry.get.return_value = {
        "inputs": ["input_a", "input_b"],  # Corresponds to variable names in formula
        "formula": "input_a - input_b",
        "description": "Test metric subtracting B from A",
    }
    # Simulate registry raising KeyError for unknown metrics
    registry.get.side_effect = (
        lambda key: registry.return_value
        if key == "test_metric"
        else (_ for _ in ()).throw(KeyError(f"Metric '{key}' not found"))
    )

    return registry


@pytest.fixture
def metric_input_nodes(node_a: Node, node_b: Node) -> dict[str, Node]:
    """Provides input nodes mapped to metric input names."""
    # Map the logical metric input names to actual node instances
    return {"input_a": node_a, "input_b": node_b}


# Use patch to replace the actual registry during tests for this class
@patch("fin_statement_model.core.nodes.calculation_nodes.metric_registry", new_callable=MagicMock)
def test_metric_init_success(
    mock_registry: MagicMock, metric_input_nodes: dict[str, Node], node_a: Node, node_b: Node
):
    """Test successful initialization of MetricCalculationNode."""
    # Configure the mock registry for this specific test
    mock_registry.get.return_value = {
        "inputs": ["input_a", "input_b"],
        "formula": "input_a - input_b",
        "description": "Test metric",
    }
    mock_registry.get.side_effect = None  # Clear side effect for this test

    node = MetricCalculationNode(
        name="TestMetric", metric_name="test_metric", input_nodes=metric_input_nodes
    )
    assert node.name == "TestMetric"
    assert node.metric_name == "test_metric"
    assert node.definition == mock_registry.get.return_value
    assert node.has_calculation() is True
    # get_dependencies should return logical dependencies from definition
    assert node.get_dependencies() == ["input_a", "input_b"]
    # Check internal calc_node was created
    assert isinstance(node.calc_node, FormulaCalculationNode)
    assert node.calc_node.name == "_TestMetric_formula_calc"
    assert node.calc_node.formula == "input_a - input_b"
    # Check the internal calc_node received the correctly mapped nodes
    assert node.calc_node.inputs == metric_input_nodes


@patch("fin_statement_model.core.nodes.calculation_nodes.metric_registry", new_callable=MagicMock)
def test_metric_init_metric_not_found(
    mock_registry: MagicMock, metric_input_nodes: dict[str, Node]
):
    """Test ConfigurationError if metric name is not in the registry."""
    mock_registry.get.side_effect = KeyError("Metric 'unknown_metric' not found")

    with pytest.raises(ConfigurationError, match="Metric definition 'unknown_metric' not found"):
        MetricCalculationNode(
            name="TestMetricNotFound", metric_name="unknown_metric", input_nodes=metric_input_nodes
        )


@patch("fin_statement_model.core.nodes.calculation_nodes.metric_registry", new_callable=MagicMock)
def test_metric_init_invalid_definition(
    mock_registry: MagicMock, metric_input_nodes: dict[str, Node]
):
    """Test MetricError if the retrieved metric definition is invalid (missing fields)."""
    mock_registry.get.return_value = {"inputs": ["a"]}  # Missing 'formula'
    mock_registry.get.side_effect = None

    with pytest.raises(MetricError, match="Metric definition .* is invalid. Missing fields"):
        MetricCalculationNode(
            name="TestInvalidMetric", metric_name="test_metric", input_nodes=metric_input_nodes
        )


@patch("fin_statement_model.core.nodes.calculation_nodes.metric_registry", new_callable=MagicMock)
def test_metric_init_input_node_mismatch_missing(mock_registry: MagicMock, node_a: Node):
    """Test MetricError if a required input node is missing."""
    mock_registry.get.return_value = {"inputs": ["req_a", "req_b"], "formula": "req_a + req_b"}
    mock_registry.get.side_effect = None

    with pytest.raises(
        MetricError, match="Input nodes mismatch.*missing required inputs: {'req_b'}"
    ):
        MetricCalculationNode(
            name="TestMissingInput", metric_name="test_metric", input_nodes={"req_a": node_a}
        )


@patch("fin_statement_model.core.nodes.calculation_nodes.metric_registry", new_callable=MagicMock)
def test_metric_init_input_node_mismatch_extra(
    mock_registry: MagicMock, metric_input_nodes: dict[str, Node], node_c: Node
):
    """Test MetricError if an extra, unrequired input node is provided."""
    mock_registry.get.return_value = {
        "inputs": ["input_a", "input_b"],
        "formula": "input_a - input_b",
    }
    mock_registry.get.side_effect = None
    extra_input_nodes = metric_input_nodes.copy()
    extra_input_nodes["extra_c"] = node_c

    with pytest.raises(
        MetricError, match="Input nodes mismatch.*unexpected inputs provided: {'extra_c'}"
    ):
        MetricCalculationNode(
            name="TestExtraInput", metric_name="test_metric", input_nodes=extra_input_nodes
        )


@patch("fin_statement_model.core.nodes.calculation_nodes.metric_registry", new_callable=MagicMock)
def test_metric_init_invalid_input_nodes_type(mock_registry: MagicMock):
    """Test TypeError if input_nodes is not a dict of Nodes."""
    mock_registry.get.return_value = {"inputs": ["a"], "formula": "a * 2"}
    mock_registry.get.side_effect = None

    with pytest.raises(
        TypeError, match="MetricCalculationNode input_nodes must be a dict of Node instances"
    ):
        MetricCalculationNode(
            name="TestInvalidType", metric_name="test_metric", input_nodes={"a": 123}
        )


@patch("fin_statement_model.core.nodes.calculation_nodes.metric_registry", new_callable=MagicMock)
def test_metric_calculate_success(mock_registry: MagicMock, metric_input_nodes: dict[str, Node]):
    """Test successful calculation by delegating to the internal formula node."""
    mock_registry.get.return_value = {
        "inputs": ["input_a", "input_b"],
        "formula": "input_a - input_b",
    }
    mock_registry.get.side_effect = None

    node = MetricCalculationNode(
        name="TestMetricCalc", metric_name="test_metric", input_nodes=metric_input_nodes
    )
    # node_a=10, node_b=5 for 2023 -> 10 - 5 = 5
    assert node.calculate("2023") == pytest.approx(5.0)
    # node_a=12, node_b=4 for 2024 -> 12 - 4 = 8
    assert node.calculate("2024") == pytest.approx(8.0)


@patch("fin_statement_model.core.nodes.calculation_nodes.metric_registry", new_callable=MagicMock)
def test_metric_calculate_internal_formula_error(
    mock_registry: MagicMock, metric_input_nodes: dict[str, Node]
):
    """Test that CalculationError from internal formula node is re-raised correctly."""
    # Setup a metric with a formula that will cause division by zero
    zero_node = FinancialStatementItemNode("ZeroNode", values={"2023": 0.0})
    mock_registry.get.return_value = {"inputs": ["input_a", "zero"], "formula": "input_a / zero"}
    mock_registry.get.side_effect = None

    # Create a dictionary with only the required nodes for this metric
    required_nodes = {
        "input_a": metric_input_nodes["input_a"],  # Get node_a from the fixture
        "zero": zero_node,
    }

    node = MetricCalculationNode(
        name="TestMetricDivZero", metric_name="div_zero_metric", input_nodes=required_nodes
    )

    with pytest.raises(CalculationError) as exc_info:
        node.calculate("2023")

    # Check that the error message includes metric context and the original error
    assert "Error calculating metric 'div_zero_metric'" in str(exc_info.value)
    assert f"for node '{node.name}'" in str(exc_info.value)  # Check the correct node ID
    assert f"and period '{exc_info.value.period}'" in str(exc_info.value)  # Check period
    # Check that the original error detail (division by zero) is present
    original_error_str = exc_info.value.details.get("original_error", "")
    assert (
        "division by zero" in original_error_str.lower()
        or "float division by zero" in original_error_str.lower()
    )
    assert exc_info.value.node_id == "TestMetricDivZero"  # Check attribute directly
    assert exc_info.value.period == "2023"
    assert exc_info.value.details["metric_name"] == "div_zero_metric"


# --- Add tests for Custom nodes below ---

# === CustomCalculationNode Fixtures and Tests ===


def custom_sum_func(val_a: float, val_b: float) -> float:
    """Simple custom function for testing: adds two values."""
    return val_a + val_b


def custom_logic_func(a: float, b: float, c: float) -> float:
    """More complex custom function for testing."""
    return (a + b) / c if c != 0 else 0.0


def custom_error_func(a: float, b: float) -> float:
    """Custom function that raises an error."""
    raise ValueError("Custom function failed!")


def custom_non_numeric_func(a: float, b: float) -> str:
    """Custom function that returns a non-numeric value."""
    return f"{a} + {b}"


def test_custom_init_success(node_a: Node, node_b: Node):
    """Test successful initialization of CustomCalculationNode."""
    inputs = [node_a, node_b]
    node = CustomCalculationNode(
        name="TestCustom", inputs=inputs, formula_func=custom_sum_func, description="Adds A and B"
    )
    assert node.name == "TestCustom"
    assert node.inputs == inputs
    assert node.formula_func == custom_sum_func
    assert node.description == "Adds A and B"
    assert node.has_calculation() is True
    assert node.get_dependencies() == ["NodeA", "NodeB"]


def test_custom_init_invalid_inputs_type(node_a: Node):
    """Test TypeError if inputs is not a list."""
    with pytest.raises(
        TypeError, match="CustomCalculationNode inputs must be a list of Node instances"
    ):
        CustomCalculationNode(name="TestCustom", inputs={"a": node_a}, formula_func=custom_sum_func)


def test_custom_init_invalid_input_value_type():
    """Test TypeError if inputs list contains non-Node values."""
    with pytest.raises(
        TypeError, match="CustomCalculationNode inputs must be a list of Node instances"
    ):
        CustomCalculationNode(name="TestCustom", inputs=[123], formula_func=custom_sum_func)


def test_custom_init_invalid_formula_func_type(node_a: Node):
    """Test TypeError if formula_func is not callable."""
    with pytest.raises(
        TypeError, match="CustomCalculationNode formula_func must be a callable function"
    ):
        CustomCalculationNode(name="TestCustom", inputs=[node_a], formula_func=123)


def test_custom_calculate_success(node_a: Node, node_b: Node, node_c: Node):
    """Test successful calculation using the custom function."""
    sum_node = CustomCalculationNode(
        name="TestSumCustom", inputs=[node_a, node_b], formula_func=custom_sum_func
    )
    logic_node = CustomCalculationNode(
        name="TestLogicCustom", inputs=[node_a, node_b, node_c], formula_func=custom_logic_func
    )

    # Test sum_node
    assert sum_node.calculate("2023") == pytest.approx(15.0)  # 10.0 + 5.0
    assert sum_node.calculate("2024") == pytest.approx(16.0)  # 12.0 + 4.0

    # Test logic_node
    assert logic_node.calculate("2023") == pytest.approx(7.5)  # (10.0 + 5.0) / 2.0
    assert logic_node.calculate("2024") == pytest.approx(5.333333)  # (12.0 + 4.0) / 3.0


def test_custom_calculate_error_in_function(node_a: Node, node_b: Node):
    """Test CalculationError when the custom function raises an exception."""
    node = CustomCalculationNode(
        name="TestErrorFunc", inputs=[node_a, node_b], formula_func=custom_error_func
    )
    with pytest.raises(CalculationError) as exc_info:
        node.calculate("2023")
    assert "Error during custom calculation" in str(exc_info.value)
    assert "Custom function failed!" in str(exc_info.value)
    assert exc_info.value.node_id == "TestErrorFunc"
    assert exc_info.value.period == "2023"
    assert exc_info.value.details["function"] == "custom_error_func"


def test_custom_calculate_non_numeric_return(node_a: Node, node_b: Node):
    """Test CalculationError when the custom function returns a non-numeric value."""
    node = CustomCalculationNode(
        name="TestNonNumericFunc", inputs=[node_a, node_b], formula_func=custom_non_numeric_func
    )
    with pytest.raises(CalculationError) as exc_info:
        node.calculate("2023")
    assert "did not return a numeric value" in str(exc_info.value)
    assert "Got str" in str(exc_info.value)
    assert exc_info.value.node_id == "TestNonNumericFunc"
    assert exc_info.value.period == "2023"
    assert exc_info.value.details["function"] == "custom_non_numeric_func"


def test_custom_calculate_input_node_error(non_numeric_node: MagicMock, node_b: Node):
    """Test CalculationError when an input node fails calculation or returns non-numeric."""
    # Use the non_numeric_node fixture which returns a string
    node = CustomCalculationNode(
        name="TestInputError", inputs=[non_numeric_node, node_b], formula_func=custom_sum_func
    )

    with pytest.raises(CalculationError) as exc_info:
        node.calculate("2023")

    # Check that the error indicates the input node failed to provide a numeric value
    assert "Input node 'NonNumericNode'" in str(exc_info.value)
    assert "did not return a numeric value" in str(exc_info.value)
    assert "Got str" in str(exc_info.value)
    assert exc_info.value.node_id == "TestInputError"
    assert exc_info.value.period == "2023"


# Final check: Ensure no placeholders remain
# (The placeholder comment is removed by adding these tests)
