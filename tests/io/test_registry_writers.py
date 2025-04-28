# tests/io/test_registry_writers.py
"""Tests for the writer registry in fin_statement_model.io.registry_writers."""

import pytest
from pathlib import Path

from fin_statement_model.io.registry import get_writer, list_writers
from fin_statement_model.io.exceptions import FormatNotSupportedError, WriteError
from fin_statement_model.io.config.models import (
    ExcelWriterConfig,
    DataFrameWriterConfig,
    DictWriterConfig,
)


def test_list_writers_contains_expected_formats() -> None:
    """Assert that known writer formats are registered."""
    writers = list_writers()
    assert "excel" in writers
    assert "dataframe" in writers
    assert "dict" in writers


@pytest.mark.parametrize(
    ("format_type", "config_class", "extra_kwargs"),
    [
        (
            "excel",
            ExcelWriterConfig,
            {
                "sheet_name": "MySheet",
                "recalculate": False,
                "include_nodes": ["A", "B"],
                "excel_writer_kwargs": {"engine": "openpyxl"},
            },
        ),
        (
            "dataframe",
            DataFrameWriterConfig,
            {"recalculate": True, "include_nodes": None},
        ),
        ("dict", DictWriterConfig, {}),
    ],
)
def test_get_writer_success(
    format_type: str,
    config_class: type,
    extra_kwargs: dict,
    tmp_path: Path,
) -> None:
    """Test get_writer returns correct writer instance and config."""
    target = str(tmp_path / f"output.{format_type}")
    kwargs = {"target": target, **extra_kwargs}
    writer = get_writer(format_type, **kwargs)
    assert hasattr(writer, "cfg"), "Writer should have cfg attribute"
    cfg = writer.cfg
    assert isinstance(cfg, config_class)
    assert cfg.target == target
    assert cfg.format_type == format_type


def test_get_writer_unknown_format_raises() -> None:
    """Test get_writer raises FormatNotSupportedError for unknown writer."""
    with pytest.raises(FormatNotSupportedError):
        get_writer("unknown", target="x")


def test_get_writer_invalid_extra_field_raises_write_error() -> None:
    """Test get_writer raises WriteError for invalid init kwargs."""
    with pytest.raises(WriteError):
        get_writer("excel", target="x", invalid_field="value")
