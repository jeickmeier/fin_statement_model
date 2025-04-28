"""Tests for the statistical nodes in stats_nodes.py."""

import pytest
import statistics
import math
from unittest.mock import MagicMock
from typing import Optional
import pandas as pd

from fin_statement_model.core.nodes.base import Node
from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode
from fin_statement_model.core.nodes.stats_nodes import (
    YoYGrowthNode,
    MultiPeriodStatNode,
    TwoPeriodAverageNode,
)
from fin_statement_model.core.errors import CalculationError

# --- Fixtures ---


@pytest.fixture
def input_node_yoy() -> FinancialStatementItemNode:
    """Provides an input node with values for YoY testing."""
    return FinancialStatementItemNode(
        name="Sales",
        values={"2022": 100.0, "2023": 120.0, "2024": 110.0, "2025": 0.0, "2026": 150.0},
    )


@pytest.fixture
def input_node_multi() -> FinancialStatementItemNode:
    """Provides an input node with values for multi-period stats."""
    return FinancialStatementItemNode(
        name="UnitsSold",
        values={
            "Q1": 10,
            "Q2": 12,
            "Q3": 11,
            "Q4": 13,
            "Q5_invalid": "abc",
            "Q6_nan": float("nan"),
        },
    )


@pytest.fixture
def input_node_avg() -> FinancialStatementItemNode:
    """Provides an input node for two-period average testing."""
    return FinancialStatementItemNode(
        name="Price", values={"Jan": 10.5, "Feb": 11.5, "Mar_nan": float("nan")}
    )


@pytest.fixture
def non_numeric_input_node() -> MagicMock:
    """Provides a mock node that returns a non-numeric value."""
    mock = MagicMock(spec=Node)
    mock.name = "NonNumericInput"
    mock.calculate.return_value = "not a number"
    return mock


@pytest.fixture
def error_input_node() -> MagicMock:
    """Provides a mock node that raises an error on calculation."""
    mock = MagicMock(spec=Node)
    mock.name = "ErrorInput"
    mock.calculate.side_effect = CalculationError("Input failed!", node_id="ErrorInput")
    return mock


# --- YoYGrowthNode Tests ---


def test_yoy_init_success(input_node_yoy: Node):
    """Test successful initialization of YoYGrowthNode."""
    node = YoYGrowthNode(
        name="SalesYoY", input_node=input_node_yoy, prior_period="2022", current_period="2023"
    )
    assert node.name == "SalesYoY"
    assert node.input_node == input_node_yoy
    assert node.prior_period == "2022"
    assert node.current_period == "2023"
    assert node.has_calculation() is True
    assert node.get_dependencies() == ["Sales"]


def test_yoy_init_invalid_input_type():
    """Test TypeError if input_node is not a Node."""
    with pytest.raises(TypeError, match="input_node must be a Node instance"):
        YoYGrowthNode(name="test", input_node=123, prior_period="a", current_period="b")


def test_yoy_init_invalid_period_type(input_node_yoy: Node):
    """Test TypeError if periods are not strings."""
    with pytest.raises(TypeError, match="prior_period and current_period must be strings"):
        YoYGrowthNode(
            name="test", input_node=input_node_yoy, prior_period=2022, current_period="2023"
        )
    with pytest.raises(TypeError, match="prior_period and current_period must be strings"):
        YoYGrowthNode(
            name="test", input_node=input_node_yoy, prior_period="2022", current_period=2023
        )


def test_yoy_calculate_positive_growth(input_node_yoy: Node):
    """Test calculation for positive growth."""
    node = YoYGrowthNode(
        name="g", input_node=input_node_yoy, prior_period="2022", current_period="2023"
    )
    # Growth = (120 - 100) / 100 = 0.2
    assert node.calculate() == pytest.approx(0.2)


