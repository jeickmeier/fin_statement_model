"""Tests for ConfigurationMixin functionality."""

import os
from typing import Any, Optional
from unittest.mock import patch
import pytest
from pydantic import BaseModel, Field

from fin_statement_model.io.core.mixins import ConfigurationMixin
from fin_statement_model.io.exceptions import ReadError


class TestConfigurationMixin:
    """Test the ConfigurationMixin functionality."""

    def setup_method(self):
        """Set up test fixtures."""

        # Create a test class that uses ConfigurationMixin
        class TestReader(ConfigurationMixin):
            def __init__(self, cfg: Optional[Any] = None):
                super().__init__()
                self.cfg = cfg
                self.__class__.__name__ = "TestReader"

        # Create a test Pydantic config model
        class TestConfig(BaseModel):
            source: str = Field(..., description="Test source")
            format_type: str = Field("test", description="Test format")
            optional_field: str = Field("default_value", description="Optional field")
            numeric_field: int = Field(42, description="Numeric field")

        self.TestReader = TestReader
        self.TestConfig = TestConfig

    def test_configuration_context(self):
        """Test configuration context management."""
        reader = self.TestReader()

        # Initially empty
        assert reader.get_config_context() == {}

        # Set context
        reader.set_config_context(file_path="test.csv", operation="read")
        context = reader.get_config_context()
        assert context["file_path"] == "test.csv"
        assert context["operation"] == "read"

        # Update context
        reader.set_config_context(row_count=100)
        context = reader.get_config_context()
        assert context["file_path"] == "test.csv"
        assert context["row_count"] == 100

    def test_configuration_overrides(self):
        """Test configuration override functionality."""
        config = self.TestConfig(source="test.csv")
        reader = self.TestReader(config)

        # Normal access
        assert reader.get_config_value("source") == "test.csv"

        # Set override
        reader.set_config_override("source", "override.csv")
        assert reader.get_config_value("source") == "override.csv"

        # Clear overrides
        reader.clear_config_overrides()
        assert reader.get_config_value("source") == "test.csv"

    def test_get_config_value_basic(self):
        """Test basic configuration value retrieval."""
        config = self.TestConfig(source="test.csv")
        reader = self.TestReader(config)

        # Existing value
        assert reader.get_config_value("source") == "test.csv"

        # Default value
        assert reader.get_config_value("nonexistent", "default") == "default"

        # None default
        assert reader.get_config_value("nonexistent") is None

    def test_get_config_value_with_type_validation(self):
        """Test configuration value retrieval with type validation."""
        config = self.TestConfig(source="test.csv", numeric_field=42)
        reader = self.TestReader(config)

        # Correct type
        value = reader.get_config_value("numeric_field", value_type=int)
        assert value == 42
        assert isinstance(value, int)

        # Type conversion
        value = reader.get_config_value("numeric_field", value_type=str)
        assert value == "42"
        assert isinstance(value, str)

    def test_get_config_value_type_validation_failure(self):
        """Test configuration value type validation failure."""
        config = self.TestConfig(source="test.csv")
        reader = self.TestReader(config)

        # Invalid type conversion
        with pytest.raises(ReadError) as exc_info:
            reader.get_config_value("source", value_type=int)

        error = exc_info.value
        assert "invalid type" in str(error)
        assert "Expected int, got str" in str(error)

    def test_get_config_value_with_validator(self):
        """Test configuration value retrieval with custom validator."""
        config = self.TestConfig(source="test.csv", numeric_field=42)
        reader = self.TestReader(config)

        # Valid value
        value = reader.get_config_value("numeric_field", validator=lambda x: x > 0)
        assert value == 42

        # Invalid value
        with pytest.raises(ReadError) as exc_info:
            reader.get_config_value("numeric_field", validator=lambda x: x > 100)

        assert "failed validation" in str(exc_info.value)

    def test_get_config_value_validator_exception(self):
        """Test configuration value validator exception handling."""
        config = self.TestConfig(source="test.csv")
        reader = self.TestReader(config)

        def failing_validator(value: Any) -> bool:
            raise ValueError("Validator error")

        with pytest.raises(ReadError) as exc_info:
            reader.get_config_value("source", validator=failing_validator)

        error = exc_info.value
        assert "Configuration validation error" in str(error)
        assert "Validator error" in str(error)

    def test_require_config_value_success(self):
        """Test successful required configuration value retrieval."""
        config = self.TestConfig(source="test.csv")
        reader = self.TestReader(config)

        value = reader.require_config_value("source")
        assert value == "test.csv"

    def test_require_config_value_missing(self):
        """Test required configuration value missing."""
        config = self.TestConfig(source="test.csv")
        reader = self.TestReader(config)

        with pytest.raises(ReadError) as exc_info:
            reader.require_config_value("nonexistent")

        assert "Required configuration value 'nonexistent' is missing" in str(
            exc_info.value
        )

    def test_require_config_value_with_validation(self):
        """Test required configuration value with type and custom validation."""
        config = self.TestConfig(source="test.csv", numeric_field=42)
        reader = self.TestReader(config)

        # Success case
        value = reader.require_config_value(
            "numeric_field", value_type=int, validator=lambda x: x > 0
        )
        assert value == 42

        # Validation failure
        with pytest.raises(ReadError):
            reader.require_config_value("numeric_field", validator=lambda x: x > 100)

    def test_get_config_with_env_fallback(self):
        """Test configuration value with environment variable fallback."""
        config = self.TestConfig(source="test.csv")
        reader = self.TestReader(config)

        # Config value exists
        value = reader.get_config_with_env_fallback("source", "TEST_SOURCE")
        assert value == "test.csv"

        # Config value missing, env var exists
        with patch.dict(os.environ, {"TEST_ENV": "env_value"}):
            value = reader.get_config_with_env_fallback("nonexistent", "TEST_ENV")
            assert value == "env_value"

        # Both missing, use default
        value = reader.get_config_with_env_fallback(
            "nonexistent", "MISSING_ENV", "default"
        )
        assert value == "default"

    def test_get_config_with_env_fallback_type_conversion(self):
        """Test environment variable fallback with type conversion."""
        reader = self.TestReader()

        with patch.dict(os.environ, {"TEST_NUMBER": "123"}):
            value = reader.get_config_with_env_fallback(
                "nonexistent", "TEST_NUMBER", value_type=int
            )
            assert value == 123
            assert isinstance(value, int)

    def test_get_config_with_env_fallback_conversion_failure(self):
        """Test environment variable fallback type conversion failure."""
        reader = self.TestReader()

        with (
            patch.dict(os.environ, {"TEST_INVALID": "not_a_number"}),
            patch("fin_statement_model.io.core.mixins.logger") as mock_logger,
        ):
            value = reader.get_config_with_env_fallback(
                "nonexistent", "TEST_INVALID", value_type=int
            )
            assert value == "not_a_number"  # Should use as-is
            mock_logger.warning.assert_called_once()

    def test_validate_configuration_success(self):
        """Test successful configuration validation."""
        config = self.TestConfig(source="test.csv")
        reader = self.TestReader(config)

        validator = reader.validate_configuration()
        assert not validator.has_errors()
        summary = validator.get_summary()
        assert summary["valid"] == 1

    def test_validate_configuration_missing(self):
        """Test configuration validation with missing config."""
        reader = self.TestReader()

        validator = reader.validate_configuration()
        assert validator.has_errors()
        summary = validator.get_summary()
        assert "Missing configuration object" in summary["errors"][0]

    def test_get_effective_configuration_pydantic(self):
        """Test getting effective configuration from Pydantic model."""
        config = self.TestConfig(source="test.csv")
        reader = self.TestReader(config)
        reader.set_config_override("source", "override.csv")

        effective = reader.get_effective_configuration()
        assert effective["source"] == "override.csv"  # Override applied
        assert effective["format_type"] == "test"  # Original value

    def test_get_effective_configuration_regular_object(self):
        """Test getting effective configuration from regular object."""

        class SimpleConfig:
            def __init__(self):
                self.source = "test.csv"
                self.format_type = "test"

        config = SimpleConfig()
        reader = self.TestReader(config)
        reader.set_config_override("source", "override.csv")

        effective = reader.get_effective_configuration()
        assert effective["source"] == "override.csv"
        assert effective["format_type"] == "test"

    def test_merge_configurations_pydantic(self):
        """Test merging Pydantic configuration objects."""
        config1 = self.TestConfig(source="test1.csv", format_type="type1")
        config2 = self.TestConfig(source="test2.csv", numeric_field=100)

        reader = self.TestReader()
        merged = reader.merge_configurations(config1, config2)

        assert merged["source"] == "test2.csv"  # Later takes precedence
        assert merged["format_type"] == "test"  # From second config (default value)
        assert merged["numeric_field"] == 100  # From second config

    def test_merge_configurations_mixed_types(self):
        """Test merging different types of configuration objects."""
        config1 = self.TestConfig(source="test1.csv")

        class SimpleConfig:
            def __init__(self):
                self.source = "test2.csv"
                self.extra_field = "extra"

        config2 = SimpleConfig()
        config3 = {"source": "test3.csv", "dict_field": "dict_value"}

        reader = self.TestReader()
        merged = reader.merge_configurations(config1, config2, config3)

        assert merged["source"] == "test3.csv"  # Last takes precedence
        assert merged["extra_field"] == "extra"
        assert merged["dict_field"] == "dict_value"

    def test_merge_configurations_with_none(self):
        """Test merging configurations with None values."""
        config = self.TestConfig(source="test.csv")
        reader = self.TestReader()

        merged = reader.merge_configurations(None, config, None)
        assert merged["source"] == "test.csv"

    def test_merge_configurations_unsupported_type(self):
        """Test merging with unsupported configuration type."""
        config = self.TestConfig(source="test.csv")
        reader = self.TestReader()

        with patch("fin_statement_model.io.core.mixins.logger") as mock_logger:
            merged = reader.merge_configurations(config, "unsupported")
            assert merged["source"] == "test.csv"
            mock_logger.warning.assert_called_once()

    def test_no_configuration_object(self):
        """Test behavior when no configuration object is set."""
        reader = self.TestReader()

        # Should return default
        assert reader.get_config_value("anything", "default") == "default"

        # Should raise for required
        with pytest.raises(ReadError):
            reader.require_config_value("anything")

    def test_configuration_context_in_errors(self):
        """Test that configuration context can be set and retrieved."""
        reader = self.TestReader()
        reader.set_config_context(file_path="test.csv", operation="read")

        # Verify context is set
        context = reader.get_config_context()
        assert context["file_path"] == "test.csv"
        assert context["operation"] == "read"

        # Verify error is still raised for missing config
        with pytest.raises(ReadError) as exc_info:
            reader.require_config_value("missing")

        error = exc_info.value
        assert "Required configuration value 'missing' is missing" in str(error)
