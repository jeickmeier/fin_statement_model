from __future__ import annotations

"""Additional tests for CalculationEngine focusing on metrics, error handling, and
period-selection logic.  These complement the basic suite and aim to push branch
coverage of *core/graph/services/calculation_engine.py* beyond the 80 % target.
"""

import math
import pytest

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.errors import CalculationError, NodeError


# -----------------------------------------------------------------------------
# Helper - build a graph with two data nodes and two periods
# -----------------------------------------------------------------------------


def _make_graph_two_periods() -> Graph:
    g = Graph(periods=["2023", "2024"])
    g.add_financial_statement_item("A", {"2023": 10.0, "2024": 12.0})
    g.add_financial_statement_item("B", {"2023": 5.0, "2024": 7.0})
    g.add_calculation("Sum", ["A", "B"], "addition")
    return g


# -----------------------------------------------------------------------------
# recalc_all - exercise explicit period selection paths
# -----------------------------------------------------------------------------


def test_recalc_all_with_explicit_period_list() -> None:
    g = _make_graph_two_periods()
    engine = g._calc_engine  # pylint: disable=protected-access

    # First calculate only 2023 so cache is partial
    assert g.calculate("Sum", "2023") == 15.0
    assert "2024" not in engine.cache.get("Sum", {})

    # Trigger recalc for a *subset* of periods
    g.recalculate_all(periods=["2024"])

    # Cache should now contain the value for 2024 but previous period cleared
    assert engine.cache["Sum"] == {"2024": 19.0}


# -----------------------------------------------------------------------------
# calculate - error handling (ZeroDivisionError → CalculationError)
# -----------------------------------------------------------------------------


def test_calculate_error_path_zero_division() -> None:
    g = Graph(periods=["2023"])
    g.add_financial_statement_item("X", {"2023": 10})
    g.add_financial_statement_item("Y", {"2023": 0})  # zero denominator
    g.add_calculation(
        name="Div",
        input_names=["X", "Y"],
        operation_type="formula",
        formula="input_0 / input_1",
        formula_variable_names=["input_0", "input_1"],
    )

    with pytest.raises(CalculationError):
        g.calculate("Div", "2023")


# -----------------------------------------------------------------------------
# ensure_signed_nodes - negative branch when base missing
# -----------------------------------------------------------------------------


def test_ensure_signed_nodes_missing_base() -> None:
    g = Graph(periods=["2023"])
    engine = g._calc_engine  # pylint: disable=protected-access
    with pytest.raises(NodeError):
        engine.ensure_signed_nodes(["DoesNotExist"])


# -----------------------------------------------------------------------------
# Metric helpers - get_metric / list / info
# -----------------------------------------------------------------------------


def test_metric_round_trip_current_ratio() -> None:
    """Verify metric helpers work end-to-end for a built-in metric."""
    # Prepare required inputs for *current_ratio*
    g = Graph(periods=["2023"])
    g.add_financial_statement_item("current_assets", {"2023": 200.0})
    g.add_financial_statement_item("current_liabilities", {"2023": 100.0})

    # Add metric node (uses CalculationEngine internally)
    g.add_metric("current_ratio")

    # Should now appear in available metrics and have correct value
    engine = g._calc_engine  # pylint: disable=protected-access
    assert "current_ratio" in engine.get_available_metrics()

    # Metric node retrieved via helper
    metric_node = engine.get_metric("current_ratio")
    assert metric_node is not None
    assert math.isclose(g.calculate("current_ratio", "2023"), 2.0)

    # Info helper returns rich dict
    info = engine.get_metric_info("current_ratio")
    assert info["id"] == "current_ratio"
    assert info["name"].lower().startswith("current")
    assert "inputs" in info and set(info["inputs"]) == {
        "current_assets",
        "current_liabilities",
    }