def test_yoy_calculate_negative_growth(input_node_yoy: Node):
    """Test calculation for negative growth."""
    node = YoYGrowthNode(
        name="g", input_node=input_node_yoy, prior_period="2023", current_period="2024"
    )
    # Growth = (110 - 120) / 120 = -10 / 120 = -0.08333...
    assert node.calculate("ignored_period") == pytest.approx(-0.08333333)


def test_yoy_calculate_prior_zero(input_node_yoy: Node):
    """Test calculation returns NaN when prior period value is zero."""
    node = YoYGrowthNode(
        name="g", input_node=input_node_yoy, prior_period="2025", current_period="2026"
    )
    assert math.isnan(node.calculate())


def test_yoy_calculate_non_numeric_prior(input_node_yoy: Node, non_numeric_input_node: MagicMock):
    """Test CalculationError when prior period value is non-numeric."""
    non_numeric_input_node.calculate.side_effect = lambda p: "abc" if p == "prior" else 100
    node = YoYGrowthNode(
        name="g", input_node=non_numeric_input_node, prior_period="prior", current_period="current"
    )
    with pytest.raises(CalculationError) as exc_info:
        node.calculate()
    assert "Prior period ('prior') value is non-numeric" in exc_info.value.details["original_error"]


def test_yoy_calculate_non_numeric_current(input_node_yoy: Node, non_numeric_input_node: MagicMock):
    """Test CalculationError when current period value is non-numeric."""
    non_numeric_input_node.calculate.side_effect = lambda p: 100 if p == "prior" else "abc"
    node = YoYGrowthNode(
        name="g", input_node=non_numeric_input_node, prior_period="prior", current_period="current"
    )
    with pytest.raises(CalculationError) as exc_info:
        node.calculate()
    assert (
        "Current period ('current') value is non-numeric"
        in exc_info.value.details["original_error"]
    )


def test_yoy_calculate_input_error(error_input_node: MagicMock):
    """Test CalculationError propagation when input node calculation fails."""
    node = YoYGrowthNode(
        name="g", input_node=error_input_node, prior_period="2022", current_period="2023"
    )
    with pytest.raises(CalculationError) as exc_info:
        node.calculate()
    assert "Failed to calculate YoY growth" in exc_info.value.message
    assert "Input failed!" in exc_info.value.details["original_error"]


# --- MultiPeriodStatNode Tests ---


def test_multi_init_success(input_node_multi: Node):
    """Test successful initialization of MultiPeriodStatNode."""
    periods = ["Q1", "Q2", "Q3"]
    node = MultiPeriodStatNode(
        name="SalesStats", input_node=input_node_multi, periods=periods, stat_func=statistics.mean
    )
    assert node.name == "SalesStats"
    assert node.input_node == input_node_multi
    assert node.periods == periods
    assert node.stat_func == statistics.mean
    assert node.has_calculation() is True
    assert node.get_dependencies() == ["UnitsSold"]


def test_multi_init_default_stat_func(input_node_multi: Node):
    """Test initialization uses statistics.stdev by default."""
    node = MultiPeriodStatNode(
        name="SalesStdDev", input_node=input_node_multi, periods=["Q1", "Q2"]
    )
    assert node.stat_func == statistics.stdev


def test_multi_init_invalid_input_type():
    """Test TypeError if input_node is not a Node."""
    with pytest.raises(TypeError, match="input_node must be a Node instance"):
        MultiPeriodStatNode(name="t", input_node="abc", periods=["Q1"], stat_func=statistics.mean)


def test_multi_init_invalid_periods_empty(input_node_multi: Node):
    """Test ValueError if periods list is empty."""
    with pytest.raises(ValueError, match="periods must be a non-empty list"):
        MultiPeriodStatNode(
            name="t", input_node=input_node_multi, periods=[], stat_func=statistics.mean
        )


