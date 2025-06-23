from __future__ import annotations

import pytest

from fin_statement_model.config.access import (
    cfg,
    ConfigurationAccessError,
    parse_env_value,
)


def test_cfg_strict_mode_raises_error() -> None:
    with pytest.raises(ConfigurationAccessError):
        cfg("nonexistent.key", strict=True)


def test_cfg_default_return() -> None:
    # Non-strict with default should return default value
    assert cfg("another.missing", default=42) == 42


def test_parse_env_value_edge_cases() -> None:
    # Float in scientific notation
    assert parse_env_value("1e3") == 1000.0
    # Negative integer string
    assert parse_env_value("-10") == -10
