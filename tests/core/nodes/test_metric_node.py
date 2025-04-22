"""Tests for the MetricCalculationNode defined in metric_node.py."""

import pytest
from unittest.mock import MagicMock, patch

from fin_statement_model.core.nodes.base import Node
from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode

# Import the correct MetricCalculationNode (from metric_node.py)
from fin_statement_model.core.nodes.metric_node import MetricCalculationNode
from fin_statement_model.core.nodes.calculation_nodes import (
    FormulaCalculationNode,
)  # Needed for checking internal node
from fin_statement_model.core.errors import ConfigurationError, CalculationError, MetricError

# --- Fixtures ---


@pytest.fixture
def node_rev() -> FinancialStatementItemNode:
    """Provides a mock revenue node."""
    return FinancialStatementItemNode(name="revenue_item", values={"2023": 500.0, "2024": 600.0})


@pytest.fixture
def node_cogs() -> FinancialStatementItemNode:
    """Provides a mock COGS node."""
    return FinancialStatementItemNode(name="cogs_item", values={"2023": 200.0, "2024": 250.0})


@pytest.fixture
def mock_graph(node_rev: Node, node_cogs: Node) -> MagicMock:
    """Provides a mock graph object with a get_node method."""
    graph = MagicMock()
    nodes = {
        "revenue_item": node_rev,
        "cogs_item": node_cogs,
        "non_node_item": object(),  # Item that is not a Node subclass
    }
    graph.get_node.side_effect = lambda name: nodes.get(name)
    return graph


@pytest.fixture
def metric_definition() -> dict:
    """Provides a sample metric definition."""
    return {
        "gross_profit": {
            "inputs": ["revenue_item", "cogs_item"],
            "formula": "revenue_item - cogs_item",
            "description": "Revenue minus Cost of Goods Sold.",
        }
    }


# Patch metric_registry for all tests in this module
@pytest.fixture(autouse=True)
def patch_registry(metric_definition: dict):
    """Patches the global metric_registry for isolated testing."""
    with patch("fin_statement_model.core.nodes.metric_node.metric_registry") as mock_registry:
        # Configure mock to return the definition or raise KeyError
        def get_side_effect(key):
            if key == "gross_profit":
                return metric_definition["gross_profit"]
            raise KeyError(f"Metric definition '{key}' not found in registry.")

        mock_registry.get.side_effect = get_side_effect
        yield mock_registry  # Provide the mock to tests if needed


# --- Test Cases ---


def test_metric_node_init_success(mock_graph: MagicMock, metric_definition: dict):
    """Test successful initialization when metric and inputs are found."""
    node = MetricCalculationNode(name="gp_calc", metric_name="gross_profit", graph=mock_graph)

    assert node.name == "gp_calc"
    assert node.metric_name == "gross_profit"
    assert node.graph == mock_graph
    assert node.definition == metric_definition["gross_profit"]
    assert node.has_calculation() is True
    assert node.get_dependencies() == ["revenue_item", "cogs_item"]

    # Check internal FormulaCalculationNode
    assert isinstance(node.calc_node, FormulaCalculationNode)
    assert node.calc_node.name == "_gp_calc_formula_calc"
    assert node.calc_node.formula == "revenue_item - cogs_item"
    # Verify the correct nodes were resolved from the graph
    assert node.calc_node.inputs["revenue_item"] == mock_graph.get_node("revenue_item")
    assert node.calc_node.inputs["cogs_item"] == mock_graph.get_node("cogs_item")


def test_metric_node_init_metric_not_found(mock_graph: MagicMock):
    """Test MetricError if metric_name is not in the registry."""
    with pytest.raises(MetricError, match="Metric 'unknown_metric' not found in registry"):
        MetricCalculationNode(name="test", metric_name="unknown_metric", graph=mock_graph)


