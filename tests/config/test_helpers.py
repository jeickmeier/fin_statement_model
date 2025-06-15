import os

import pytest
from pydantic import ValidationError

from fin_statement_model.config import update_config
from fin_statement_model.config.helpers import (
    ConfigurationAccessError,
    cfg,
    cfg_or_param,
    get_typed_config,
    parse_env_value,
)
from fin_statement_model.config.manager import ConfigManager


@pytest.fixture(autouse=True)
def reset_config_manager(monkeypatch):
    # Reset global config manager to fresh instance and clear env vars
    import fin_statement_model.config.manager as cm_module

    monkeypatch.setattr(cm_module, "_config_manager", ConfigManager())
    # Clear FSM_ env vars and FMP_API_KEY
    for key in list(os.environ.keys()):
        if key.startswith("FSM_") or key == "FMP_API_KEY":
            monkeypatch.delenv(key, raising=False)
    yield


def test_cfg_returns_value_and_default():
    # Default config logging.level is 'WARNING'
    assert cfg("logging.level") == "WARNING"
    # Provide default fallback for nonexistent key
    assert cfg("nonexistent.key", default="foo") == "foo"


def test_cfg_raises_on_missing_without_default():
    with pytest.raises(ConfigurationAccessError):
        cfg("nonexistent.key")


def test_cfg_with_sequence_path_and_override():
    # Default forecasting.default_periods is 5
    assert cfg(["forecasting", "default_periods"]) == 5
    # Override via update_config
    update_config({"forecasting": {"default_periods": 10}})
    assert cfg("forecasting.default_periods") == 10


def test_get_typed_config_correct_type_and_default():
    # Logging level is str
    lvl = get_typed_config("logging.level", str)
    assert isinstance(lvl, str)
    # Use default when missing
    val = get_typed_config("nonexistent.key", int, default=42)
    assert val == 42


def test_get_typed_config_wrong_type_raises():
    update_config({"logging": {"level": 123}})
    with pytest.raises(ValidationError):
        get_typed_config("logging.level", str)


def test_get_typed_config_none_without_default_raises():
    # Temporarily set logging.level to None via runtime override
    update_config({"logging": {"level": None}})
    with pytest.raises(ValidationError):
        get_typed_config("logging.level", str)


def test_cfg_or_param_prioritizes_param():
    # When param provided, return it
    assert cfg_or_param("logging.level", "DEBUG") == "DEBUG"
    # When param is None, fallback to config
    assert cfg_or_param("logging.level", None) == "WARNING"


@pytest.mark.parametrize(
    "input_str, expected",
    [
        ("true", True),
        ("False", False),
        ("42", 42),
        ("-7", -7),
        ("3.14", 3.14),
        ("1e-3", 1e-3),
        ("foo", "foo"),
    ],
)
def test_parse_env_value_various(input_str, expected):
    result = parse_env_value(input_str)
    assert result == expected
