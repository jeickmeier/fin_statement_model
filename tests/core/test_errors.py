import pytest

from fin_statement_model.core.errors import (
    CalculationError,
    CircularDependencyError,
    ConfigurationError,
    DataValidationError,
    ExportError,
    FinancialModelError,
    GraphError,
    ImportError,
    MetricError,
    MissingInputError,
    NodeError,
    PeriodError,
    StatementError,
    StrategyError,
    TransformationError,
)


def test_financial_model_error_instantiation():
    """Test basic instantiation of the base error class."""
    message = "Base error message"
    err = FinancialModelError(message)
    assert err.message == message
    assert str(err) == message


@pytest.mark.parametrize(
    "message, config_path, errors, expected_str",
    [
        ("Base msg", None, None, "Base msg"),
        ("Base msg", "path/to/config.yaml", None, "Base msg in path/to/config.yaml"),
        ("Base msg", None, ["err1", "err2"], "Base msg: err1; err2"),
        (
            "Base msg",
            "path/to/config.yaml",
            ["err1", "err2"],
            "Base msg in path/to/config.yaml: err1; err2",
        ),
    ],
)
def test_configuration_error_instantiation(message, config_path, errors, expected_str):
    """Test ConfigurationError instantiation and message formatting."""
    err = ConfigurationError(message, config_path=config_path, errors=errors)
    assert err.config_path == config_path
    assert err.errors == (errors or [])
    assert str(err) == expected_str
    assert isinstance(err, FinancialModelError)


@pytest.mark.parametrize(
    "message, node_id, period, details, expected_str",
    [
        ("Base msg", None, None, None, "Base msg"),
        ("Base msg", "node1", None, None, "Base msg for node 'node1'"),
        ("Base msg", None, "2023Q1", None, "Base msg for period '2023Q1'"),
        (
            "Base msg",
            "node1",
            "2023Q1",
            {"detail": "value"},
            "Base msg for node 'node1' and period '2023Q1' (Details: detail=\"value\")",
        ),
    ],
)
def test_calculation_error_instantiation(message, node_id, period, details, expected_str):
    """Test CalculationError instantiation and message formatting."""
    err = CalculationError(message, node_id=node_id, period=period, details=details)
    assert err.node_id == node_id
    assert err.period == period
    assert err.details == (details or {})
    assert str(err) == expected_str
    assert isinstance(err, FinancialModelError)


@pytest.mark.parametrize(
    "message, node_id, expected_str",
    [
        ("Base msg", None, "Base msg"),
        ("Base msg", "node1", "Base msg for node 'node1'"),
    ],
)
def test_node_error_instantiation(message, node_id, expected_str):
    """Test NodeError instantiation and message formatting."""
    err = NodeError(message, node_id=node_id)
    assert err.node_id == node_id
    assert str(err) == expected_str
    assert isinstance(err, FinancialModelError)


@pytest.mark.parametrize(
    "message, node_id, input_name, period, expected_str",
    [
        ("Base msg", None, None, None, "Base msg"),
        ("Base msg", "node1", None, None, "Base msg for node 'node1'"),
        ("Base msg", None, "input1", None, "Base msg for input 'input1'"),
        ("Base msg", None, None, "2023", "Base msg for period '2023'"),
        (
            "Base msg",
            "node1",
            "input1",
            "2023",
            "Base msg for node 'node1' in input 'input1' in period '2023'",
        ),
        ("Base msg", "node1", "input1", None, "Base msg for node 'node1' in input 'input1'"),
        ("Base msg", "node1", None, "2023", "Base msg for node 'node1' in period '2023'"),
        ("Base msg", None, "input1", "2023", "Base msg for input 'input1' in period '2023'"),
    ],
)
def test_missing_input_error_instantiation(message, node_id, input_name, period, expected_str):
    """Test MissingInputError instantiation and message formatting."""
    err = MissingInputError(message, node_id=node_id, input_name=input_name, period=period)
    assert err.node_id == node_id
    assert err.input_name == input_name
    assert err.period == period
    assert str(err) == expected_str
    assert isinstance(err, FinancialModelError)


