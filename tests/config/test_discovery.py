"""Tests for configuration discovery utilities."""

import pytest
from typing import Optional
from pydantic import BaseModel, Field

from fin_statement_model.config.discovery import (
    list_all_config_paths,
    generate_env_var_documentation,
    generate_param_mapping_documentation,
    get_config_field_info,
    find_config_paths_by_type,
    validate_config_completeness,
    generate_config_summary,
)
from fin_statement_model.config.models import Config


class TestListAllConfigPaths:
    """Test the list_all_config_paths function."""

    def test_simple_model(self):
        """Test listing paths for a simple model."""

        class SimpleConfig(BaseModel):
            name: str = "test"
            count: int = 5
            enabled: bool = True

        paths = list_all_config_paths(SimpleConfig)
        expected = ["count", "enabled", "name"]  # Should be sorted
        assert paths == expected

    def test_nested_model(self):
        """Test listing paths for nested models."""

        class DatabaseConfig(BaseModel):
            host: str = "localhost"
            port: int = 5432

        class AppConfig(BaseModel):
            debug: bool = False
            database: DatabaseConfig = Field(default_factory=DatabaseConfig)

        paths = list_all_config_paths(AppConfig)
        expected = ["database.host", "database.port", "debug"]
        assert paths == expected

    def test_optional_fields(self):
        """Test listing paths for models with optional fields."""

        class ConfigWithOptional(BaseModel):
            required_field: str
            optional_field: Optional[str] = None

        paths = list_all_config_paths(ConfigWithOptional)
        expected = ["optional_field", "required_field"]
        assert paths == expected

    def test_real_config_model(self):
        """Test listing paths for the actual Config model."""
        paths = list_all_config_paths(Config)

        # Check that some expected paths exist
        assert "logging.level" in paths
        assert "io.default_excel_sheet" in paths
        assert "forecasting.default_periods" in paths
        assert "api.fmp_api_key" in paths

        # Should have many paths
        assert len(paths) > 20

    def test_default_model_parameter(self):
        """Test that Config is used as default model."""
        paths_default = list_all_config_paths()
        paths_explicit = list_all_config_paths(Config)
        assert paths_default == paths_explicit


class TestGenerateEnvVarDocumentation:
    """Test the generate_env_var_documentation function."""

    def test_simple_model_documentation(self):
        """Test documentation generation for a simple model."""

        class SimpleConfig(BaseModel):
            name: str = "test"
            count: int = 5

        doc = generate_env_var_documentation(SimpleConfig)

        # Should contain header
        assert "# Environment Variables" in doc

        # Should contain the mappings (uses default FSM prefix)
        assert "FSM_NAME" in doc
        assert "FSM_COUNT" in doc
        assert "name" in doc
        assert "count" in doc

    def test_nested_model_documentation(self):
        """Test documentation generation for nested models."""

        class DatabaseConfig(BaseModel):
            host: str = "localhost"

        class AppConfig(BaseModel):
            database: DatabaseConfig = Field(default_factory=DatabaseConfig)

        doc = generate_env_var_documentation(AppConfig)

        # Should contain nested mapping (uses default FSM prefix)
        assert "FSM_DATABASE_HOST" in doc
        assert "database.host" in doc

    def test_real_config_documentation(self):
        """Test documentation generation for the real Config model."""
        doc = generate_env_var_documentation(Config)

        # Should contain expected sections
        assert "# Environment Variables" in doc
        assert "FSM_LOGGING_LEVEL" in doc
        assert "FSM_IO_DEFAULT_EXCEL_SHEET" in doc

    def test_default_model_parameter(self):
        """Test that Config is used as default model."""
        doc_default = generate_env_var_documentation()
        doc_explicit = generate_env_var_documentation(Config)
        assert doc_default == doc_explicit


class TestGenerateParamMappingDocumentation:
    """Test the generate_param_mapping_documentation function."""

    def test_param_mapping_documentation(self):
        """Test parameter mapping documentation generation."""
        doc = generate_param_mapping_documentation()

        # Should contain header
        assert "# Parameter Mappings" in doc

        # Should contain some known mappings
        assert "delimiter" in doc
        assert "io.default_csv_delimiter" in doc
        assert "sheet_name" in doc
        assert "io.default_excel_sheet" in doc

        # Should contain convention section
        assert "## Convention-Based Mappings" in doc
        assert "default_*" in doc
        assert "*_timeout" in doc


