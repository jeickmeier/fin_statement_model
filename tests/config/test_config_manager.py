"""Tests for the configuration management system."""

import os
import pytest
from pathlib import Path
import tempfile
import yaml

from fin_statement_model.config import (
    get_config,
    update_config,
    reset_config,
    Config,
    ConfigManager,
)


class TestConfigManager:
    """Test configuration manager functionality."""

    def test_default_config(self):
        """Test that default configuration loads correctly."""
        reset_config()
        config = get_config()

        # Check some defaults
        assert config.logging.level == "WARNING"
        assert config.forecasting.default_method == "simple"
        assert config.display.scale_factor == 1.0
        assert config.io.default_excel_sheet == "Sheet1"

    def test_runtime_updates(self):
        """Test runtime configuration updates."""
        reset_config()

        # Update configuration
        update_config({"logging": {"level": "DEBUG"}, "forecasting": {"default_periods": 10}})

        config = get_config()
        assert config.logging.level == "DEBUG"
        assert config.forecasting.default_periods == 10

    def test_reset_config(self):
        """Test configuration reset."""
        # Make changes
        update_config({"logging": {"level": "ERROR"}})
        assert get_config().logging.level == "ERROR"

        # Reset
        reset_config()
        assert get_config().logging.level == "WARNING"

    def test_environment_variables(self):
        """Test loading configuration from environment variables."""
        reset_config()

        # Set environment variables
        os.environ["FSM_LOGGING_LEVEL"] = "INFO"
        os.environ["FSM_FORECASTING_DEFAULT_PERIODS"] = "7"
        os.environ["FSM_API_FMP_API_KEY"] = "test_key_123"
        os.environ["FSM_DISPLAY_HIDE_ZERO_ROWS"] = "true"

        try:
            # Force reload
            manager = ConfigManager()
            config = manager.get()

            assert config.logging.level == "INFO"
            assert config.forecasting.default_periods == 7
            assert config.api.fmp_api_key == "test_key_123"
            assert config.display.hide_zero_rows is True

        finally:
            # Clean up
            for key in [
                "FSM_LOGGING_LEVEL",
                "FSM_FORECASTING_DEFAULT_PERIODS",
                "FSM_API_FMP_API_KEY",
                "FSM_DISPLAY_HIDE_ZERO_ROWS",
            ]:
                os.environ.pop(key, None)

    def test_config_file_loading(self):
        """Test loading configuration from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.yaml"

            # Write test configuration
            test_config = {
                "logging": {"level": "DEBUG"},
                "display": {"scale_factor": 0.001, "default_units": "USD Thousands"},
                "validation": {"strict_mode": True},
            }

            with open(config_path, "w") as f:
                yaml.dump(test_config, f)

            # Load configuration
            manager = ConfigManager(config_file=config_path)
            config = manager.get()

            assert config.logging.level == "DEBUG"
            assert config.display.scale_factor == 0.001
            assert config.display.default_units == "USD Thousands"
            assert config.validation.strict_mode is True

    def test_config_precedence(self):
        """Test configuration precedence order."""
        reset_config()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config file
            config_path = Path(tmpdir) / "test_config.yaml"
            with open(config_path, "w") as f:
                yaml.dump({"logging": {"level": "INFO"}}, f)

            # Set environment variable (higher precedence)
            os.environ["FSM_LOGGING_LEVEL"] = "DEBUG"

            try:
                manager = ConfigManager(config_file=config_path)

                # Runtime update (highest precedence)
                manager.update({"logging": {"level": "ERROR"}})

                config = manager.get()
                assert config.logging.level == "ERROR"

            finally:
                os.environ.pop("FSM_LOGGING_LEVEL", None)

    def test_config_validation(self):
        """Test configuration validation."""
        # Test invalid scale factor
        with pytest.raises(Exception):
            Config(display={"scale_factor": -1.0})

        # Test invalid periods
        with pytest.raises(Exception):
            Config(forecasting={"default_periods": 0})

    def test_config_serialization(self):
        """Test configuration serialization."""
        config = Config()

        # Test to_dict
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert "logging" in config_dict
        assert "forecasting" in config_dict

        # Test to_yaml
        yaml_str = config.to_yaml()
        assert isinstance(yaml_str, str)
        assert "logging:" in yaml_str

        # Test from_yaml
        config2 = Config.from_yaml(yaml_str)
        assert config2.logging.level == config.logging.level

    def test_nested_updates(self):
        """Test deep merging of configuration updates."""
        reset_config()

        # First update
        update_config({"display": {"scale_factor": 0.001, "default_units": "Thousands"}})

        # Second update (should merge, not replace)
        update_config({"display": {"hide_zero_rows": True}})

        config = get_config()
        assert config.display.scale_factor == 0.001
        assert config.display.default_units == "Thousands"
        assert config.display.hide_zero_rows is True
