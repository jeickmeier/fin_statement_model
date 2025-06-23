from __future__ import annotations

"""High-level tests for fin_statement_model.config.manager.ConfigManager.

The aim is to exercise the majority of code paths - YAML/JSON loading, environment
variable extraction, runtime overrides, and persistence - so that statement
coverage of *config/manager.py* exceeds 80 %.
"""

from pathlib import Path
import yaml
import pytest

from fin_statement_model.config.store import (
    ConfigStore as ConfigManager,  # alias for test compatibility
    ConfigurationError,
)

# -----------------------------------------------------------------------------
# _load_file - YAML / JSON / unsupported extension
# -----------------------------------------------------------------------------


def test_load_file_yaml_json_and_unsupported(tmp_path: Path) -> None:
    cm = ConfigManager()

    # YAML
    yaml_path = tmp_path / "cfg.yaml"
    yaml_path.write_text("logging:\n  level: DEBUG\n", encoding="utf-8")
    loaded_yaml = cm._load_file(yaml_path)
    assert loaded_yaml["logging"]["level"] == "DEBUG"

    # JSON
    json_path = tmp_path / "cfg.json"
    json_path.write_text('{"logging": {"level": "INFO"}}', encoding="utf-8")
    loaded_json = cm._load_file(json_path)
    assert loaded_json["logging"]["level"] == "INFO"

    # Unsupported extension should raise
    txt_path = tmp_path / "cfg.txt"
    txt_path.write_text("irrelevant", encoding="utf-8")
    with pytest.raises(ConfigurationError):
        cm._load_file(txt_path)


# -----------------------------------------------------------------------------
# Environment variable overrides
# -----------------------------------------------------------------------------


def test_environment_overrides(monkeypatch):
    # Prepare env var using double-underscore path segmentation
    monkeypatch.setenv("FSM_LOGGING__LEVEL", "ERROR")

    cm = ConfigManager()
    cfg = cm.get()  # triggers load and env extraction
    assert cfg.logging.level == "ERROR"

    # Ensure helper returns the parsed structure that contains our override
    overrides = cm._extract_env_overrides()
    assert overrides.get("logging", {}).get("level") == "ERROR"


# -----------------------------------------------------------------------------
# Runtime update merging and deep-merge semantics
# -----------------------------------------------------------------------------


def test_update_runtime_overrides_merges_deeply():
    cm = ConfigManager()

    # Default should be WARNING
    assert cm.get().logging.level == "WARNING"

    cm.update(
        {
            "logging": {"level": "CRITICAL"},
            "display": {"flags": {"include_notes_column": True}},
        }
    )

    cfg = cm.get()
    assert cfg.logging.level == "CRITICAL"
    assert cfg.display.flags.include_notes_column is True


# -----------------------------------------------------------------------------
# save() - ensure persisted YAML contains expected changes
# -----------------------------------------------------------------------------


def test_save_persists_changes(tmp_path: Path):
    target = tmp_path / "saved_cfg.yaml"
    cm = ConfigManager()
    cm.update({"logging": {"level": "INFO"}})

    cm.save(target)

    assert target.exists() and target.stat().st_size > 0
    saved_content = yaml.safe_load(target.read_text())
    assert saved_content["logging"]["level"] == "INFO"

    # Round-trip load via ConfigManager._load_file as additional verification
    round_trip = cm._load_file(target)
    assert round_trip["logging"]["level"] == "INFO"
