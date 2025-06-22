from __future__ import annotations

"""Tests covering CsvReader happy-path and common failure scenarios.

These tests intentionally keep the CSV payload minimal to avoid fragile
string parsing while still exercising period detection, mapping, and
error handling paths in *CsvReader* and the shared *file_utils* helpers.
"""

from pathlib import Path

import pandas as pd
import pytest

from fin_statement_model.io import read_data
from fin_statement_model.io.exceptions import ReadError
from fin_statement_model.io.core.file_utils import (
    validate_file_exists,
    validate_file_extension,
)


# -----------------------------------------------------------------------------
# CsvReader happy-path
# -----------------------------------------------------------------------------


def _write_simple_csv(tmp_path: Path) -> Path:
    """Create a tiny CSV file in long format and return its path."""
    csv_path = tmp_path / "simple.csv"
    df = pd.DataFrame(
        {
            "item": ["Revenue", "Revenue", "COGS", "COGS"],
            "period": ["2023", "2024", "2023", "2024"],
            "value": [100, 110, 60, 65],
        }
    )
    df.to_csv(csv_path, index=False)
    return csv_path


def test_csv_reader_basic(tmp_path: Path) -> None:
    """CsvReader should parse the sample file into a Graph with correct values."""
    path = _write_simple_csv(tmp_path)

    graph = read_data(
        format_type="csv",
        source=str(path),
        config={
            "item_col": "item",
            "period_col": "period",
            "value_col": "value",
            "delimiter": ",",
        },
    )

    assert graph.get_node("Revenue").calculate("2024") == 110
    assert graph.get_node("COGS").calculate("2023") == 60


# -----------------------------------------------------------------------------
# CsvReader – invalid extension triggers ReadError via validate_file_extension
# -----------------------------------------------------------------------------


def test_csv_reader_invalid_extension(tmp_path: Path) -> None:
    """A file with an unsupported extension should raise *ReadError*."""
    bad_path = tmp_path / "data.txt-notcsv"
    bad_path.write_text("irrelevant content", encoding="utf-8")

    with pytest.raises(ReadError):
        # We still pass CsvReader config; failure expected during extension check
        read_data(
            format_type="csv",
            source=str(bad_path),
            config={
                "item_col": "item",
                "period_col": "period",
                "value_col": "value",
            },
        )


# -----------------------------------------------------------------------------
# file_utils helpers – direct unit tests (no Graph involvement)
# -----------------------------------------------------------------------------


def test_validate_file_helpers(tmp_path: Path) -> None:
    """validate_file_exists / validate_file_extension basic behaviour."""
    test_file = tmp_path / "tiny.csv"
    test_file.write_text("a,b\n1,2\n", encoding="utf-8")

    # Should not raise for existing file and correct extension
    validate_file_exists(str(test_file))
    validate_file_extension(str(test_file), valid_extensions=(".csv",))

    # Non-existent file triggers ReadError
    with pytest.raises(ReadError):
        validate_file_exists(str(test_file) + "_missing")

    # Wrong extension triggers ReadError
    with pytest.raises(ReadError):
        validate_file_extension(str(test_file), valid_extensions=(".xlsx",))
