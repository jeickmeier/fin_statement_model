"""Tests for configuration introspection utilities."""

import pytest
from typing import Optional
from pydantic import BaseModel, Field

from fin_statement_model.config.introspection import (
    generate_env_mappings,
    validate_env_mappings,
    get_field_type_info,
    _validate_config_path,
)
from fin_statement_model.config.models import Config


class TestGenerateEnvMappings:
    """Test the generate_env_mappings function."""

    def test_simple_model(self):
        """Test env mapping generation for a simple model."""

        class SimpleConfig(BaseModel):
            name: str = "test"
            count: int = 5
            enabled: bool = True

        mappings = generate_env_mappings(SimpleConfig, "TEST")

        expected = {
            "TEST_NAME": ["name"],
            "TEST_COUNT": ["count"],
            "TEST_ENABLED": ["enabled"],
        }

        assert mappings == expected

    def test_nested_model(self):
        """Test env mapping generation for nested models."""

        class DatabaseConfig(BaseModel):
            host: str = "localhost"
            port: int = 5432

        class AppConfig(BaseModel):
            debug: bool = False
            database: DatabaseConfig = Field(default_factory=DatabaseConfig)

        mappings = generate_env_mappings(AppConfig, "APP")

        expected = {
            "APP_DEBUG": ["debug"],
            "APP_DATABASE_HOST": ["database", "host"],
            "APP_DATABASE_PORT": ["database", "port"],
        }

        assert mappings == expected

    def test_optional_fields(self):
        """Test env mapping generation for optional fields."""

        class ConfigWithOptional(BaseModel):
            required_field: str
            optional_field: Optional[str] = None
            optional_int: Optional[int] = None

        mappings = generate_env_mappings(ConfigWithOptional, "OPT")

        expected = {
            "OPT_REQUIRED_FIELD": ["required_field"],
            "OPT_OPTIONAL_FIELD": ["optional_field"],
            "OPT_OPTIONAL_INT": ["optional_int"],
        }

        assert mappings == expected

    def test_real_config_model(self):
        """Test env mapping generation for the actual Config model."""
        mappings = generate_env_mappings(Config, "FSM")

        # Check that some expected mappings exist
        assert "FSM_LOGGING_LEVEL" in mappings
        assert mappings["FSM_LOGGING_LEVEL"] == ["logging", "level"]

        assert "FSM_IO_DEFAULT_EXCEL_SHEET" in mappings
        assert mappings["FSM_IO_DEFAULT_EXCEL_SHEET"] == ["io", "default_excel_sheet"]

        assert "FSM_FORECASTING_DEFAULT_PERIODS" in mappings
        assert mappings["FSM_FORECASTING_DEFAULT_PERIODS"] == [
            "forecasting",
            "default_periods",
        ]

        # Check that we have a reasonable number of mappings
        assert len(mappings) > 20  # Should have many config fields

    def test_custom_prefix(self):
        """Test env mapping generation with custom prefix."""

        class SimpleConfig(BaseModel):
            value: str = "test"

        mappings = generate_env_mappings(SimpleConfig, "CUSTOM")

        expected = {
            "CUSTOM_VALUE": ["value"],
        }

        assert mappings == expected


class TestValidateEnvMappings:
    """Test the validate_env_mappings function."""

    def test_valid_mappings(self):
        """Test validation of valid mappings."""

        class TestConfig(BaseModel):
            field1: str = "test"
            field2: int = 5

        mappings = {
            "TEST_FIELD1": ["field1"],
            "TEST_FIELD2": ["field2"],
        }

        errors = validate_env_mappings(TestConfig, mappings)
        assert errors == []

    def test_invalid_mappings(self):
        """Test validation of invalid mappings."""

        class TestConfig(BaseModel):
            field1: str = "test"

        mappings = {
            "TEST_FIELD1": ["field1"],
            "TEST_INVALID": ["nonexistent_field"],
            "TEST_NESTED_INVALID": ["field1", "nested"],
        }

        errors = validate_env_mappings(TestConfig, mappings)
        assert len(errors) == 2
        assert "TEST_INVALID" in errors[0]
        assert "TEST_NESTED_INVALID" in errors[1]

    def test_nested_model_validation(self):
        """Test validation of nested model mappings."""

        class NestedConfig(BaseModel):
            nested_field: str = "test"

        class MainConfig(BaseModel):
            main_field: str = "main"
            nested: NestedConfig = Field(default_factory=NestedConfig)

        mappings = {
            "TEST_MAIN_FIELD": ["main_field"],
            "TEST_NESTED_NESTED_FIELD": ["nested", "nested_field"],
            "TEST_INVALID_NESTED": ["nested", "invalid_field"],
        }

        errors = validate_env_mappings(MainConfig, mappings)
        assert len(errors) == 1
        assert "TEST_INVALID_NESTED" in errors[0]