def test_multi_init_invalid_periods_type(input_node_multi: Node):
    """Test TypeError if periods is not a list or contains non-strings."""
    with pytest.raises(ValueError, match="periods must be a non-empty list"):
        MultiPeriodStatNode(
            name="t", input_node=input_node_multi, periods="Q1,Q2", stat_func=statistics.mean
        )
    with pytest.raises(TypeError, match="periods must contain only strings"):
        MultiPeriodStatNode(
            name="t", input_node=input_node_multi, periods=["Q1", 2], stat_func=statistics.mean
        )


def test_multi_init_invalid_stat_func_type(input_node_multi: Node):
    """Test TypeError if stat_func is not callable."""
    with pytest.raises(TypeError, match="stat_func must be a callable function"):
        MultiPeriodStatNode(name="t", input_node=input_node_multi, periods=["Q1"], stat_func=123)


def test_multi_calculate_mean(input_node_multi: Node):
    """Test calculation using statistics.mean."""
    node = MultiPeriodStatNode(
        name="AvgSales",
        input_node=input_node_multi,
        periods=["Q1", "Q2", "Q3", "Q4"],
        stat_func=statistics.mean,
    )
    # Mean of [10, 12, 11, 13] = 46 / 4 = 11.5
    assert node.calculate() == pytest.approx(11.5)


def test_multi_calculate_stdev(input_node_multi: Node):
    """Test calculation using statistics.stdev (default)."""
    node = MultiPeriodStatNode(
        name="StdevSales", input_node=input_node_multi, periods=["Q1", "Q2", "Q3", "Q4"]
    )
    # Stdev of [10, 12, 11, 13]
    assert node.calculate("ignored") == pytest.approx(statistics.stdev([10, 12, 11, 13]))


def test_multi_calculate_median(input_node_multi: Node):
    """Test calculation using statistics.median."""
    node = MultiPeriodStatNode(
        name="MedianSales",
        input_node=input_node_multi,
        periods=["Q1", "Q2", "Q3", "Q4"],
        stat_func=statistics.median,
    )
    # Median of [10, 12, 11, 13] = (11 + 12) / 2 = 11.5
    assert node.calculate() == pytest.approx(11.5)


def test_multi_calculate_with_skipped_periods(input_node_multi: Node):
    """Test calculation skips non-numeric/non-finite values."""
    # Includes Q5 (invalid string) and Q6 (nan)
    node = MultiPeriodStatNode(
        name="AvgWithSkip",
        input_node=input_node_multi,
        periods=["Q1", "Q2", "Q5_invalid", "Q6_nan"],
        stat_func=statistics.mean,
    )
    # Should only use Q1 (10) and Q2 (12). Mean = (10 + 12) / 2 = 11.0
    assert node.calculate() == pytest.approx(11.0)


def test_multi_calculate_insufficient_data_for_stat(input_node_multi: Node):
    """Test returns NaN if stat function requires more data (e.g., stdev with 1 point)."""
    node = MultiPeriodStatNode(
        name="StdevOnePoint",
        input_node=input_node_multi,
        periods=["Q1"],
        stat_func=statistics.stdev,
    )
    assert math.isnan(node.calculate())


def test_multi_calculate_no_valid_data(input_node_multi: Node):
    """Test returns NaN if no valid numeric data points are found."""
    node = MultiPeriodStatNode(
        name="AvgNoneValid",
        input_node=input_node_multi,
        periods=["Q5_invalid", "Q6_nan"],
        stat_func=statistics.mean,
    )
    assert math.isnan(node.calculate())