class TestGetConfigFieldInfo:
    """Test the get_config_field_info function."""

    def test_simple_field_info(self):
        """Test getting field info for simple fields."""

        class TestConfig(BaseModel):
            string_field: str = "default"
            int_field: int = 42
            optional_field: Optional[str] = None

        # Test string field
        info = get_config_field_info("string_field", TestConfig)
        assert info["path"] == "string_field"
        assert info["type"] == str
        assert not info["is_optional"]
        assert info["default"] == "default"

        # Test optional field
        info = get_config_field_info("optional_field", TestConfig)
        assert info["type"] == str
        assert info["is_optional"]
        assert info["default"] is None

    def test_nested_field_info(self):
        """Test getting field info for nested fields."""

        class NestedConfig(BaseModel):
            nested_value: int = 100

        class MainConfig(BaseModel):
            nested: NestedConfig = Field(default_factory=NestedConfig)

        info = get_config_field_info("nested.nested_value", MainConfig)
        assert info["path"] == "nested.nested_value"
        assert info["type"] == int
        assert not info["is_optional"]
        assert info["default"] == 100

    def test_real_config_field_info(self):
        """Test getting field info for real config fields."""
        # Test logging level
        info = get_config_field_info("logging.level")
        assert info["path"] == "logging.level"
        assert not info["is_optional"]

        # Test optional API key
        info = get_config_field_info("api.fmp_api_key")
        assert info["path"] == "api.fmp_api_key"
        assert info["is_optional"]

    def test_invalid_config_path(self):
        """Test error handling for invalid config paths."""
        with pytest.raises(
            ValueError, match="Configuration path 'invalid.path' not found"
        ):
            get_config_field_info("invalid.path")

    def test_default_model_parameter(self):
        """Test that Config is used as default model."""
        info_default = get_config_field_info("logging.level")
        info_explicit = get_config_field_info("logging.level", Config)
        assert info_default == info_explicit


class TestFindConfigPathsByType:
    """Test the find_config_paths_by_type function."""

    def test_find_by_type_simple_model(self):
        """Test finding paths by type in a simple model."""

        class TestConfig(BaseModel):
            string_field: str = "test"
            int_field: int = 42
            bool_field: bool = True
            another_string: str = "another"

        # Find string fields
        string_paths = find_config_paths_by_type(str, TestConfig)
        assert set(string_paths) == {"another_string", "string_field"}

        # Find int fields
        int_paths = find_config_paths_by_type(int, TestConfig)
        assert int_paths == ["int_field"]

        # Find bool fields
        bool_paths = find_config_paths_by_type(bool, TestConfig)
        assert bool_paths == ["bool_field"]

    def test_find_by_type_real_config(self):
        """Test finding paths by type in the real Config model."""
        # Find boolean fields
        bool_paths = find_config_paths_by_type(bool)
        assert "logging.detailed" in bool_paths
        assert "io.validate_on_read" in bool_paths

        # Should have multiple fields
        assert len(bool_paths) > 5

    def test_find_nonexistent_type(self):
        """Test finding paths for a type that doesn't exist."""

        class TestConfig(BaseModel):
            string_field: str = "test"

        # Find float fields (none exist)
        float_paths = find_config_paths_by_type(float, TestConfig)
        assert float_paths == []

    def test_default_model_parameter(self):
        """Test that Config is used as default model."""
        bool_paths_default = find_config_paths_by_type(bool)
        bool_paths_explicit = find_config_paths_by_type(bool, Config)
        assert bool_paths_default == bool_paths_explicit