def test_metric_node_init_invalid_definition(mock_graph: MagicMock, patch_registry: MagicMock):
    """Test ValueError if metric definition is missing required fields."""
    patch_registry.get.side_effect = (
        lambda key: {"formula": "a", "inputs": ["x"]} if key == "invalid_metric_no_desc"
        else {"formula": "a", "description": "desc"} if key == "invalid_metric_no_inputs"
        else {"inputs": ["a"], "description": "desc"} if key == "invalid_metric_no_formula"
        else KeyError
    )

    # Test missing description
    with pytest.raises(
        ValueError, match=r"invalid: missing required field\(s\): \['description'\]"
    ):
        MetricCalculationNode(name="test", metric_name="invalid_metric_no_desc", graph=mock_graph)

    # Test missing inputs
    with pytest.raises(
        ValueError, match=r"invalid: missing required field\(s\): \['inputs'\]"
    ):
        MetricCalculationNode(name="test", metric_name="invalid_metric_no_inputs", graph=mock_graph)

    # Test missing formula
    with pytest.raises(
        ValueError, match=r"invalid: missing required field\(s\): \['formula'\]"
    ):
        MetricCalculationNode(name="test", metric_name="invalid_metric_no_formula", graph=mock_graph)


def test_metric_node_init_input_node_not_in_graph(mock_graph: MagicMock, patch_registry: MagicMock):
    """Test ConfigurationError if a required input node is not in the graph."""
    patch_registry.get.return_value = {
        "description": "Test metric",
        "inputs": ["revenue_item", "missing_input"],
        "formula": "revenue_item - missing_input",
    }
    patch_registry.get.side_effect = None  # Use return_value

    with pytest.raises(
        ConfigurationError,
        match=r"Input node\(s\) required by metric 'gross_profit' not found in graph: \['missing_input'\]",
    ):
        MetricCalculationNode(name="test", metric_name="gross_profit", graph=mock_graph)


def test_metric_node_init_input_not_a_node(mock_graph: MagicMock, patch_registry: MagicMock):
    """Test TypeError if a resolved input is not a Node instance."""
    patch_registry.get.return_value = {
        "description": "Test metric",
        "inputs": ["revenue_item", "non_node_item"],
        "formula": "revenue_item - non_node_item",
    }
    patch_registry.get.side_effect = None  # Use return_value

    with pytest.raises(
        TypeError,
        match="Resolved input 'non_node_item' for metric 'gross_profit' is not a Node instance",
    ):
        MetricCalculationNode(name="test", metric_name="gross_profit", graph=mock_graph)


def test_metric_node_init_formula_node_error(mock_graph: MagicMock, patch_registry: MagicMock):
    """Test ValueError if internal FormulaCalculationNode init fails (e.g., bad formula)."""
    patch_registry.get.return_value = {
        "description": "Test metric",
        "inputs": ["revenue_item", "cogs_item"],
        "formula": "revenue_item -",
    }
    patch_registry.get.side_effect = None  # Use return_value

    with pytest.raises(
        ValueError,
        match="Error creating formula node for metric 'gross_profit'.*Invalid formula syntax",
    ):
        MetricCalculationNode(name="test", metric_name="gross_profit", graph=mock_graph)


def test_metric_node_calculate_success(mock_graph: MagicMock):
    """Test successful calculation."""
    node = MetricCalculationNode(name="gp_calc", metric_name="gross_profit", graph=mock_graph)
    # 2023: 500 - 200 = 300
    assert node.calculate("2023") == pytest.approx(300.0)
    # 2024: 600 - 250 = 350
    assert node.calculate("2024") == pytest.approx(350.0)


def test_metric_node_calculate_error_propagation(mock_graph: MagicMock, node_rev: Node):
    """Test that CalculationError from the internal node is propagated correctly."""
    # Make one of the input nodes raise an error during calculation
    original_calculate = node_rev.calculate

    def failing_calculate(period):
        if period == "2023":
            raise CalculationError("Input failed!", node_id="revenue_item", period="2023")
        return original_calculate(period)

    node_rev.calculate = failing_calculate

    node = MetricCalculationNode(name="gp_calc_fail", metric_name="gross_profit", graph=mock_graph)

    with pytest.raises(CalculationError) as exc_info:
        node.calculate("2023")

    # Restore original method
    node_rev.calculate = original_calculate

    # Check error details
    assert "Failed to calculate metric 'gross_profit'" in exc_info.value.message
    assert exc_info.value.node_id == "gp_calc_fail"
    assert exc_info.value.period == "2023"
    assert "Input failed!" in exc_info.value.details["original_error"]
