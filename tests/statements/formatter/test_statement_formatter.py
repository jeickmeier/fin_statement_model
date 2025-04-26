"""Unit tests for the StatementFormatter class."""

import pytest
import pandas as pd

# Imports from your project (adjust paths as necessary)
from fin_statement_model.statements.formatter.statement_formatter import StatementFormatter
from fin_statement_model.statements.structure.containers import StatementStructure, Section
from fin_statement_model.statements.structure.items import LineItem, SubtotalLineItem

# --- Fixtures --- #

@pytest.fixture
def sample_income_structure() -> StatementStructure:
    """Create a sample income statement structure for testing."""
    structure = StatementStructure(id="income_statement", name="Income Statement")
    revenue_section = Section(id="revenue_sec", name="Revenue")
    revenue_section.add_item(LineItem(id="revenue", name="Total Revenue", node_id="revenue_node"))
    structure.add_section(revenue_section)

    cogs_section = Section(id="cogs_sec", name="Cost of Goods Sold")
    cogs_section.add_item(
        LineItem(id="cogs", name="Cost of Goods Sold", node_id="cogs_node", sign_convention=-1)
    )
    cogs_section.add_item(
        SubtotalLineItem(id="gross_profit", name="Gross Profit", item_ids=["revenue", "cogs"])
    )
    structure.add_section(cogs_section)

    opex_section = Section(id="opex_sec", name="Operating Expenses")
    opex_section.add_item(
        LineItem(id="sga", name="SG&A", node_id="sga_node", sign_convention=-1)
    )
    opex_section.add_item(
        LineItem(id="rnd", name="R&D", node_id="rnd_node", sign_convention=-1)
    )
    opex_section.add_item(
        SubtotalLineItem(
            id="operating_expenses",
            name="Total Operating Expenses",
            item_ids=["sga", "rnd"],
            sign_convention=-1, # Subtotal itself can have sign convention
        )
    )
    opex_section.add_item(
        SubtotalLineItem(
            id="operating_income",
            name="Operating Income",
            item_ids=["gross_profit", "operating_expenses"],
        )
    )
    structure.add_section(opex_section)

    return structure

@pytest.fixture
def sample_data() -> pd.DataFrame:
    """Create sample financial data DataFrame."""
    data = {
        "2023": [1000, 250, 50, 100],
        "2024": [1200, 300, 60, 110],
    }
    index = ["revenue", "cogs", "sga", "rnd"] # Note: Only raw data, no calculated items yet
    return pd.DataFrame(data, index=index)

# --- Test Cases --- #

def test_formatter_initialization(sample_income_structure):
    """Test successful initialization of StatementFormatter."""
    formatter = StatementFormatter(structure=sample_income_structure)
    assert formatter.structure == sample_income_structure
    assert formatter.add_subtotals is True
    assert formatter.apply_sign_convention is True

def test_formatter_init_type_error():
    """Test TypeError if structure is not StatementStructure."""
    with pytest.raises(TypeError, match="`structure` must be an instance of StatementStructure"):
        StatementFormatter(structure="not a structure")

def test_add_subtotals(sample_income_structure, sample_data):
    """Test that _add_subtotals correctly calculates and adds rows."""
    formatter = StatementFormatter(structure=sample_income_structure, apply_sign_convention=False)
    # Manually call _add_subtotals for isolated testing
    result_df = formatter._add_subtotals(sample_data.copy())

    assert "gross_profit" in result_df.index
    assert "operating_expenses" in result_df.index
    assert "operating_income" in result_df.index

    # Check calculations (assumes cogs is positive in input data before sign convention)
    pd.testing.assert_series_equal(
        result_df.loc["gross_profit"], sample_data.loc["revenue"] + sample_data.loc["cogs"], check_names=False
    )
    pd.testing.assert_series_equal(
        result_df.loc["operating_expenses"], sample_data.loc["sga"] + sample_data.loc["rnd"], check_names=False
    )
    # Check op income = gross_profit + operating_expenses (using calculated values)
    expected_op_income = (
        result_df.loc["gross_profit"] + result_df.loc["operating_expenses"]
    )
    pd.testing.assert_series_equal(
        result_df.loc["operating_income"], expected_op_income, check_names=False
    )

def test_apply_sign_convention(sample_income_structure, sample_data):
    """Test that _apply_sign_convention flips signs correctly based on structure."""
    formatter = StatementFormatter(structure=sample_income_structure, add_subtotals=False)
    # Manually call _apply_sign_convention for isolated testing
    result_df = formatter._apply_sign_convention(sample_data.copy())

    # Items defined with sign_convention=-1 should be negative if originally positive
    assert (result_df.loc["cogs"] < 0).all()
    assert (result_df.loc["sga"] < 0).all()
    assert (result_df.loc["rnd"] < 0).all()
    # Revenue should remain positive
    assert (result_df.loc["revenue"] > 0).all()

def test_reorder_items(sample_income_structure, sample_data):
    """Test that _reorder_items orders rows according to structure."""
    # Add dummy data for calculated items to test ordering
    data_with_calc = sample_data.copy()
    data_with_calc.loc["gross_profit"] = 0
    data_with_calc.loc["operating_expenses"] = 0
    data_with_calc.loc["operating_income"] = 0

    formatter = StatementFormatter(structure=sample_income_structure)
    result_df = formatter._reorder_items(data_with_calc)

    expected_order = [
        "revenue",
        "cogs",
        "gross_profit",
        "sga",
        "rnd",
        "operating_expenses",
        "operating_income",
    ]
    assert result_df.index.tolist() == expected_order

def test_transform_integration(sample_income_structure, sample_data):
    """Test the full transform method integration."""
    formatter = StatementFormatter(structure=sample_income_structure)
    result_df = formatter.transform(sample_data.copy())

    # Check final order
    expected_order = [
        "revenue",
        "cogs",
        "gross_profit",
        "sga",
        "rnd",
        "operating_expenses",
        "operating_income",
    ]
    assert result_df.index.tolist() == expected_order

    # Check sign conventions applied
    assert (result_df.loc["cogs"] < 0).all()
    assert (result_df.loc["sga"] < 0).all()
    assert (result_df.loc["rnd"] < 0).all()
    assert (result_df.loc["operating_expenses"] < 0).all() # Check subtotal sign too

    # Check a final calculation (Operating Income)
    # Revenue (pos) + COGS (neg) = Gross Profit
    # Gross Profit + OpEx (neg) = Operating Income
    expected_gp = sample_data["2023"]["revenue"] - sample_data["2023"]["cogs"]
    expected_opex = sample_data["2023"]["sga"] + sample_data["2023"]["rnd"]
    expected_op_income_2023 = expected_gp - expected_opex
    assert result_df.loc["operating_income", "2023"] == expected_op_income_2023

    expected_gp_24 = sample_data["2024"]["revenue"] - sample_data["2024"]["cogs"]
    expected_opex_24 = sample_data["2024"]["sga"] + sample_data["2024"]["rnd"]
    expected_op_income_2024 = expected_gp_24 - expected_opex_24
    assert result_df.loc["operating_income", "2024"] == expected_op_income_2024 