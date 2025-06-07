"""Tests for parameter mapping utilities."""

import pytest
from pydantic import BaseModel

from fin_statement_model.config.param_mapping import (
    ParamMapper,
    get_class_param_mappings,
    merge_param_mappings,
)


class TestParamMapper:
    """Test the ParamMapper class."""

    def setup_method(self):
        """Reset ParamMapper to clean state before each test."""
        ParamMapper.clear_custom_mappings()

    def test_get_config_path_explicit_mapping(self):
        """Test getting config path for explicitly mapped parameters."""
        # Test some known mappings
        assert ParamMapper.get_config_path("delimiter") == "io.default_csv_delimiter"
        assert ParamMapper.get_config_path("sheet_name") == "io.default_excel_sheet"
        assert ParamMapper.get_config_path("periods") == "forecasting.default_periods"
        assert ParamMapper.get_config_path("timeout") == "api.api_timeout"

    def test_get_config_path_convention_mapping(self):
        """Test getting config path using convention-based mapping."""
        # Test default_* convention
        path = ParamMapper.get_config_path("default_periods")
        assert path == "forecasting.default_periods"

        path = ParamMapper.get_config_path("default_growth_rate")
        assert path == "forecasting.default_growth_rate"

    def test_get_config_path_format_convention(self):
        """Test getting config path for *_format parameters."""
        # These should map to display section
        path = ParamMapper.get_config_path("number_format")
        assert path == "display.default_number_format"

        path = ParamMapper.get_config_path("currency_format")
        assert path == "display.default_currency_format"

    def test_get_config_path_timeout_convention(self):
        """Test getting config path for *_timeout parameters."""
        # api_timeout should map directly
        path = ParamMapper.get_config_path("api_timeout")
        assert path == "api.api_timeout"

    def test_get_config_path_auto_convention(self):
        """Test getting config path for auto_* parameters."""
        path = ParamMapper.get_config_path("auto_clean_data")
        assert path == "preprocessing.auto_clean_data"

    def test_get_config_path_unknown_parameter(self):
        """Test getting config path for unknown parameters."""
        path = ParamMapper.get_config_path("unknown_parameter")
        assert path is None

    def test_register_mapping(self):
        """Test registering custom parameter mappings."""
        # Register a custom mapping
        ParamMapper.register_mapping("custom_param", "custom.config.path")

        # Should be able to retrieve it
        path = ParamMapper.get_config_path("custom_param")
        assert path == "custom.config.path"

        # Should appear in all mappings
        all_mappings = ParamMapper.get_all_mappings()
        assert "custom_param" in all_mappings
        assert all_mappings["custom_param"] == "custom.config.path"

    def test_register_mapping_override(self):
        """Test that custom mappings can override base mappings."""
        # Override an existing mapping
        original_path = ParamMapper.get_config_path("delimiter")
        assert original_path == "io.default_csv_delimiter"

        ParamMapper.register_mapping("delimiter", "custom.delimiter.path")

        # Should return the custom mapping
        new_path = ParamMapper.get_config_path("delimiter")
        assert new_path == "custom.delimiter.path"

    def test_get_all_mappings(self):
        """Test getting all current mappings."""
        mappings = ParamMapper.get_all_mappings()

        # Should contain known base mappings
        assert "delimiter" in mappings
        assert "sheet_name" in mappings
        assert "periods" in mappings

        # Should be a copy (modifications shouldn't affect original)
        mappings["test"] = "test.path"
        assert "test" not in ParamMapper.get_all_mappings()

    def test_clear_custom_mappings(self):
        """Test clearing custom mappings."""
        # Add a custom mapping
        ParamMapper.register_mapping("custom_param", "custom.path")
        assert ParamMapper.get_config_path("custom_param") == "custom.path"

        # Clear custom mappings
        ParamMapper.clear_custom_mappings()

        # Custom mapping should be gone
        assert ParamMapper.get_config_path("custom_param") is None

        # Base mappings should still exist
        assert ParamMapper.get_config_path("delimiter") == "io.default_csv_delimiter"


class TestConventionMapping:
    """Test convention-based parameter mapping."""

    def setup_method(self):
        """Reset ParamMapper to clean state before each test."""
        ParamMapper.clear_custom_mappings()

    def test_find_config_field(self):
        """Test finding config fields by name."""
        # Test finding a field that exists
        path = ParamMapper._find_config_field(
            ParamMapper._get_config_model(), "default_periods"
        )
        assert path == "forecasting.default_periods"

        # Test finding a field that doesn't exist
        path = ParamMapper._find_config_field(
            ParamMapper._get_config_model(), "nonexistent_field"
        )
        assert path is None

    def test_field_exists(self):
        """Test checking if a field path exists."""
        from fin_statement_model.config.models import Config

        # Test existing path
        assert ParamMapper._field_exists(Config, ["logging", "level"])
        assert ParamMapper._field_exists(Config, ["io", "default_excel_sheet"])

        # Test non-existing path
        assert not ParamMapper._field_exists(Config, ["invalid", "path"])
        assert not ParamMapper._field_exists(Config, ["logging", "invalid_field"])

    def test_search_model_recursive(self):
        """Test recursive model searching."""
        from fin_statement_model.config.models import Config

        # Test finding a top-level field
        path = ParamMapper._search_model_recursive(Config, "project_name", [])
        assert path == "project_name"

        # Test finding a nested field
        path = ParamMapper._search_model_recursive(Config, "level", [])
        assert path == "logging.level"

        # Test finding a deeply nested field
        path = ParamMapper._search_model_recursive(Config, "default_periods", [])
        assert path == "forecasting.default_periods"


