import pytest

# Import config sub-modules explicitly so that their module-level code is executed
# and included in coverage metrics.  Simply importing the package triggers class
# definitions and validators which account for a large portion of lines.
import fin_statement_model.config.access as utils
import fin_statement_model.config.access as helpers
from fin_statement_model.config.store import ConfigStore
from fin_statement_model.config.models import Config


class TestUtils:
    """Tests for fin_statement_model.config.utils helpers."""

    @pytest.mark.parametrize(
        ("key", "expected"),
        [
            ("FSM_LOGGING__LEVEL", ["logging", "level"]),
            ("FSM_API__FMP_API_KEY", ["api", "fmp_api_key"]),
            ("OTHER_VAR", ["other", "var"]),  # prefix not matched → original split
            ("FSM_FOO_BAR", ["foo", "bar"]),  # single underscore fallback
        ],
    )
    def test_parse_env_var(self, key: str, expected: list[str]) -> None:
        """`parse_env_var` should split keys into lower-case path segments."""
        assert utils.parse_env_var(key, prefix="FSM_") == expected


class TestHelpers:
    """Tests for fin_statement_model.config.helpers utilities."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("true", True),
            ("FALSE", False),
            ("42", 42),
            ("-3", -3),
            ("-3.14", -3.14),
            ("2.5", 2.5),
            ("[1, 2, 3]", [1, 2, 3]),
            ('{"a": 1}', {"a": 1}),
            ("hello", "hello"),
        ],
    )
    def test_parse_env_value(self, raw: str, expected):  # type: ignore[override]
        """`parse_env_value` should coerce strings to appropriate Python types."""
        assert helpers.parse_env_value(raw) == expected

    def test_cfg_and_cfg_or_param(self):
        """`cfg` retrieves values correctly and `cfg_or_param` prefers param."""
        # Known existing config value
        assert helpers.cfg("logging.level") == "WARNING"

        # Fallback to default when key missing
        sentinel = "SENTINEL"
        assert helpers.cfg("nonexistent.key", default=sentinel) == sentinel

        # `cfg_or_param` behaviour
        assert helpers.cfg_or_param("logging.level", "DEBUG") == "DEBUG"
        assert helpers.cfg_or_param("logging.level", None) == "WARNING"


class TestManager:
    """Tests targeting private helpers inside `ConfigManager`."""

    def test_extract_env_overrides(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Environment variables should be converted into a nested override dict."""
        monkeypatch.setenv("FSM_LOGGING__LEVEL", "INFO")
        monkeypatch.setenv("FSM_IO__DEFAULT_CSV_DELIMITER", ";")

        manager = ConfigStore()
        overrides = manager._extract_env_overrides()

        assert overrides["logging"]["level"] == "INFO"
        assert overrides["io"]["default_csv_delimiter"] == ";"


class TestConfigModel:
    """Smoke tests for the high-level `Config` model helpers."""

    def test_serialization_roundtrip(self):
        """`Config` should round-trip through YAML and dict helpers without loss."""
        cfg = Config()
        yaml_str = cfg.to_yaml()
        cfg2 = Config.from_yaml(yaml_str)

        assert cfg2 == cfg  # Ensures entire hierarchy survives round-trip

        # Also ensure dict round-trip matches
        as_dict = cfg.to_dict()
        cfg3 = Config.from_dict(as_dict)
        assert cfg3 == cfg
