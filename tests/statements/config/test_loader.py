"""Tests for statement configuration loading functions."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from fin_statement_model.io.readers.statement_config_reader import (
    read_statement_config_from_path,
    list_available_builtin_configs,
    read_builtin_statement_config,
)
from fin_statement_model.statements.config.config import (
    StatementConfig,
)
from fin_statement_model.io.exceptions import ReadError

# TODO: Remove skip once refactor is complete
# pytest.skip("Skipping tests for refactored statements config reader", allow_module_level=True)


def test_list_built_in_statements_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test listing built-in statements when the mapping directory is empty."""
    # Point mapping dir to a temp empty directory
    # Monkeypatching the internal _get_builtin_config_package might be complex
    # Instead, let's mock importlib.resources.files to simulate empty/missing dir
    with patch("importlib.resources.files") as mock_files:
        mock_path = MagicMock(spec=Path)
        mock_path.is_dir.return_value = False # Simulate non-existent/non-dir path
        mock_files.return_value = mock_path

        names = list_available_builtin_configs()
        assert isinstance(names, list)
        assert names == []

        # Test case where iterdir returns nothing
        mock_path.is_dir.return_value = True
        mock_path.iterdir.return_value = []
        names_empty_iter = list_available_builtin_configs()
        assert names_empty_iter == []


def test_load_statement_config_valid(tmp_path: Path) -> None:
    """Test loading a valid statement config file (JSON/YAML)."""
    # Create a minimal JSON config file
    data = {"id": "s1", "name": "Statement 1", "sections": []}
    cfg_file = tmp_path / "stmt.json"
    cfg_file.write_text(json.dumps(data))
    # read_statement_config_from_path only reads the raw data
    raw_data = read_statement_config_from_path(str(cfg_file))
    assert raw_data == data

    # Validation happens in StatementConfig
    config = StatementConfig(raw_data)
    validation_errors = config.validate_config()
    assert not validation_errors
    assert config.model is not None
    assert config.model.id == "s1"
    assert config.model.name == "Statement 1"
    assert config.model.sections == []


def test_load_statement_config_invalid(tmp_path: Path) -> None:
    """Test loading an invalid or non-existent config file."""
    # Create invalid YAML/JSON
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("invalid: yaml: here")
    # read function raises ReadError for parsing issues
    with pytest.raises(ReadError, match="Invalid YAML format"):
        read_statement_config_from_path(str(bad_file))

    # Test non-existent file
    non_existent_file = tmp_path / "nosuchfile.json"
    with pytest.raises(ReadError, match="Configuration file not found"):
        read_statement_config_from_path(str(non_existent_file))


def test_load_built_in_statement_not_found() -> None:
    """Test trying to load a built-in statement that does not exist."""
    # read_builtin raises ReadError if not found
    with pytest.raises(ReadError, match="Built-in statement config 'nonexistent' not found"):
        read_builtin_statement_config("nonexistent")