@pytest.mark.parametrize(
    "message, nodes, expected_str",
    [
        ("Base msg", None, "Base msg"),
        ("Base msg", ["n1", "n2"], "Base msg involving nodes: n1, n2"),
    ],
)
def test_graph_error_instantiation(message, nodes, expected_str):
    """Test GraphError instantiation and message formatting."""
    err = GraphError(message, nodes=nodes)
    assert err.nodes == (nodes or [])
    assert str(err) == expected_str
    assert isinstance(err, FinancialModelError)


@pytest.mark.parametrize(
    "message, validation_errors, expected_str",
    [
        ("Base msg", None, "Base msg"),
        ("Base msg", ["err1", "err2"], "Base msg: err1; err2"),
    ],
)
def test_data_validation_error_instantiation(message, validation_errors, expected_str):
    """Test DataValidationError instantiation and message formatting."""
    err = DataValidationError(message, validation_errors=validation_errors)
    assert err.validation_errors == (validation_errors or [])
    assert str(err) == expected_str
    assert isinstance(err, FinancialModelError)


@pytest.mark.parametrize(
    "message, source, adapter, original_error, expected_str_contains",
    [
        ("Base msg", None, None, None, "Base msg"),
        ("Base msg", "file.csv", None, None, "Base msg from source 'file.csv'"),
        ("Base msg", None, "csv_reader", None, "Base msg using adapter 'csv_reader'"),
        (
            "Base msg",
            "file.csv",
            "csv_reader",
            None,
            "Base msg using source 'file.csv' adapter 'csv_reader'",
        ),
        (
            "Base msg",
            "api.com",
            "api_reader",
            ValueError("Inner error"),
            "Base msg using source 'api.com' adapter 'api_reader': Inner error",
        ),
        (
            "Base msg",
            "file.csv",
            None,
            ValueError("Inner error"),
            "Base msg from source 'file.csv': Inner error",
        ),
    ],
)
def test_import_error_instantiation(
    message, source, adapter, original_error, expected_str_contains
):
    """Test ImportError instantiation and message formatting."""
    err = ImportError(message, source=source, adapter=adapter, original_error=original_error)
    assert err.source == source
    assert err.adapter == adapter
    assert err.original_error == original_error
    assert str(err) == expected_str_contains  # Exact match due to simplified test cases
    assert isinstance(err, FinancialModelError)


@pytest.mark.parametrize(
    "message, target, format_type, original_error, expected_str_contains",
    [
        ("Base msg", None, None, None, "Base msg"),
        ("Base msg", "out.json", None, None, "Base msg to target 'out.json'"),
        ("Base msg", None, "json", None, "Base msg in format 'json'"),
        ("Base msg", "out.json", "json", None, "Base msg in target 'out.json' format 'json'"),
        (
            "Base msg",
            "db://...",
            "sql",
            RuntimeError("DB down"),
            "Base msg in target 'db://...' format 'sql': DB down",
        ),
        (
            "Base msg",
            "out.csv",
            None,
            RuntimeError("Disk full"),
            "Base msg to target 'out.csv': Disk full",
        ),
    ],
)
def test_export_error_instantiation(
    message, target, format_type, original_error, expected_str_contains
):
    """Test ExportError instantiation and message formatting."""
    err = ExportError(
        message, target=target, format_type=format_type, original_error=original_error
    )
    assert err.target == target
    assert err.format_type == format_type
    assert err.original_error == original_error
    # Using exact match as the test cases cover the logic branches
    assert str(err) == expected_str_contains
    assert isinstance(err, FinancialModelError)


@pytest.mark.parametrize(
    "message, cycle, expected_str",
    [
        ("Default message", None, "Default message"),
        ("Custom message", None, "Custom message"),
        ("Default message", ["a", "b", "a"], "Default message: a -> b -> a"),
        ("Custom message", ["x", "y", "z", "x"], "Custom message: x -> y -> z -> x"),
    ],
)
def test_circular_dependency_error_instantiation(message, cycle, expected_str):
    """Test CircularDependencyError instantiation and message formatting."""
    # Test default message
    if message == "Default message":
        # The actual default message is hardcoded in the class
        err = CircularDependencyError(cycle=cycle)
        expected_str = (
            f"Circular dependency detected: {' -> '.join(cycle)}"
            if cycle
            else "Circular dependency detected"
        )
    else:
        err = CircularDependencyError(message=message, cycle=cycle)

    assert err.cycle == (cycle or [])
    assert str(err) == expected_str
    assert isinstance(err, FinancialModelError)


