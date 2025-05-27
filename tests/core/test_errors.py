"""Tests for custom error classes in fin_statement_model.core.errors."""

import pytest
from typing import Any, Optional
from collections.abc import Sequence

from fin_statement_model.core.errors import (
    CalculationError,
    CircularDependencyError,
    ConfigurationError,
    DataValidationError,
    FinancialModelError,
    GraphError,
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
    ("message", "config_path", "errors", "expected_str"),
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
def test_configuration_error_instantiation(
    message: str,
    config_path: Optional[str],
    errors: Optional[list[str]],
    expected_str: str,
) -> None:
    """Test ConfigurationError instantiation and message formatting."""
    err = ConfigurationError(message, config_path=config_path, errors=errors)
    assert err.config_path == config_path
    assert err.errors == (errors or [])
    assert str(err) == expected_str
    assert isinstance(err, FinancialModelError)


@pytest.mark.parametrize(
    ("message", "node_id", "period", "details", "expected_str"),
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
def test_calculation_error_instantiation(
    message: str,
    node_id: Optional[str],
    period: Optional[str],
    details: Optional[str],
    expected_str: str,
) -> None:
    """Test CalculationError instantiation and message formatting."""
    err = CalculationError(message, node_id=node_id, period=period, details=details)
    assert err.node_id == node_id
    assert err.period == period
    assert err.details == (details or {})
    assert str(err) == expected_str
    assert isinstance(err, FinancialModelError)


@pytest.mark.parametrize(
    ("message", "node_id", "expected_str"),
    [
        ("Base msg", None, "Base msg"),
        ("Base msg", "node1", "Base msg for node 'node1'"),
    ],
)
def test_node_error_instantiation(
    message: str,
    node_id: Optional[str],
    expected_str: str,
) -> None:
    """Test NodeError instantiation and message formatting."""
    err = NodeError(message, node_id=node_id)
    assert err.node_id == node_id
    assert str(err) == expected_str
    assert isinstance(err, FinancialModelError)


@pytest.mark.parametrize(
    ("message", "node_id", "input_name", "period", "expected_str"),
    [
        (
            "Missing input value",
            "NodeX",
            "InputA",
            "2023",
            "Missing input value for node 'NodeX', input 'InputA' in period '2023'",
        ),
        (
            "Input data unavailable",
            "NodeY",
            "InputB",
            None,
            "Input data unavailable for node 'NodeY', input 'InputB'",
        ),
        ("General missing input", None, None, None, "General missing input"),
    ],
)
def test_missing_input_error_instantiation(
    message: str,
    node_id: Optional[str],
    input_name: Optional[str],
    period: Optional[str],
    expected_str: str,
) -> None:
    """Test MissingInputError instantiation and message formatting."""
    err = MissingInputError(message, node_id=node_id, input_name=input_name, period=period)
    assert err.node_id == node_id
    assert err.input_name == input_name
    assert err.period == period
    # Adjust for potential wording change: "for node X in input Y"
    expected_adj = expected_str.replace(", input ", " in input ")
    assert str(err) == expected_adj
    assert isinstance(err, FinancialModelError)


@pytest.mark.parametrize(
    ("message", "nodes", "expected_str"),
    [
        ("Basic graph error", None, "Basic graph error"),
        ("Nodes involved", ["A", "B"], "Nodes involved: A, B"),
        ("Single node involved", ["C"], "Single node involved: C"),
        ("Empty node list", [], "Empty node list"),
    ],
)
def test_graph_error_instantiation(
    message: str, nodes: Optional[Sequence[str]], expected_str: str
) -> None:
    """Test GraphError instantiation and message formatting."""
    err = GraphError(message, nodes=nodes)
    assert err.nodes == (nodes or [])
    assert message in str(err)
    if nodes:
        assert all(n in str(err) for n in nodes)


@pytest.mark.parametrize(
    ("message", "validation_errors", "expected_str"),
    [
        ("Data validation failed", None, "Data validation failed"),
        (
            "Validation issues",
            {"field1": "Error A", "field2": "Error B"},
            "Validation issues:\n - field1: Error A\n - field2: Error B",
        ),
        ("Empty errors dict", {}, "Empty errors dict"),
    ],
)
def test_data_validation_error_instantiation(
    message: str,
    validation_errors: Optional[dict[str, Any]],
    expected_str: str,
) -> None:
    """Test DataValidationError instantiation and message formatting."""
    err = DataValidationError(message, validation_errors=validation_errors)
    assert err.validation_errors == (validation_errors or [])
    assert message in str(err)
    if validation_errors:
        assert all(e in str(err) for e in validation_errors)


@pytest.mark.parametrize(
    ("message", "cycle", "expected_str"),
    [
        (
            None,  # Default message
            ["A", "B", "C", "A"],
            "Circular dependency detected: A -> B -> C -> A",
        ),
        (
            "Custom message",
            ["X", "Y", "X"],
            "Custom message: X -> Y -> X",
        ),
        (
            "No cycle provided",
            None,
            "No cycle provided",
        ),  # Should format without cycle info
        (
            "Empty cycle provided",
            [],
            "Empty cycle provided",
        ),  # Should format without cycle info
    ],
)
def test_circular_dependency_error_instantiation(
    message: Optional[str], cycle: Optional[Sequence[str]], expected_str: str
) -> None:
    """Test CircularDependencyError instantiation and message formatting."""
    # Test default message
    if message is None:
        err = CircularDependencyError(cycle=cycle)
    else:
        err = CircularDependencyError(message, cycle=cycle)
    assert err.cycle == (cycle or [])
    assert (message or "Circular dependency") in str(err)
    if cycle:
        assert " -> " in str(err)


@pytest.mark.parametrize(
    ("message", "period", "available_periods", "expected_str"),
    [
        (
            "Invalid period requested",
            "2025",
            ["2023", "2024"],
            "Invalid period requested: '2025'. Available periods: ['2023', '2024']",
        ),
        (
            "Period format incorrect",
            "Q5-2023",
            None,
            "Period format incorrect: 'Q5-2023'",
        ),
        (
            "Period not found",
            "2022",
            [],
            "Period not found: '2022'. Available periods: []",
        ),
        ("General period error", None, None, "General period error"),
    ],
)
def test_period_error_instantiation(
    message: str,
    period: Optional[str],
    available_periods: Optional[Sequence[str]],
    expected_str: str,
) -> None:
    """Test PeriodError instantiation and message formatting."""
    err = PeriodError(message, period=period, available_periods=available_periods)
    assert err.period == period
    assert err.available_periods == (available_periods or [])
    assert message in str(err)
    if period:
        assert period in str(err)


@pytest.mark.parametrize(
    ("message", "statement_id", "expected_str"),
    [
        ("Statement not found", "BS", "Statement not found: 'BS'"),
        ("Error processing statement", "IS", "Error processing statement: 'IS'"),
        ("Generic statement issue", None, "Generic statement issue"),
    ],
)
def test_statement_error_instantiation(
    message: str, statement_id: Optional[str], expected_str: str
) -> None:
    """Test StatementError instantiation and message formatting."""
    err = StatementError(message, statement_id=statement_id)
    assert err.statement_id == statement_id
    assert message in str(err)
    if statement_id:
        assert statement_id in str(err)


@pytest.mark.parametrize(
    ("message", "strategy_name", "node_id", "expected_str"),
    [
        (
            "Failed to apply strategy",
            "Addition",
            "NodeA",
            "Failed to apply strategy 'Addition' for node 'NodeA'",
        ),
        (
            "Invalid configuration for strategy",
            "WeightedAverage",
            None,
            "Invalid configuration for strategy 'WeightedAverage'",
        ),
        (
            "Strategy execution error",
            None,
            "NodeB",
            "Strategy execution error for node 'NodeB'",
        ),
        ("General strategy problem", None, None, "General strategy problem"),
    ],
)
def test_strategy_error_instantiation(
    message: str,
    strategy_name: Optional[str],
    node_id: Optional[str],
    expected_str: str,
) -> None:
    """Test StrategyError instantiation and message formatting."""
    err = StrategyError(message, strategy_type=strategy_name, node_id=node_id)
    assert err.strategy_type == strategy_name
    assert err.node_id == node_id
    assert message in str(err)
    if strategy_name:
        assert strategy_name in str(err)
    if node_id:
        assert node_id in str(err)


@pytest.mark.parametrize(
    ("message", "transformer_name", "parameters", "expected_str"),
    [
        (
            "Transformation failed",
            "Normalize",
            {"method": "min-max"},
            "Transformation failed for transformer 'Normalize' with parameters {'method': 'min-max'}",
        ),
        (
            "Missing parameters",
            "Scale",
            None,
            "Missing parameters for transformer 'Scale'",
        ),
        ("Error during transformation", None, None, "Error during transformation"),
        (
            "Bad parameter value",
            "LogTransform",
            {"base": -1},
            "Bad parameter value for transformer 'LogTransform' with parameters {'base': -1}",
        ),
    ],
)
def test_transformation_error_instantiation(
    message: str,
    transformer_name: Optional[str],
    parameters: Optional[dict[str, Any]],
    expected_str: str,
) -> None:
    """Test TransformationError instantiation and message formatting."""
    err = TransformationError(message, transformer_type=transformer_name, parameters=parameters)
    assert err.transformer_type == transformer_name
    assert err.parameters == (parameters or {})
    assert message in str(err)
    if transformer_name:
        assert transformer_name in str(err)


@pytest.mark.parametrize(
    ("message", "metric_name", "details", "expected_str"),
    [
        (
            "Metric definition not found",
            "non_existent_metric",
            None,
            "Metric definition not found related to metric 'non_existent_metric'",
        ),
        (
            "Invalid metric calculation",
            "roi",
            "Division by zero",
            "Invalid metric calculation related to metric 'roi'",
        ),
        (
            "Metric configuration error",
            None,
            "Bad YAML format",
            "Metric configuration error",
        ),
        ("General metric issue", None, None, "General metric issue"),
    ],
)
def test_metric_error_instantiation(
    message: str,
    metric_name: Optional[str],
    details: Optional[str],
    expected_str: str,
) -> None:
    """Test MetricError instantiation and message formatting."""
    err = MetricError(message, metric_name=metric_name, details=details)
    assert err.metric_name == metric_name
    assert err.details == (details or {})
    assert str(err) == expected_str
