"""Tests for statement configuration validation logic."""

from fin_statement_model.statements.configs.validator import StatementConfig
import pytest


def test_validate_success():
    """Valid minimal config should produce no errors."""
    data = {"id": "s1", "name": "Stmt1", "sections": []}
    cfg = StatementConfig(config_data=data)
    errors = cfg.validate_config()
    assert errors == []


def test_validate_missing_fields():
    """Missing id, name, and sections should all be reported."""
    data = {}
    # Expect ValueError during __init__ for empty config_data
    with pytest.raises(ValueError, match="config_data must be a non-empty dictionary."):
        StatementConfig(config_data=data)


def test_validate_id_no_spaces():
    """IDs containing spaces should be rejected."""
    data = {"id": "with space", "name": "n", "sections": []}
    cfg = StatementConfig(config_data=data)
    errors = cfg.validate_config()
    # Adjust expected Pydantic error message format
    assert errors == ["id: Value error, must not contain spaces"]


def test_validate_duplicate_section_ids():
    """Top-level sections must have unique IDs."""
    data = {
        "id": "s1",
        "name": "n",
        "sections": [
            {"id": "a", "name": "A", "items": []},
            {"id": "a", "name": "B", "items": []},
        ],
    }
    cfg = StatementConfig(config_data=data)
    errors = cfg.validate_config()
    assert any("Duplicate section id(s): a" in e for e in errors)


def test_validate_duplicate_item_ids_in_section():
    """Items within a section must have unique IDs."""
    data = {
        "id": "s1",
        "name": "n",
        "sections": [
            {
                "id": "sec",
                "name": "S",
                "items": [
                    {"id": "i", "name": "I", "type": "line_item", "node_id": "n"},
                    {"id": "i", "name": "I2", "type": "line_item", "node_id": "n"},
                ],
            }
        ],
    }
    cfg = StatementConfig(config_data=data)
    errors = cfg.validate_config()
    assert any("Duplicate item id(s) in section 'sec': i" in e for e in errors)


def test_validate_subtotal_invalid_ref():
    """Subtotal must reference existing item IDs only."""
    data = {
        "id": "s1",
        "name": "n",
        "sections": [
            {
                "id": "sec",
                "name": "S",
                "items": [
                    {"id": "i1", "name": "I1", "type": "line_item", "node_id": "n"}
                ],
                "subtotal": {"id": "sub", "name": "Sum", "items_to_sum": ["i1", "x"]},
            }
        ],
    }
    cfg = StatementConfig(config_data=data)
    errors = cfg.validate_config()
    assert any("subtotal references undefined ids: x" in e.lower() for e in errors)