def test_multi_calculate_input_error_partial(input_node_multi: Node):
    """Test calculation proceeds if some periods fail but others succeed."""
    # Store the original calculate method before mocking
    original_calculate = input_node_multi.calculate

    def side_effect_func(period: str) -> Optional[float]:
        if period == "Q2":
            raise CalculationError("Failed Q2", node_id=input_node_multi.name, period=period)
        # Call the original method for other periods
        return original_calculate(period)

    # Mock the calculate method *after* storing the original
    input_node_multi.calculate = MagicMock(side_effect=side_effect_func)

    node = MultiPeriodStatNode(
        name="AvgWithError",
        input_node=input_node_multi,
        periods=["Q1", "Q2", "Q3"],
        stat_func=statistics.mean,
    )
    # Should use Q1 (10) and Q3 (11). Mean = (10 + 11) / 2 = 10.5
    assert node.calculate() == pytest.approx(10.5)

    # Restore the original method after the test (important if fixture scope is wider)
    # Although not strictly necessary for function-scoped fixtures, it's good practice.
    input_node_multi.calculate = original_calculate


def test_multi_calculate_stat_func_error(input_node_multi: Node):
    """Test returns NaN if the stat function itself raises an error."""

    def error_stat_func(data: pd.Series) -> float:
        raise ValueError("Stat func failed!")

    node = MultiPeriodStatNode(
        name="BadStatFunc",
        input_node=input_node_multi,
        periods=["Q1", "Q2"],
        stat_func=error_stat_func,
    )
    assert math.isnan(node.calculate())


# --- TwoPeriodAverageNode Tests ---


def test_avg_init_success(input_node_avg: Node):
    """Test successful initialization of TwoPeriodAverageNode."""
    node = TwoPeriodAverageNode(
        name="AvgPrice", input_node=input_node_avg, period1="Jan", period2="Feb"
    )
    assert node.name == "AvgPrice"
    assert node.input_node == input_node_avg
    assert node.period1 == "Jan"
    assert node.period2 == "Feb"
    assert node.has_calculation() is True
    assert node.get_dependencies() == ["Price"]


def test_avg_init_invalid_input_type():
    """Test TypeError if input_node is not a Node."""
    with pytest.raises(TypeError, match="input_node must be a Node instance"):
        TwoPeriodAverageNode(name="t", input_node=False, period1="a", period2="b")


def test_avg_init_invalid_period_type(input_node_avg: Node):
    """Test TypeError if periods are not strings."""
    with pytest.raises(TypeError, match="period1 and period2 must be strings"):
        TwoPeriodAverageNode(name="t", input_node=input_node_avg, period1=1, period2="b")
    with pytest.raises(TypeError, match="period1 and period2 must be strings"):
        TwoPeriodAverageNode(name="t", input_node=input_node_avg, period1="a", period2=2)


def test_avg_calculate_success(input_node_avg: Node):
    """Test successful calculation of the average."""
    node = TwoPeriodAverageNode(
        name="AvgJanFeb", input_node=input_node_avg, period1="Jan", period2="Feb"
    )
    # Avg(10.5, 11.5) = 22 / 2 = 11.0
    assert node.calculate() == pytest.approx(11.0)


def test_avg_calculate_with_nan_input(input_node_avg: Node):
    """Test returns NaN if one of the input values is NaN."""
    node = TwoPeriodAverageNode(
        name="AvgWithNaN", input_node=input_node_avg, period1="Jan", period2="Mar_nan"
    )
    assert math.isnan(node.calculate("ignored_period"))


def test_avg_calculate_non_numeric_input(non_numeric_input_node: MagicMock):
    """Test returns NaN if one of the input values is non-numeric."""
    non_numeric_input_node.calculate.side_effect = lambda p: 10.0 if p == "p1" else "abc"
    node = TwoPeriodAverageNode(
        name="AvgNonNum", input_node=non_numeric_input_node, period1="p1", period2="p2"
    )
    assert math.isnan(node.calculate())


def test_avg_calculate_input_error(error_input_node: MagicMock):
    """Test CalculationError propagation if input node calculation fails."""
    node = TwoPeriodAverageNode(
        name="AvgError", input_node=error_input_node, period1="p1", period2="p2"
    )
    with pytest.raises(CalculationError) as exc_info:
        node.calculate()
    assert "Failed to calculate two-period average" in exc_info.value.message
    assert "Input failed!" in exc_info.value.details["original_error"]
