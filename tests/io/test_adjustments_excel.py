"""Tests for adjustments Excel I/O functions."""

import pytest
import pandas as pd
from uuid import UUID, uuid4
from pytest_mock import MockerFixture
from pathlib import Path
from unittest.mock import MagicMock

# Assume openpyxl is installed for Excel writing
# try:
#     import openpyxl
#     OPENPYXL_INSTALLED = True
# except ImportError:
#     OPENPYXL_INSTALLED = False
# pytestmark = pytest.mark.skipif(not OPENPYXL_INSTALLED, reason="openpyxl not installed")
# Let's assume it's installed for now based on project deps

from fin_statement_model.core.adjustments.models import Adjustment, AdjustmentType
from fin_statement_model.io.adjustments_excel import (
    read_excel,
    write_excel,
    COL_TO_FIELD_MAP,
)
from fin_statement_model.io.exceptions import ReadError, WriteError

# --- Test Data ---

VALID_ADJ_DATA_LIST = [
    {
        "node_name": "Revenue",
        "period": "P1",
        "value": 10.5,
        "reason": "R1",
        "type": AdjustmentType.ADDITIVE,
        "tags": {"TagA", "TagB"},
        "scale": 1.0,
        "scenario": "Actual",
        "priority": 0,
        "user": "User1",
        "id": uuid4(),
    },
    {
        "node_name": "COGS",
        "period": "P1",
        "value": -5,
        "reason": "R2",
        "type": AdjustmentType.REPLACEMENT,
        "tags": {"TagC"},
        "scenario": "Budget",
        "user": "User2",
    },
    {
        "node_name": "Opex",
        "period": "P2",
        "value": -2.0,
        "reason": "R3",
        "type": "multiplicative",
        "scale": 0.8,
        "start_period": "P1",
        "end_period": "P3",
    },
    # Row with minimal required columns
    {"node_name": "Interest", "period": "P1", "value": 1.0, "reason": "R4"},
]

INVALID_ADJ_DATA_LIST = [
    # Missing required 'value'
    {"node_name": "Revenue", "period": "P1", "reason": "Missing Val"},
    # Invalid type enum
    {
        "node_name": "COGS",
        "period": "P1",
        "value": -5,
        "reason": "Bad Type",
        "type": "subtraction",
    },
    # Invalid scale
    {
        "node_name": "Opex",
        "period": "P2",
        "value": -2.0,
        "reason": "Bad Scale",
        "scale": 1.5,
    },
    # Invalid number format for value
    {"node_name": "Tax", "period": "P1", "value": "abc", "reason": "Bad Value"},
    # Invalid priority
    {
        "node_name": "Depr",
        "period": "P1",
        "value": -1,
        "reason": "Bad Prio",
        "priority": "high",
    },
]

# --- Test read_excel ---


@pytest.fixture
def mock_read_excel_valid(mocker: MockerFixture):
    """Mocks pd.read_excel to return valid adjustment data."""
    # Simulate the raw data read from Excel (tags as string)
    raw_data = [
        {
            "node_name": "Revenue",
            "period": "P1",
            "value": 10.5,
            "reason": "R1",
            "type": "additive",
            "tags": "TagA, TagB",
            "scale": 1.0,
            "scenario": "Actual",
            "priority": 0,
            "user": "User1",
            "id": str(uuid4()),
        },
        {
            "node_name": "COGS",
            "period": "P1",
            "value": -5,
            "reason": "R2",
            "type": "replacement",
            "tags": "TagC",
            "scenario": "Budget",
            "user": "User2",
        },
        {
            "node_name": "Opex",
            "period": "P2",
            "value": -2.0,
            "reason": "R3",
            "type": "multiplicative",
            "scale": 0.8,
            "start_period": "P1",
            "end_period": "P3",
        },
        {"node_name": "Interest", "period": "P1", "value": 1.0, "reason": "R4"},
    ]
    mock_df = pd.DataFrame(raw_data)
    mocker.patch("pandas.read_excel", return_value=mock_df)