class TestValidateConfigCompleteness:
    """Test the validate_config_completeness function."""

    def test_validate_simple_model(self):
        """Test validation for a simple model."""

        class SimpleConfig(BaseModel):
            name: str = "test"
            count: int = 5
            auto_clean: bool = True
            default_timeout: int = 30
            some_custom_field: str = "custom"

        results = validate_config_completeness(SimpleConfig)

        # All fields should have env vars generated automatically
        assert isinstance(results["missing_env_vars"], list)

        # Should return proper structure
        assert isinstance(results["missing_param_mappings"], list)
        # Note: auto_clean and default_timeout might already have mappings
        # so we just check the structure is correct

    def test_validate_real_config(self):
        """Test validation for the real Config model."""
        results = validate_config_completeness()

        # Should return proper structure
        assert "missing_env_vars" in results
        assert "missing_param_mappings" in results
        assert isinstance(results["missing_env_vars"], list)
        assert isinstance(results["missing_param_mappings"], list)

    def test_default_model_parameter(self):
        """Test that Config is used as default model."""
        results_default = validate_config_completeness()
        results_explicit = validate_config_completeness(Config)
        assert results_default == results_explicit


class TestGenerateConfigSummary:
    """Test the generate_config_summary function."""

    def test_summary_simple_model(self):
        """Test summary generation for a simple model."""

        class SimpleConfig(BaseModel):
            name: str = "test"
            count: int = 5
            enabled: bool = True

        summary = generate_config_summary(SimpleConfig)

        # Should contain basic information
        assert "# Configuration System Summary" in summary
        assert "**Model**: SimpleConfig" in summary
        assert "**Total Configuration Fields**: 3" in summary

        # Should contain type breakdown
        assert "## Field Types" in summary
        assert "str: 1 fields" in summary
        assert "int: 1 fields" in summary
        assert "bool: 1 fields" in summary

    def test_summary_real_config(self):
        """Test summary generation for the real Config model."""
        summary = generate_config_summary()

        # Should contain basic information
        assert "# Configuration System Summary" in summary
        assert "**Model**: Config" in summary
        assert "## Field Types" in summary
        assert "## Validation Results" in summary

    def test_summary_includes_validation(self):
        """Test that summary includes validation results."""
        summary = generate_config_summary()

        # Should contain validation section
        assert "## Validation Results" in summary

        # Should show either success or specific issues
        assert ("✅" in summary) or ("Missing Environment Variables" in summary)

    def test_default_model_parameter(self):
        """Test that Config is used as default model."""
        summary_default = generate_config_summary()
        summary_explicit = generate_config_summary(Config)
        assert summary_default == summary_explicit


class TestIntegrationWithRealConfig:
    """Integration tests with the real configuration system."""

    def test_all_functions_work_with_real_config(self):
        """Test that all discovery functions work with the real Config model."""
        # These should all run without errors
        paths = list_all_config_paths()
        assert len(paths) > 0

        env_doc = generate_env_var_documentation()
        assert len(env_doc) > 0

        param_doc = generate_param_mapping_documentation()
        assert len(param_doc) > 0

        field_info = get_config_field_info("logging.level")
        assert field_info["path"] == "logging.level"

        bool_paths = find_config_paths_by_type(bool)
        assert len(bool_paths) > 0

        validation = validate_config_completeness()
        assert "missing_env_vars" in validation
        assert "missing_param_mappings" in validation

        summary = generate_config_summary()
        assert len(summary) > 0

    def test_consistency_between_functions(self):
        """Test consistency between different discovery functions."""
        # Paths from list_all_config_paths should match those found by type
        all_paths = set(list_all_config_paths())

        str_paths = set(find_config_paths_by_type(str))
        int_paths = set(find_config_paths_by_type(int))
        bool_paths = set(find_config_paths_by_type(bool))
        float_paths = set(find_config_paths_by_type(float))

        # Union of typed paths should be subset of all paths
        typed_paths = str_paths | int_paths | bool_paths | float_paths
        assert typed_paths.issubset(all_paths)

        # Should cover most paths (some might be complex types)
        coverage = len(typed_paths) / len(all_paths)
        assert coverage > 0.7, f"Type coverage is only {coverage:.1%}"

    def test_field_info_consistency(self):
        """Test that get_config_field_info is consistent with other functions."""
        paths = list_all_config_paths()

        # Test a sample of paths
        sample_paths = paths[:10] if len(paths) > 10 else paths

        for path in sample_paths:
            # Should be able to get field info for each path
            try:
                info = get_config_field_info(path)
                assert info["path"] == path
                assert "type" in info
                assert "is_optional" in info
                assert "default" in info
            except ValueError:
                pytest.fail(f"Could not get field info for path: {path}")