class TestClassParamMappings:
    """Test class-level parameter mappings."""

    def test_get_class_param_mappings_with_mappings(self):
        """Test getting mappings from a class that has them."""

        class TestClass:
            _config_mappings = {
                "param1": "config.path1",
                "param2": "config.path2",
            }

        mappings = get_class_param_mappings(TestClass)
        expected = {
            "param1": "config.path1",
            "param2": "config.path2",
        }
        assert mappings == expected

    def test_get_class_param_mappings_without_mappings(self):
        """Test getting mappings from a class that doesn't have them."""

        class TestClass:
            pass

        mappings = get_class_param_mappings(TestClass)
        assert mappings == {}

    def test_get_class_param_mappings_with_none(self):
        """Test getting mappings when _config_mappings is None."""

        class TestClass:
            _config_mappings = None

        mappings = get_class_param_mappings(TestClass)
        assert mappings == {}


class TestMergeParamMappings:
    """Test merging parameter mapping dictionaries."""

    def test_merge_empty_mappings(self):
        """Test merging empty mappings."""
        result = merge_param_mappings()
        assert result == {}

        result = merge_param_mappings({}, {})
        assert result == {}

    def test_merge_single_mapping(self):
        """Test merging a single mapping."""
        mapping = {"param1": "config.path1", "param2": "config.path2"}
        result = merge_param_mappings(mapping)
        assert result == mapping
        assert result is not mapping  # Should be a copy

    def test_merge_multiple_mappings(self):
        """Test merging multiple mappings."""
        mapping1 = {"param1": "config.path1", "param2": "config.path2"}
        mapping2 = {"param3": "config.path3", "param4": "config.path4"}

        result = merge_param_mappings(mapping1, mapping2)
        expected = {
            "param1": "config.path1",
            "param2": "config.path2",
            "param3": "config.path3",
            "param4": "config.path4",
        }
        assert result == expected

    def test_merge_overlapping_mappings(self):
        """Test merging mappings with overlapping keys."""
        mapping1 = {"param1": "config.path1", "param2": "config.path2"}
        mapping2 = {"param2": "config.override", "param3": "config.path3"}

        result = merge_param_mappings(mapping1, mapping2)
        expected = {
            "param1": "config.path1",
            "param2": "config.override",  # Later mapping should override
            "param3": "config.path3",
        }
        assert result == expected

    def test_merge_preserves_original_mappings(self):
        """Test that merging doesn't modify original mappings."""
        mapping1 = {"param1": "config.path1"}
        mapping2 = {"param2": "config.path2"}

        original1 = mapping1.copy()
        original2 = mapping2.copy()

        result = merge_param_mappings(mapping1, mapping2)

        # Original mappings should be unchanged
        assert mapping1 == original1
        assert mapping2 == original2

        # Result should contain both
        assert result == {"param1": "config.path1", "param2": "config.path2"}


class TestIntegrationWithRealConfig:
    """Integration tests with the real configuration system."""

    def setup_method(self):
        """Reset ParamMapper to clean state before each test."""
        ParamMapper.clear_custom_mappings()

    def test_common_parameters_have_mappings(self):
        """Test that common parameter names have mappings."""
        common_params = [
            "delimiter",
            "sheet_name",
            "periods",
            "growth_rate",
            "timeout",
            "validate_on_read",
            "scale_factor",
        ]

        for param in common_params:
            path = ParamMapper.get_config_path(param)
            assert path is not None, f"Parameter '{param}' should have a mapping"

    def test_convention_based_mappings_work(self):
        """Test that convention-based mappings work for real config fields."""
        # Test default_* parameters
        convention_params = [
            ("default_periods", "forecasting.default_periods"),
            ("default_growth_rate", "forecasting.default_growth_rate"),
            ("default_number_format", "display.default_number_format"),
        ]

        for param, expected_path in convention_params:
            actual_path = ParamMapper.get_config_path(param)
            assert (
                actual_path == expected_path
            ), f"Parameter '{param}' should map to '{expected_path}'"

    def test_all_base_mappings_are_valid(self):
        """Test that all base parameter mappings point to valid config paths."""
        from fin_statement_model.config.introspection import _validate_config_path
        from fin_statement_model.config.models import Config

        mappings = ParamMapper.get_all_mappings()

        for param_name, config_path in mappings.items():
            path_parts = config_path.split(".")
            try:
                _validate_config_path(Config, path_parts)
            except ValueError as e:
                pytest.fail(
                    f"Parameter '{param_name}' maps to invalid config path '{config_path}': {e}"
                )


# Helper method for ParamMapper (needed for some tests)
def _get_config_model():
    """Get the Config model for testing."""
    from fin_statement_model.config.models import Config

    return Config


# Monkey patch for testing
ParamMapper._get_config_model = staticmethod(_get_config_model)
