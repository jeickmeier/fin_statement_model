import json
import pytest

from fin_statement_model.statements.config.loader import (
    load_statement_config,
    list_built_in_statements,
    load_built_in_statement,
)
from fin_statement_model.statements.errors import ConfigurationError


def test_list_built_in_statements_empty(tmp_path, monkeypatch):
    # Point mapping dir to a temp empty directory
    monkeypatch.setenv("FIN_STATEMENTS_MAPPING_DIR", str(tmp_path))
    # Reload module to pick up monkeypatched env if needed
    # Currently loader reads default dir; so without mapping files, expect empty
    names = list_built_in_statements()
    assert isinstance(names, list)
    assert names == []


def test_load_statement_config_valid(tmp_path):
    # Create a minimal JSON config file
    data = {"id": "s1", "name": "Statement 1", "sections": []}
    cfg_file = tmp_path / "stmt.json"
    cfg_file.write_text(json.dumps(data))
    struct = load_statement_config(str(cfg_file))
    assert struct.id == "s1"
    assert struct.name == "Statement 1"
    assert struct.sections == []


def test_load_statement_config_invalid(tmp_path):
    # Create invalid YAML/JSON
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("not: [valid YAML")
    with pytest.raises(ConfigurationError):
        load_statement_config(str(bad_file))


def test_load_built_in_statement_not_found():
    # No mapping files exist by default
    with pytest.raises(ConfigurationError) as excinfo:
        load_built_in_statement("nonexistent")
    msg = str(excinfo.value)
    assert "Built-in statement 'nonexistent' not found" in msg.replace("‑", "-")


def test_list_and_load_built_in_statement_present():
    # Built-in mapping 'test_statement' should be discovered and loadable
    names = list_built_in_statements()
    assert "test_statement" in names

    stmt = load_built_in_statement("test_statement")
    assert stmt.id == "test_statement"
    assert stmt.name == "Test Statement"
    # sections defined as empty list in mapping
    assert stmt.sections == []
