"""Tests for StatementFormatter integration with Adjustments."""

import pytest

from fin_statement_model.core.graph import Graph
from fin_statement_model.statements.formatter import StatementFormatter
from fin_statement_model.statements.structure import (
    StatementStructure,
    Section,
    LineItem,
    SubtotalLineItem,
)
from fin_statement_model.core.adjustments.models import AdjustmentFilter

# --- Test Setup ---


@pytest.fixture
def sample_structure() -> StatementStructure:
    """Basic statement structure for testing."""
    structure = StatementStructure(id="TestStmt", name="Test Statement")

    # Create Assets Section
    assets_section = Section(id="Assets", name="Assets")
    assets_section.add_item(LineItem(id="Cash", name="Cash", node_id="CashNode"))
    assets_section.add_item(LineItem(id="AR", name="Accounts Receivable", node_id="ARNode"))
    # Set subtotal directly on the section object (assuming this reflects structure logic)
    assets_section.subtotal = SubtotalLineItem(
        id="CurrentAssets", name="Total Current Assets", item_ids=["Cash", "AR"]
    )  # Use item_ids

    # Create Equity Section
    equity_section = Section(id="Equity", name="Equity")
    equity_section.add_item(LineItem(id="Stock", name="Common Stock", node_id="StockNode"))
    # Set subtotal directly
    equity_section.subtotal = SubtotalLineItem(
        id="TotalEquity", name="Total Equity", item_ids=["Stock"]
    )  # Use item_ids

    # Add sections to structure
    structure.add_section(assets_section)
    structure.add_section(equity_section)

    return structure


@pytest.fixture
def graph_with_adjustments() -> Graph:
    """Graph with data and some adjustments."""
    graph = Graph(periods=["P1", "P2"])
    # Base data
    graph.add_financial_statement_item("CashNode", {"P1": 100, "P2": 110})
    graph.add_financial_statement_item("ARNode", {"P1": 50, "P2": 60})
    graph.add_financial_statement_item("StockNode", {"P1": 120, "P2": 120})

    # Add some adjustments
    graph.add_adjustment("CashNode", "P1", -10, "Audit Adj", tags={"Audit"}, scenario="Actual")
    graph.add_adjustment("ARNode", "P2", 5, "Late Payment", tags={"Collections"}, scenario="Actual")
    graph.add_adjustment(
        "CashNode", "P1", 50, "Budget Scenario Adj", tags={"Budget"}, scenario="Budget"
    )

    # Add calculated nodes for subtotals (needed for formatter to work)
    # Note: The structure defines inputs based on item IDs, graph needs nodes matching those IDs
    graph.add_calculation("CurrentAssets", ["CashNode", "ARNode"], "addition")
    graph.add_calculation("TotalEquity", ["StockNode"], "addition")  # Sum of one item

    return graph


@pytest.fixture
def formatter(sample_structure: StatementStructure) -> StatementFormatter:
    """StatementFormatter instance."""
    return StatementFormatter(sample_structure)


# --- Formatter Tests ---


def test_formatter_no_filter_no_flag(
    formatter: StatementFormatter, graph_with_adjustments: Graph
) -> None:
    """Test default formatting: should apply default scenario adjustments."""
    df = formatter.generate_dataframe(graph_with_adjustments)

    # Check shape and columns (no is_adjusted flag)
    assert df.shape == (5, 4)  # 3 items + 2 subtotals, Line Item + ID + P1 + P2
    assert list(df.columns) == ["Line Item", "ID", "P1", "P2"]

    # Check adjusted values (default filter applies DEFAULT_SCENARIO adjustments ONLY)
    # The 'Actual' scenario adjustment for Cash P1 should NOT be applied here.
    cash_row = df[df["ID"] == "Cash"].iloc[0]
    assert cash_row["P1"] == "100.00"  # Base value
    assert cash_row["P2"] == "110.00"  # Unadjusted

    ar_row = df[df["ID"] == "AR"].iloc[0]
    assert ar_row["P1"] == "50.00"  # Unadjusted
    assert ar_row["P2"] == "60.00"  # Actual scenario adj ignored

    # Check subtotal includes adjusted values (SHOULD BE BASE VALUES NOW)
    ca_row = df[df["ID"] == "CurrentAssets"].iloc[0]
    assert ca_row["P1"] == "150.00"  # 100 + 50 (Base values)
    assert ca_row["P2"] == "170.00"  # 110 + 60 (Base values)


def test_formatter_unadjusted_view(
    formatter: StatementFormatter, graph_with_adjustments: Graph
) -> None:
    """Test formatting with a filter that selects NO adjustments."""
    # An empty filter object should result in no adjustments applied
    # As per AdjustmentManager._normalize_filter, this needs include_scenarios={}
    no_adj_filter = AdjustmentFilter(include_scenarios=set())  # Filter that matches nothing
    df = formatter.generate_dataframe(graph_with_adjustments, adjustment_filter=no_adj_filter)

    # Check base values (no adjustments applied)
    cash_row = df[df["ID"] == "Cash"].iloc[0]
    assert cash_row["P1"] == "100.00"
    assert cash_row["P2"] == "110.00"

    ar_row = df[df["ID"] == "AR"].iloc[0]
    assert ar_row["P1"] == "50.00"
    assert ar_row["P2"] == "60.00"

    # Check subtotal
    ca_row = df[df["ID"] == "CurrentAssets"].iloc[0]
    assert ca_row["P1"] == "150.00"  # 100 + 50
    assert ca_row["P2"] == "170.00"  # 110 + 60