class TestGetFieldTypeInfo:
    """Test the get_field_type_info function."""

    def test_simple_field_info(self):
        """Test getting type info for simple fields."""

        class TestConfig(BaseModel):
            string_field: str = "default"
            int_field: int = 42
            bool_field: bool = True
            optional_field: Optional[str] = None

        # Test string field
        info = get_field_type_info(TestConfig, ["string_field"])
        assert info["type"] == str
        assert not info["is_optional"]
        assert info["default"] == "default"

        # Test int field
        info = get_field_type_info(TestConfig, ["int_field"])
        assert info["type"] == int
        assert not info["is_optional"]
        assert info["default"] == 42

        # Test optional field
        info = get_field_type_info(TestConfig, ["optional_field"])
        assert info["type"] == str
        assert info["is_optional"]
        assert info["default"] is None

    def test_nested_field_info(self):
        """Test getting type info for nested fields."""

        class NestedConfig(BaseModel):
            nested_value: int = 100

        class MainConfig(BaseModel):
            nested: NestedConfig = Field(default_factory=NestedConfig)

        info = get_field_type_info(MainConfig, ["nested", "nested_value"])
        assert info["type"] == int
        assert not info["is_optional"]
        assert info["default"] == 100

    def test_invalid_path(self):
        """Test error handling for invalid paths."""

        class TestConfig(BaseModel):
            field: str = "test"

        with pytest.raises(ValueError, match="Field 'invalid' not found"):
            get_field_type_info(TestConfig, ["invalid"])

        with pytest.raises(ValueError, match="Field 'field' is not a nested model"):
            get_field_type_info(TestConfig, ["field", "nested"])


class TestValidateConfigPath:
    """Test the _validate_config_path function."""

    def test_valid_simple_path(self):
        """Test validation of valid simple paths."""

        class TestConfig(BaseModel):
            field: str = "test"

        # Should not raise
        _validate_config_path(TestConfig, ["field"])

    def test_valid_nested_path(self):
        """Test validation of valid nested paths."""

        class NestedConfig(BaseModel):
            nested_field: str = "test"

        class MainConfig(BaseModel):
            nested: NestedConfig = Field(default_factory=NestedConfig)

        # Should not raise
        _validate_config_path(MainConfig, ["nested", "nested_field"])

    def test_invalid_field_name(self):
        """Test validation error for invalid field names."""

        class TestConfig(BaseModel):
            field: str = "test"

        with pytest.raises(ValueError, match="Field 'invalid' not found"):
            _validate_config_path(TestConfig, ["invalid"])

    def test_invalid_nested_path(self):
        """Test validation error for invalid nested paths."""

        class TestConfig(BaseModel):
            field: str = "test"

        with pytest.raises(ValueError, match="Field 'field' is not a nested model"):
            _validate_config_path(TestConfig, ["field", "nested"])


class TestIntegrationWithRealConfig:
    """Integration tests with the real Config model."""

    def test_all_generated_mappings_are_valid(self):
        """Test that all generated mappings for Config are valid."""
        mappings = generate_env_mappings(Config, "FSM")
        errors = validate_env_mappings(Config, mappings)

        # All generated mappings should be valid
        assert errors == [], f"Generated mappings have validation errors: {errors}"

    def test_specific_config_fields(self):
        """Test specific config fields we know should exist."""
        # Test logging level (it's a Literal type)
        info = get_field_type_info(Config, ["logging", "level"])
        # Literal types are preserved, not converted to str
        assert "Literal" in str(info["type"]) or info["type"] == str
        assert not info["is_optional"]

        # Test forecasting periods
        info = get_field_type_info(Config, ["forecasting", "default_periods"])
        assert info["type"] == int
        assert not info["is_optional"]
        assert info["default"] == 5

        # Test optional API key
        info = get_field_type_info(Config, ["api", "fmp_api_key"])
        assert info["type"] == str
        assert info["is_optional"]
        assert info["default"] is None

    def test_env_mapping_coverage(self):
        """Test that env mappings cover most config fields."""
        from fin_statement_model.config.discovery import list_all_config_paths

        all_paths = set(list_all_config_paths(Config))
        mappings = generate_env_mappings(Config, "FSM")
        mapped_paths = set(".".join(path) for path in mappings.values())

        # Most paths should have env var mappings
        coverage = len(mapped_paths) / len(all_paths)
        assert coverage > 0.8, f"Environment variable coverage is only {coverage:.1%}"