@pytest.mark.parametrize(
    "message, period, available_periods, expected_str",
    [
        ("Base msg", None, None, "Base msg"),
        ("Base msg", "2023Q5", None, "Base msg for period '2023Q5'"),
        (
            "Base msg",
            "2024",
            ["2023", "2022"],
            "Base msg for period '2024'. Available periods: 2023, 2022",
        ),
    ],
)
def test_period_error_instantiation(message, period, available_periods, expected_str):
    """Test PeriodError instantiation and message formatting."""
    err = PeriodError(message, period=period, available_periods=available_periods)
    assert err.period == period
    assert err.available_periods == (available_periods or [])
    assert str(err) == expected_str
    assert isinstance(err, FinancialModelError)


@pytest.mark.parametrize(
    "message, statement_id, expected_str",
    [
        ("Base msg", None, "Base msg"),
        ("Base msg", "BS_2023", "Base msg for statement 'BS_2023'"),
    ],
)
def test_statement_error_instantiation(message, statement_id, expected_str):
    """Test StatementError instantiation and message formatting."""
    err = StatementError(message, statement_id=statement_id)
    assert err.statement_id == statement_id
    assert str(err) == expected_str
    assert isinstance(err, FinancialModelError)


@pytest.mark.parametrize(
    "message, strategy_type, node_id, expected_str",
    [
        ("Base msg", None, None, "Base msg"),
        ("Base msg", "GrowthRate", None, "Base msg for strategy type 'GrowthRate'"),
        ("Base msg", None, "node1", "Base msg for node 'node1'"),
        (
            "Base msg",
            "Summation",
            "node1",
            "Base msg for strategy type 'Summation' in node 'node1'",
        ),
    ],
)
def test_strategy_error_instantiation(message, strategy_type, node_id, expected_str):
    """Test StrategyError instantiation and message formatting."""
    err = StrategyError(message, strategy_type=strategy_type, node_id=node_id)
    assert err.strategy_type == strategy_type
    assert err.node_id == node_id
    assert str(err) == expected_str
    assert isinstance(err, FinancialModelError)


@pytest.mark.parametrize(
    "message, transformer_type, parameters, expected_str",
    [
        ("Base msg", None, None, "Base msg"),
        ("Base msg", "LogTransform", None, "Base msg in transformer 'LogTransform'"),
        (
            "Base msg",
            "Scaler",
            {"min": 0, "max": 1},
            "Base msg in transformer 'Scaler' with parameters: min=0, max=1",
        ),
    ],
)
def test_transformation_error_instantiation(message, transformer_type, parameters, expected_str):
    """Test TransformationError instantiation and message formatting."""
    err = TransformationError(message, transformer_type=transformer_type, parameters=parameters)
    assert err.transformer_type == transformer_type
    assert err.parameters == (parameters or {})
    assert str(err) == expected_str
    assert isinstance(err, FinancialModelError)


@pytest.mark.parametrize(
    "message, metric_name, details, expected_str",
    [
        ("Base msg", None, None, "Base msg"),
        ("Base msg", "revenue_growth", None, "Base msg related to metric 'revenue_growth'"),
        (
            "Base msg",
            "profit_margin",
            {"formula": "invalid("},
            "Base msg related to metric 'profit_margin'",  # Details not included in standard str
        ),
    ],
)
def test_metric_error_instantiation(message, metric_name, details, expected_str):
    """Test MetricError instantiation and message formatting."""
    err = MetricError(message, metric_name=metric_name, details=details)
    assert err.metric_name == metric_name
    assert err.details == (details or {})
    assert str(err) == expected_str
    assert isinstance(err, FinancialModelError)
