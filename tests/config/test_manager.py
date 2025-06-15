import json
import os

import pytest
import yaml

import fin_statement_model.config.manager as cm_module
from fin_statement_model.config.manager import ConfigManager, ConfigurationError
from fin_statement_model.utils.dicts import deep_merge


@pytest.fixture(autouse=True)
def isolate_env_and_cwd(monkeypatch, tmp_path):
    # Change working directory to a clean temp path
    monkeypatch.chdir(tmp_path)
    # Reset global config manager
    monkeypatch.setattr(cm_module, "_config_manager", ConfigManager())
    # Clear FSM_ env vars and FMP_API_KEY
    for key in list(os.environ.keys()):
        if key.startswith("FSM_") or key == "FMP_API_KEY":
            monkeypatch.delenv(key, raising=False)
    yield


def test_load_yaml_file(tmp_path):
    # Create a simple YAML config file
    content = {"logging": {"level": "ERROR"}}
    file_path = tmp_path / "config.yaml"
    file_path.write_text(yaml.dump(content))
    cm = ConfigManager()
    data = cm._load_file(file_path)
    assert data == content


def test_load_json_file(tmp_path):
    content = {"api": {"api_timeout": 60}}
    file_path = tmp_path / "config.json"
    file_path.write_text(json.dumps(content))
    cm = ConfigManager()
    data = cm._load_file(file_path)
    assert data == content


def test_load_file_unsupported(tmp_path):
    file_path = tmp_path / "config.txt"
    file_path.write_text("unsupported")
    cm = ConfigManager()
    with pytest.raises(ConfigurationError):
        cm._load_file(file_path)


def test_deep_merge():
    base = {"a": {"b": 1, "c": 2}, "d": 3}
    update = {"a": {"b": 10}, "e": 4}
    result = deep_merge(base, update)
    assert result["a"]["b"] == 10
    assert result["a"]["c"] == 2
    assert result["d"] == 3
    assert result["e"] == 4


def test_update_and_get_config():
    cm = ConfigManager()
    cfg1 = cm.get()
    # Default api_timeout is from APIConfig default
    assert cfg1.api.api_timeout == 30
    # Apply runtime override
    cm.update({"api": {"api_timeout": 15}})
    cfg2 = cm.get()
    assert cfg2.api.api_timeout == 15


def test_user_config_file_override(tmp_path):
    # Create a user config file with an override for validation.strict_mode
    content = {"validation": {"strict_mode": True}}
    file_path = tmp_path / "fsm_config.yaml"
    file_path.write_text(yaml.dump(content))
    # Initialize manager pointing to this file
    cm = ConfigManager(config_file=file_path)
    cfg = cm.get()
    assert cfg.validation.strict_mode is True


def test_env_file_mapping_of_fmp_key(tmp_path):
    # Write .env file with FMP_API_KEY
    env_file = tmp_path / ".env"
    env_file.write_text("FMP_API_KEY=secret_key\nOTHER=1")
    cm = ConfigManager()
    cm._load_dotenv()
    # Ensure mapping to namespaced key occurred
    assert os.environ.get("FMP_API_KEY") == "secret_key"
    assert os.environ.get("FSM_API_FMP_API_KEY") == "secret_key"