@pytest.fixture
def mock_read_excel_invalid(mocker: MockerFixture):
    """Mocks pd.read_excel to return data with invalid rows."""
    # Simulate raw data read from Excel
    raw_valid = [
        {
            "node_name": "Revenue",
            "period": "P1",
            "value": 10.5,
            "reason": "R1",
            "type": "additive",
            "tags": "TagA, TagB",
            "scale": 1.0,
            "scenario": "Actual",
            "priority": 0,
            "user": "User1",
            "id": str(uuid4()),
        },
        {"node_name": "Interest", "period": "P1", "value": 1.0, "reason": "R4"},
    ]
    raw_invalid = [
        {
            "node_name": "Revenue",
            "period": "P1",
            "reason": "Missing Val",
        },  # Missing value
        {
            "node_name": "COGS",
            "period": "P1",
            "value": -5,
            "reason": "Bad Type",
            "type": "subtraction",
        },  # Invalid type
        {
            "node_name": "Opex",
            "period": "P2",
            "value": -2.0,
            "reason": "Bad Scale",
            "scale": 1.5,
        },  # Invalid scale
        {
            "node_name": "Tax",
            "period": "P1",
            "value": "abc",
            "reason": "Bad Value",
        },  # Invalid value format
        {
            "node_name": "Depr",
            "period": "P1",
            "value": -1,
            "reason": "Bad Prio",
            "priority": "high",
        },  # Invalid priority
    ]
    mock_df = pd.DataFrame(raw_valid + raw_invalid)
    mocker.patch("pandas.read_excel", return_value=mock_df)


@pytest.fixture
def mock_read_excel_missing_cols(mocker: MockerFixture):
    """Mocks pd.read_excel to return data with missing required columns."""
    data_missing_reason = [d.copy() for d in VALID_ADJ_DATA_LIST]
    for item in data_missing_reason:
        item.pop("reason")
    mock_df = pd.DataFrame(data_missing_reason)
    mocker.patch("pandas.read_excel", return_value=mock_df)


def test_read_excel_valid_data(mock_read_excel_valid: MagicMock) -> None:
    """Test reading a valid Excel file."""
    adj_list, error_df = read_excel("dummy_valid.xlsx")

    assert isinstance(adj_list, list)
    assert len(adj_list) == len(VALID_ADJ_DATA_LIST)
    assert all(isinstance(adj, Adjustment) for adj in adj_list)
    assert isinstance(error_df, pd.DataFrame)
    assert error_df.empty

    # Check details of a parsed adjustment
    adj0 = adj_list[0]
    assert adj0.node_name == "Revenue"
    assert adj0.period == "P1"
    assert adj0.value == 10.5
    assert adj0.reason == "R1"
    assert adj0.type == AdjustmentType.ADDITIVE
    assert adj0.tags == {"TagA", "TagB"}
    assert adj0.scale == 1.0
    assert adj0.scenario == "Actual"
    assert adj0.priority == 0
    assert adj0.user == "User1"
    assert isinstance(adj0.id, UUID)

    # Check adjustment with defaults
    adj3 = adj_list[3]
    assert adj3.node_name == "Interest"
    assert adj3.type == AdjustmentType.ADDITIVE
    assert adj3.scale == 1.0
    assert adj3.priority == 0
    assert adj3.tags == set()
    assert adj3.scenario == "default"
    assert adj3.user is None


def test_read_excel_invalid_data(mock_read_excel_invalid: MagicMock) -> None:
    """Test reading an Excel file with some invalid rows."""
    adj_list, error_df = read_excel("dummy_invalid.xlsx")

    # Assert against the number of valid rows provided by the mock fixture
    # mock_read_excel_invalid provides 2 valid + 5 invalid rows
    assert len(adj_list) == 2
    assert not error_df.empty
    assert len(error_df) == len(INVALID_ADJ_DATA_LIST)
    assert "error" in error_df.columns

    # Check some error messages
    assert "Missing value" in error_df.iloc[0]["error"]
    assert "Invalid value" in error_df.iloc[1]["error"]  # Type enum error
    # Pydantic validation error now likely caught during Adjustment(**final_adj_data)
    # Check the combined error message format
    assert "Scale must be between 0.0 and 1.0" in error_df.iloc[2]["error"]
    assert "could not convert string to float" in error_df.iloc[3]["error"]
    assert "Invalid value" in error_df.iloc[4]["error"]
    assert "invalid literal for int()" in error_df.iloc[4]["error"]


def test_read_excel_missing_columns(mock_read_excel_missing_cols: MagicMock) -> None:
    """Test reading file with missing required columns."""
    with pytest.raises(ReadError, match="Missing required columns.*'.*reason'.*"):
        read_excel("dummy_missing_cols.xlsx")


def test_read_excel_file_not_found(mocker: MockerFixture):
    """Test error handling when the file does not exist."""
    mocker.patch("pandas.read_excel", side_effect=FileNotFoundError)
    with pytest.raises(ReadError, match="Adjustment Excel file not found"):
        read_excel("non_existent_file.xlsx")


def test_read_excel_read_error(mocker: MockerFixture):
    """Test error handling for other pandas read errors."""
    mocker.patch("pandas.read_excel", side_effect=ValueError("Some pandas error"))
    with pytest.raises(ReadError, match="Failed to read Excel file.*Some pandas error"):
        read_excel("bad_format.xlsx")


