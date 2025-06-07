"""Tests for configuration utility functions."""

import pytest
from fin_statement_model.config import (
    cfg,
    cfg_or_param,
    get_typed_config,
    list_config_paths,
    ConfigurationAccessError,
    update_config,
    reset_config,
    # Convenience functions
    default_csv_delimiter,
    default_excel_sheet,
    default_periods,
    default_growth_rate,
    api_timeout,
    api_retry_count,
)


class TestCfgFunction:
    """Test the cfg() function."""

    def setup_method(self):
        """Reset config before each test."""
        reset_config()

    def teardown_method(self):
        """Reset config after each test."""
        reset_config()

    def test_cfg_with_valid_string_path(self):
        """Test cfg with a valid dotted string path."""
        assert cfg("io.default_excel_sheet") == "Sheet1"
        assert cfg("forecasting.default_periods") == 5
        assert cfg("display.scale_factor") == 1.0

    def test_cfg_with_valid_sequence_path(self):
        """Test cfg with a sequence path."""
        assert cfg(["io", "default_excel_sheet"]) == "Sheet1"
        assert cfg(["forecasting", "default_periods"]) == 5
        assert cfg(["display", "scale_factor"]) == 1.0

    def test_cfg_with_default_value(self):
        """Test cfg returns default when path doesn't exist."""
        assert cfg("invalid.path", "default_value") == "default_value"
        assert cfg(["invalid", "path"], 42) == 42

    def test_cfg_raises_on_invalid_path_without_default(self):
        """Test cfg raises ConfigurationAccessError for invalid path."""
        with pytest.raises(ConfigurationAccessError) as exc_info:
            cfg("invalid.path")
        assert "does not exist" in str(exc_info.value)

    def test_cfg_with_empty_path(self):
        """Test cfg raises on empty path."""
        with pytest.raises(ConfigurationAccessError) as exc_info:
            cfg("")
        assert "cannot be empty" in str(exc_info.value)

        with pytest.raises(ConfigurationAccessError) as exc_info:
            cfg([])
        assert "cannot be empty" in str(exc_info.value)

    def test_cfg_with_updated_config(self):
        """Test cfg returns updated values after config update."""
        # Check initial value
        assert cfg("forecasting.default_periods") == 5

        # Update config
        update_config({"forecasting": {"default_periods": 10}})

        # Check updated value
        assert cfg("forecasting.default_periods") == 10

    def test_cfg_with_none_values(self):
        """Test cfg handles None configuration values correctly."""
        # API key is None by default
        assert cfg("api.fmp_api_key") is None
        assert cfg("api.fmp_api_key", "default_key") == "default_key"


class TestGetTypedConfig:
    """Test the get_typed_config() function."""

    def test_get_typed_config_with_correct_type(self):
        """Test get_typed_config returns value with correct type."""
        assert get_typed_config("forecasting.default_periods", int) == 5
        assert get_typed_config("display.scale_factor", float) == 1.0
        assert get_typed_config("io.default_excel_sheet", str) == "Sheet1"
        assert get_typed_config("io.validate_on_read", bool) is True

    def test_get_typed_config_with_wrong_type(self):
        """Test get_typed_config raises TypeError for wrong type."""
        with pytest.raises(TypeError) as exc_info:
            get_typed_config("forecasting.default_periods", str)
        assert "expected str" in str(exc_info.value)

    def test_get_typed_config_with_default(self):
        """Test get_typed_config with default value."""
        assert get_typed_config("invalid.path", int, 42) == 42

    def test_get_typed_config_none_without_default(self):
        """Test get_typed_config raises for None value without default."""
        with pytest.raises(ConfigurationAccessError):
            get_typed_config("api.fmp_api_key", str)


class TestCfgOrParam:
    """Test the cfg_or_param() function."""

    def test_cfg_or_param_with_provided_value(self):
        """Test cfg_or_param returns parameter when provided."""
        assert cfg_or_param("io.default_csv_delimiter", ";") == ";"
        assert cfg_or_param("forecasting.default_periods", 10) == 10

    def test_cfg_or_param_with_none_value(self):
        """Test cfg_or_param returns config value when param is None."""
        assert cfg_or_param("io.default_csv_delimiter", None) == ","
        assert cfg_or_param("forecasting.default_periods", None) == 5

    def test_cfg_or_param_with_false_value(self):
        """Test cfg_or_param handles falsy values correctly."""
        # Should return False, not config value
        assert cfg_or_param("io.validate_on_read", False) is False
        # Should return 0, not config value
        assert cfg_or_param("forecasting.default_periods", 0) == 0
        # Should return empty string, not config value
        assert cfg_or_param("io.default_csv_delimiter", "") == ""


class TestListConfigPaths:
    """Test the list_config_paths() function."""

    def test_list_all_paths(self):
        """Test listing all configuration paths."""
        paths = list_config_paths()

        # Check some expected paths exist
        assert "io.default_excel_sheet" in paths
        assert "forecasting.default_periods" in paths
        assert "display.scale_factor" in paths
        assert "api.api_timeout" in paths

        # Check it's sorted
        assert paths == sorted(paths)

    def test_list_paths_with_prefix(self):
        """Test listing paths with a prefix."""
        io_paths = list_config_paths("io")

        # All paths should start with "io"
        assert all(p.startswith("io.") for p in io_paths)

        # Check expected IO paths
        assert "io.default_excel_sheet" in io_paths
        assert "io.default_csv_delimiter" in io_paths

        # Non-IO paths shouldn't be included
        assert "forecasting.default_periods" not in io_paths

    def test_list_paths_with_nested_prefix(self):
        """Test listing paths with nested prefix."""
        forecast_paths = list_config_paths("forecasting")

        assert all(p.startswith("forecasting.") for p in forecast_paths)
        assert len(forecast_paths) > 0


class TestConvenienceFunctions:
    """Test the convenience config access functions."""

    def setup_method(self):
        """Reset config before each test."""
        reset_config()

    def teardown_method(self):
        """Reset config after each test."""
        reset_config()

    def test_default_csv_delimiter(self):
        """Test default_csv_delimiter function."""
        assert default_csv_delimiter() == ","

        # Update config and check
        update_config({"io": {"default_csv_delimiter": ";"}})
        assert default_csv_delimiter() == ";"

    def test_default_excel_sheet(self):
        """Test default_excel_sheet function."""
        assert default_excel_sheet() == "Sheet1"

        # Update config and check
        update_config({"io": {"default_excel_sheet": "Data"}})
        assert default_excel_sheet() == "Data"

    def test_default_periods(self):
        """Test default_periods function."""
        assert default_periods() == 5
        assert isinstance(default_periods(), int)

        # Update config and check
        update_config({"forecasting": {"default_periods": 10}})
        assert default_periods() == 10

    def test_default_growth_rate(self):
        """Test default_growth_rate function."""
        assert default_growth_rate() == 0.0
        assert isinstance(default_growth_rate(), float)

        # Update config and check
        update_config({"forecasting": {"default_growth_rate": 0.05}})
        assert default_growth_rate() == 0.05

    def test_api_timeout(self):
        """Test api_timeout function."""
        assert api_timeout() == 30
        assert isinstance(api_timeout(), int)

        # Update config and check
        update_config({"api": {"api_timeout": 60}})
        assert api_timeout() == 60

    def test_api_retry_count(self):
        """Test api_retry_count function."""
        assert api_retry_count() == 3
        assert isinstance(api_retry_count(), int)

        # Update config and check
        update_config({"api": {"api_retry_count": 5}})
        assert api_retry_count() == 5
