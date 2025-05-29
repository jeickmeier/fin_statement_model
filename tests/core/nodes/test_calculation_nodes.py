"""Tests for various CalculationNode implementations."""

import pytest
from unittest.mock import MagicMock

from fin_statement_model.core.nodes.base import Node
from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode
from fin_statement_model.core.nodes.calculation_nodes import (
    FormulaCalculationNode,
    CalculationNode,
    CustomCalculationNode,
)
from fin_statement_model.core.errors import CalculationError

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
    assert node.inputs_dict == inputs
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
    ("formula", "period", "expected"),
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
    calc_node = FormulaCalculationNode(
        name="TestCalc", inputs={"a": node_a}, formula="a + x"
    )
    with pytest.raises(CalculationError) as exc_info:
        calc_node.calculate("2023")
    assert "Unknown variable 'x'" in str(exc_info.value)
    assert exc_info.value.node_id == "TestCalc"
    assert exc_info.value.period == "2023"


def test_formula_calculate_non_numeric_input(node_a: Node, non_numeric_node: MagicMock):
    """Test CalculationError if an input node returns non-numeric."""
    calc_node = FormulaCalculationNode(
        name="TestCalc",
        inputs={"a": node_a, "non_num": non_numeric_node},
        formula="a + non_num",
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
    calc_node = FormulaCalculationNode(
        name="TestCalc", inputs={"a": node_a}, formula="a + 'hello'"
    )
    with pytest.raises(CalculationError) as exc_info:
        calc_node.calculate("2023")
    assert "Unsupported constant type 'str'" in str(exc_info.value)


# --- Add tests for Strategy, Metric, Custom nodes below ---

# === StrategyCalculationNode Fixtures and Tests ===


class MockSumStrategy:
    """A simple strategy for testing that sums inputs."""

    def calculate(self, inputs: list[Node], period: str) -> float:
        """Calculates the sum of input node values for the period."""
        return sum(node.calculate(period) for node in inputs)


class MockProductStrategy:
    """A simple strategy for testing that multiplies inputs."""

    def calculate(self, inputs: list[Node], period: str) -> float:
        """Calculates the product of input node values for the period."""
        result = 1.0
        for node in inputs:
            result *= node.calculate(period)
        return result


class MockErrorStrategy:
    """A strategy that always raises an error."""

    def calculate(self, inputs: list[Node], period: str) -> float:
        """Raises a ValueError to simulate strategy failure."""
        raise ValueError("Strategy failed!")


class MockNonNumericStrategy:
    """A strategy that returns a non-numeric value."""

    def calculate(self, inputs: list[Node], period: str) -> str:
        """Returns a string, violating the expected numeric return type."""
        return "not a number"


@pytest.fixture
def sum_strategy() -> MockSumStrategy:
    """Provides an instance of MockSumStrategy."""
    return MockSumStrategy()


@pytest.fixture
def product_strategy() -> MockProductStrategy:
    """Provides an instance of MockProductStrategy."""
    return MockProductStrategy()


@pytest.fixture
def error_strategy() -> MockErrorStrategy:
    """Provides an instance of MockErrorStrategy."""
    return MockErrorStrategy()


@pytest.fixture
def non_numeric_strategy() -> MockNonNumericStrategy:
    """Provides an instance of MockNonNumericStrategy."""
    return MockNonNumericStrategy()


def test_strategy_init_success(
    node_a: Node, node_b: Node, sum_strategy: MockSumStrategy
):
    """Test successful initialization of CalculationNode with a strategy."""
    inputs = [node_a, node_b]
    node = CalculationNode(name="TestStrategy", inputs=inputs, calculation=sum_strategy)
    assert node.name == "TestStrategy"
    assert node.inputs == inputs
    assert node.calculation == sum_strategy
    assert node.has_calculation() is True
    assert node.get_dependencies() == ["NodeA", "NodeB"]


def test_strategy_init_invalid_inputs_type(node_a: Node, sum_strategy: MockSumStrategy):
    """Test TypeError if inputs is not a list."""
    with pytest.raises(
        TypeError, match="CalculationNode inputs must be a list of Node instances"
    ):
        CalculationNode(
            name="TestStrategy", inputs={"a": node_a}, calculation=sum_strategy
        )


def test_strategy_init_invalid_input_value_type(sum_strategy: MockSumStrategy):
    """Test TypeError if inputs list contains non-Node values."""
    with pytest.raises(
        TypeError, match="CalculationNode inputs must be a list of Node instances"
    ):
        CalculationNode(name="TestStrategy", inputs=[123], calculation=sum_strategy)


def test_strategy_init_invalid_strategy_no_calculate():
    """Test TypeError if calculation object lacks a calculate method."""
    invalid_calculation = object()  # Plain object lacks calculate
    with pytest.raises(
        TypeError, match="Calculation object must have a callable 'calculate' method"
    ):
        CalculationNode(name="TestStrategy", inputs=[], calculation=invalid_calculation)


def test_strategy_init_invalid_strategy_non_callable_calculate():
    """Test TypeError if calculation's calculate attribute is not callable."""

    class InvalidCalculation:
        calculate = 123  # Not callable

    with pytest.raises(
        TypeError, match="Calculation object must have a callable 'calculate' method"
    ):
        CalculationNode(
            name="TestStrategy", inputs=[], calculation=InvalidCalculation()
        )


def test_strategy_calculate_success(
    node_a: Node, node_b: Node, sum_strategy: MockSumStrategy
):
    """Test successful calculation using the strategy via CalculationNode."""
    node = CalculationNode(
        name="TestSum", inputs=[node_a, node_b], calculation=sum_strategy
    )
    assert node.calculate("2023") == pytest.approx(15.0)  # 10.0 + 5.0
    assert node.calculate("2024") == pytest.approx(16.0)  # 12.0 + 4.0


def test_strategy_calculate_caching(
    node_a: Node, node_b: Node, sum_strategy: MockSumStrategy
):
    """Test that results are cached after the first calculation."""
    mock_strategy = MagicMock(wraps=sum_strategy)
    node = CalculationNode(
        name="TestCache", inputs=[node_a, node_b], calculation=mock_strategy
    )

    # First call - should call strategy
    assert node.calculate("2023") == pytest.approx(15.0)
    mock_strategy.calculate.assert_called_once_with([node_a, node_b], "2023")

    # Second call - should use cache, not call strategy again
    mock_strategy.calculate.reset_mock()
    assert node.calculate("2023") == pytest.approx(15.0)
    mock_strategy.calculate.assert_not_called()


def test_strategy_clear_cache(
    node_a: Node, node_b: Node, sum_strategy: MockSumStrategy
):
    """Test that clear_cache empties the cache."""
    mock_strategy = MagicMock(wraps=sum_strategy)
    node = CalculationNode(
        name="TestClearCache", inputs=[node_a, node_b], calculation=mock_strategy
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
    node_a: Node,
    node_b: Node,
    sum_strategy: MockSumStrategy,
    product_strategy: MockProductStrategy,
):
    """Test changing the calculation object and recalculating."""
    mock_sum_strategy = MagicMock(wraps=sum_strategy)
    mock_product_strategy = MagicMock(wraps=product_strategy)

    node = CalculationNode(
        name="TestSetStrategy", inputs=[node_a, node_b], calculation=mock_sum_strategy
    )

    # Calculate with sum strategy
    assert node.calculate("2023") == pytest.approx(15.0)
    mock_sum_strategy.calculate.assert_called_once()
    mock_product_strategy.calculate.assert_not_called()

    # Change strategy to product
    node.set_calculation(mock_product_strategy)
    assert node.calculation == mock_product_strategy

    # Recalculate - should use product strategy (cache was cleared)
    mock_sum_strategy.calculate.reset_mock()
    assert node.calculate("2023") == pytest.approx(50.0)  # 10.0 * 5.0
    mock_sum_strategy.calculate.assert_not_called()
    mock_product_strategy.calculate.assert_called_once_with([node_a, node_b], "2023")


def test_strategy_set_invalid_strategy(
    node_a: Node, node_b: Node, sum_strategy: MockSumStrategy
):
    """Test TypeError when setting an invalid calculation object."""
    node = CalculationNode(
        name="TestSetInvalid", inputs=[node_a, node_b], calculation=sum_strategy
    )
    invalid_calculation = object()
    with pytest.raises(
        TypeError,
        match="New calculation object must have a callable 'calculate' method",
    ):
        node.set_calculation(invalid_calculation)


def test_strategy_calculate_error_in_strategy(
    node_a: Node, node_b: Node, error_strategy: MockErrorStrategy
):
    """Test CalculationError when the calculation object raises an exception."""
    node = CalculationNode(
        name="TestErrorStrategy", inputs=[node_a, node_b], calculation=error_strategy
    )
    with pytest.raises(CalculationError) as exc_info:
        node.calculate("2023")
    assert "Error during calculation for node" in str(exc_info.value)
    assert "Strategy failed!" in str(exc_info.value)
    assert exc_info.value.node_id == "TestErrorStrategy"
    assert exc_info.value.period == "2023"


def test_strategy_calculate_non_numeric_return(
    node_a: Node, node_b: Node, non_numeric_strategy: MockNonNumericStrategy
):
    """Test CalculationError when the calculation object returns a non-numeric value."""
    node = CalculationNode(
        name="TestNonNumericStrategy",
        inputs=[node_a, node_b],
        calculation=non_numeric_strategy,
    )
    with pytest.raises(CalculationError) as exc_info:
        node.calculate("2023")
    assert "did not return a numeric value" in str(exc_info.value)
    assert "got MockNonNumericStrategy" in str(exc_info.value)
    assert exc_info.value.node_id == "TestNonNumericStrategy"
    assert exc_info.value.period == "2023"


# --- Add tests for Metric, Custom nodes below ---

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
        name="TestCustom",
        inputs=inputs,
        formula_func=custom_sum_func,
        description="Adds A and B",
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
        CustomCalculationNode(
            name="TestCustom", inputs={"a": node_a}, formula_func=custom_sum_func
        )


def test_custom_init_invalid_input_value_type():
    """Test TypeError if inputs list contains non-Node values."""
    with pytest.raises(
        TypeError, match="CustomCalculationNode inputs must be a list of Node instances"
    ):
        CustomCalculationNode(
            name="TestCustom", inputs=[123], formula_func=custom_sum_func
        )


def test_custom_init_invalid_formula_func_type(node_a: Node):
    """Test TypeError if formula_func is not callable."""
    with pytest.raises(
        TypeError,
        match="CustomCalculationNode formula_func must be a callable function",
    ):
        CustomCalculationNode(name="TestCustom", inputs=[node_a], formula_func=123)


def test_custom_calculate_success(node_a: Node, node_b: Node, node_c: Node):
    """Test successful calculation using the custom function."""
    sum_node = CustomCalculationNode(
        name="TestSumCustom", inputs=[node_a, node_b], formula_func=custom_sum_func
    )
    logic_node = CustomCalculationNode(
        name="TestLogicCustom",
        inputs=[node_a, node_b, node_c],
        formula_func=custom_logic_func,
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
        name="TestNonNumericFunc",
        inputs=[node_a, node_b],
        formula_func=custom_non_numeric_func,
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
        name="TestInputError",
        inputs=[non_numeric_node, node_b],
        formula_func=custom_sum_func,
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