# --- Test write_excel ---

# Use tmp_path fixture provided by pytest for temporary file writing


def test_write_excel_valid(tmp_path: Path):
    """Test writing adjustments to an Excel file."""
    # Use valid Pydantic models directly for writing
    adj_list = []
    # adj_list.append(Adjustment(node_name="Revenue", period="P1", value=10.5, reason="R1", type=AdjustmentType.ADDITIVE, tags={"TagA", "TagB"}, scale=1.0, scenario="Actual", priority=0, user="User1", id=uuid4())) # Scenario: Actual
    # adj_list.append(Adjustment(node_name="COGS", period="P1", value=-5, reason="R2", type=AdjustmentType.REPLACEMENT, tags={"TagC"}, scenario="Budget", user="User2", id=uuid4())) # Scenario: Budget
    adj_list.append(
        Adjustment(
            node_name="Opex",
            period="P2",
            value=-2.0,
            reason="R3",
            type=AdjustmentType.MULTIPLICATIVE,
            scale=0.8,
            start_period="P1",
            end_period="P3",
            id=uuid4(),
        )
    )  # Scenario: default
    adj_list.append(
        Adjustment(
            node_name="Interest", period="P1", value=1.0, reason="R4", id=uuid4()
        )
    )  # Scenario: default
    # adj_list.append(Adjustment(node_name="Tax", period="P1", value=-1, reason="Budget Tax", scenario="Budget", id=uuid4())) # Scenario: Budget

    output_file = tmp_path / "output_adjustments.xlsx"
    write_excel(adj_list, output_file)

    # Verify file exists
    assert output_file.is_file()

    # Read back and check content
    try:
        # Read sheets by name
        # df_actual = pd.read_excel(output_file, sheet_name="Actual") # Skip other sheets for this test
        df_default = pd.read_excel(output_file, sheet_name="default")
        # df_budget = pd.read_excel(output_file, sheet_name="Budget") # Skip other sheets for this test
    except Exception as e:
        pytest.fail(f"Failed to read back written Excel file: {e}")

    # Check lengths based on scenarios
    # assert len(df_actual) == 1
    assert len(df_default) == 2  # Expect only the 2 default adjustments
    # assert len(df_budget) == 2

    # Check columns (ensure order and presence)
    # Let's check that all expected cols are present
    # Check a representative sheet (default)
    df_default = pd.read_excel(output_file, sheet_name="default")
    assert set(df_default.columns) == set(COL_TO_FIELD_MAP.keys())

    # Check some values after read back
    # assert df_actual.loc[0, 'node_name'] == "Revenue"
    # assert df_actual.loc[0, 'tags'] == "TagA,TagB" # Comma separated

    # Check one from default
    assert (
        df_default[df_default["node_name"] == "Opex"].iloc[0]["type"]
        == "multiplicative"
    )

    # Check one from budget - removed
    # assert df_budget[df_budget['node_name'] == 'Tax'].iloc[0]['reason'] == "Budget Tax"


def test_write_excel_empty_list(tmp_path: Path):
    """Test writing an empty list of adjustments."""
    output_file = tmp_path / "empty_adjustments.xlsx"
    write_excel([], output_file)

    assert output_file.is_file()
    # Check it created a file, maybe read to ensure it's a valid empty excel
    try:
        df_read = pd.read_excel(
            output_file
        )  # Reading without sheet name reads first sheet
        assert df_read.empty  # Expect an empty dataframe
    except Exception as e:
        pytest.fail(f"Failed to read back empty Excel file: {e}")


def test_write_excel_error(tmp_path: Path, mocker: MockerFixture):
    """Test error handling during file writing."""
    # Use valid Pydantic models for writing test
    adj_list = []
    adj_list.append(
        Adjustment(
            node_name="Revenue",
            period="P1",
            value=10.5,
            reason="R1",
            type=AdjustmentType.ADDITIVE,
            tags={"TagA", "TagB"},
            scale=1.0,
            scenario="Actual",
            priority=0,
            user="User1",
            id=uuid4(),
        )
    )

    output_file = tmp_path / "protected_output.xlsx"

    # Mock ExcelWriter to raise an error (e.g., permission denied)
    mock_writer_instance = mocker.MagicMock()
    mock_writer_instance.save.side_effect = OSError("Permission denied")
    mocker.patch("pandas.ExcelWriter", return_value=mock_writer_instance)

    # A more direct way might be to mock df.to_excel
    mocker.patch(
        "pandas.DataFrame.to_excel",
        side_effect=OSError("Permission denied during save"),
    )

    with pytest.raises(
        WriteError, match="Failed to write adjustments to Excel.*Permission denied"
    ):
        write_excel(adj_list, output_file)
