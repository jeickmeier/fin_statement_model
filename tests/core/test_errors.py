from __future__ import annotations

"""Unit tests to exercise the rich message-formatting branches in
`fin_statement_model.core.errors` so the module achieves ≥ 80 % coverage.

The tests intentionally inspect the *str(exc)* representation produced by each
error class rather than just their type to validate that contextual information
is combined correctly.
"""


from fin_statement_model.core.errors import (
    FinStatementModelError,
    FinancialModelError,
    ConfigurationError,
    CalculationError,
    NodeError,
    MissingInputError,
    GraphError,
    CircularDependencyError,
    PeriodError,
    StatementError,
    StrategyError,
    TransformationError,
    MetricError,
)


def test_financial_model_error_alias() -> None:
    """Alias *FinStatementModelError* should point to *FinancialModelError*."""
    assert FinStatementModelError is FinancialModelError
    exc = FinancialModelError("base")
    assert str(exc) == "base"


# -----------------------------------------------------------------------------
# ConfigurationError – path + errors list concatenation
# -----------------------------------------------------------------------------


def test_configuration_error_full_context() -> None:
    err = ConfigurationError(
        "Invalid config",
        config_path="/tmp/cfg.yaml",
        errors=["missing_field", "bad_value"],
    )
    msg = str(err)
    assert "/tmp/cfg.yaml" in msg and "missing_field" in msg and "bad_value" in msg


# -----------------------------------------------------------------------------
# CalculationError – details + original_error propagation
# -----------------------------------------------------------------------------


def test_calculation_error_with_original_error() -> None:
    err = CalculationError(
        "Failed",
        node_id="N",
        period="2023",
        details={"original_error": "division by zero", "foo": 1},
    )
    msg = str(err)
    assert "division by zero" in msg and "N" in msg and "2023" in msg


# -----------------------------------------------------------------------------
# NodeError & MissingInputError message assembly
# -----------------------------------------------------------------------------


def test_node_and_missing_input_errors() -> None:
    node_exc = NodeError("NotFound", node_id="X")
    assert "X" in str(node_exc)

    missing_exc = MissingInputError(
        "Missing", node_id="A", input_name="B", period="2024"
    )
    msg = str(missing_exc)
    # Expect all context pieces present
    for token in ("A", "B", "2024"):
        assert token in msg


# -----------------------------------------------------------------------------
# GraphError and CircularDependencyError formatting
# -----------------------------------------------------------------------------


def test_graph_and_cycle_errors() -> None:
    g_err = GraphError("Orphan", nodes=["n1", "n2"])
    assert "n1" in str(g_err) and "n2" in str(g_err)

    cycle = ["a", "b", "c", "a"]
    cyc_err = CircularDependencyError(cycle=cycle)
    msg = str(cyc_err)
    # Ensure arrow-joined representation appears
    assert " -> ".join(cycle) in msg


# -----------------------------------------------------------------------------
# PeriodError combinations
# -----------------------------------------------------------------------------


def test_period_error_variants() -> None:
    e1 = PeriodError("Bad", period="2023Q5")
    assert "2023Q5" in str(e1)

    e2 = PeriodError("Missing", period="2025", available_periods=["2023", "2024"])
    msg2 = str(e2)
    assert "2025" in msg2 and "2023" in msg2 and "2024" in msg2


# -----------------------------------------------------------------------------
# StatementError, StrategyError, TransformationError, MetricError
# -----------------------------------------------------------------------------


def test_misc_error_messages() -> None:
    stmt_err = StatementError("Unbalanced", statement_id="BS2023")
    assert "BS2023" in str(stmt_err)

    strat_err = StrategyError("Bad", strategy_type="GrowthRate", node_id="proj")
    msg = str(strat_err)
    assert "GrowthRate" in msg and "proj" in msg

    trans_err = TransformationError(
        "Fail", transformer_type="Scaler", parameters={"range": (0, 1)}
    )
    assert "Scaler" in str(trans_err) and "range" in str(trans_err)

    metr_err = MetricError("Unknown", metric_name="weird_ratio")
    assert "weird_ratio" in str(metr_err)
