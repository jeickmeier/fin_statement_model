"""Tests for the IO registry module."""

import pytest
from unittest.mock import Mock, patch
from pydantic import ValidationError

from fin_statement_model.io.core.registry import (
    _get_handler,
    get_reader,
    get_writer,
    register_reader,
    register_writer,
    list_readers,
    list_writers,
    _readers,
    _writers,
    _reader_registry,
    _writer_registry,
    _READER_SCHEMA_MAP,
    _WRITER_SCHEMA_MAP,
    HandlerRegistry,
)
from fin_statement_model.io.core.base import DataReader, DataWriter
from fin_statement_model.io.exceptions import (
    FormatNotSupportedError,
    ReadError,
    WriteError,
)


class TestRegistryDecorators:
    """Test the registration decorators."""

    def test_register_reader_success(self):
        """Test successful reader registration."""

        @register_reader("test_format")
        class TestReader(DataReader):
            def read(self, source, **kwargs):
                return None

        assert "test_format" in _readers
        assert _readers["test_format"] is TestReader

        # Clean up
        del _readers["test_format"]

    def test_register_reader_duplicate_same_class(self):
        """Test re-registering the same reader class is allowed."""

        # Create a class
        class TestReader(DataReader):
            def read(self, source, **kwargs):
                return None

        # First registration
        register_reader("test_format2")(TestReader)

        # Re-register the exact same class object should work
        register_reader("test_format2")(TestReader)

        # Should still be registered
        assert "test_format2" in _readers
        assert _readers["test_format2"] is TestReader

        # Clean up
        del _readers["test_format2"]

    def test_register_reader_duplicate_different_class(self):
        """Test registering a different class for same format raises error."""

        @register_reader("test_format3")
        class TestReader1(DataReader):
            def read(self, source, **kwargs):
                return None

        with pytest.raises(ValueError) as exc_info:

            @register_reader("test_format3")
            class TestReader2(DataReader):
                def read(self, source, **kwargs):
                    return None

        assert "already registered" in str(exc_info.value)

        # Clean up
        del _readers["test_format3"]

    def test_register_writer_success(self):
        """Test successful writer registration."""

        @register_writer("test_format")
        class TestWriter(DataWriter):
            def write(self, graph, target=None, **kwargs):
                return None

        assert "test_format" in _writers
        assert _writers["test_format"] is TestWriter

        # Clean up
        del _writers["test_format"]


class TestGetHandler:
    """Test the generic _get_handler function."""

    def test_get_handler_format_not_supported(self):
        """Test _get_handler raises FormatNotSupportedError for unknown format."""
        # Create a mock registry that raises FormatNotSupportedError
        mock_registry = Mock(spec=HandlerRegistry)
        mock_registry.get.side_effect = FormatNotSupportedError(
            format_type="unknown", operation="read operations"
        )

        with pytest.raises(FormatNotSupportedError) as exc_info:
            _get_handler(
                format_type="unknown",
                registry=mock_registry,
                schema_map={},
                handler_type="read",
                error_class=ReadError,
            )

        assert exc_info.value.format_type == "unknown"
        # Check the error message contains the operation
        assert "read operations" in str(exc_info.value)

    def test_get_handler_with_schema_validation_success(self):
        """Test _get_handler with successful schema validation."""
        # Mock handler class
        mock_handler_class = Mock(return_value="handler_instance")

        # Mock registry
        mock_registry = Mock(spec=HandlerRegistry)
        mock_registry.get.return_value = mock_handler_class

        # Mock schema that validates successfully
        mock_schema = Mock()
        mock_schema.model_validate.return_value = Mock(format_type="test")

        result = _get_handler(
            format_type="test",
            registry=mock_registry,
            schema_map={"test": mock_schema},
            handler_type="read",
            error_class=ReadError,
            source="test.csv",
            extra_param="value",
        )

        assert result == "handler_instance"
        mock_registry.get.assert_called_once_with("test")
        mock_schema.model_validate.assert_called_once_with(
            {"source": "test.csv", "extra_param": "value", "format_type": "test"}
        )
        mock_handler_class.assert_called_once()

    def test_get_handler_with_schema_validation_error(self):
        """Test _get_handler with schema validation error."""
        # Mock registry
        mock_registry = Mock(spec=HandlerRegistry)
        mock_registry.get.return_value = Mock()

        # Mock schema that raises ValidationError
        mock_schema = Mock()
        mock_schema.model_validate.side_effect = ValidationError.from_exception_data(
            "ValidationError",
            [
                {
                    "type": "missing",
                    "loc": ("field",),
                    "msg": "Field required",
                    "input": {},
                }
            ],
        )

        with pytest.raises(ReadError) as exc_info:
            _get_handler(
                format_type="test",
                registry=mock_registry,
                schema_map={"test": mock_schema},
                handler_type="read",
                error_class=ReadError,
                source="test.csv",
            )

        assert "Invalid reader configuration" in str(exc_info.value)
        assert exc_info.value.source_or_target == "test.csv"
        assert exc_info.value.format_type == "test"

    def test_get_handler_instantiation_error(self):
        """Test _get_handler when handler instantiation fails."""
        # Mock handler class that raises exception
        mock_handler_class = Mock(side_effect=RuntimeError("Init failed"))
        # Add __name__ attribute to the mock
        mock_handler_class.__name__ = "MockHandlerClass"

        # Mock registry
        mock_registry = Mock(spec=HandlerRegistry)
        mock_registry.get.return_value = mock_handler_class

        # Mock schema
        mock_schema = Mock()
        mock_schema.model_validate.return_value = Mock()

        with pytest.raises(ReadError) as exc_info:
            _get_handler(
                format_type="test",
                registry=mock_registry,
                schema_map={"test": mock_schema},
                handler_type="read",
                error_class=ReadError,
                source="test.csv",
            )

        assert "Failed to initialize reader" in str(exc_info.value)
        assert isinstance(exc_info.value.original_error, RuntimeError)

    def test_get_handler_without_schema(self):
        """Test _get_handler for legacy handlers without schema."""
        # Mock handler class
        mock_handler_class = Mock(return_value="handler_instance")

        # Mock registry
        mock_registry = Mock(spec=HandlerRegistry)
        mock_registry.get.return_value = mock_handler_class

        result = _get_handler(
            format_type="legacy",
            registry=mock_registry,
            schema_map={},  # No schema for this format
            handler_type="write",
            error_class=WriteError,
            target="output.txt",
            custom_param="value",
        )

        assert result == "handler_instance"
        mock_handler_class.assert_called_once_with(
            target="output.txt", custom_param="value"
        )

    def test_get_handler_error_context_for_reader(self):
        """Test _get_handler sets correct error context for readers."""
        # Mock registry
        mock_registry = Mock(spec=HandlerRegistry)
        mock_registry.get.return_value = Mock()

        # Test with a validation error to check error context
        mock_schema = Mock()
        mock_schema.model_validate.side_effect = ValidationError.from_exception_data(
            "ValidationError",
            [
                {
                    "type": "missing",
                    "loc": ("field",),
                    "msg": "Field required",
                    "input": {},
                }
            ],
        )

        with pytest.raises(ReadError) as exc_info:
            _get_handler(
                format_type="test",
                registry=mock_registry,
                schema_map={"test": mock_schema},
                handler_type="read",
                error_class=ReadError,
                source="input.csv",
            )

        assert exc_info.value.source_or_target == "input.csv"
        assert exc_info.value.format_type == "test"

    def test_get_handler_error_context_for_writer(self):
        """Test _get_handler sets correct error context for writers."""
        # Mock registry
        mock_registry = Mock(spec=HandlerRegistry)
        mock_registry.get.return_value = Mock()

        mock_schema = Mock()
        mock_schema.model_validate.side_effect = ValidationError.from_exception_data(
            "ValidationError",
            [
                {
                    "type": "missing",
                    "loc": ("field",),
                    "msg": "Field required",
                    "input": {},
                }
            ],
        )

        with pytest.raises(WriteError) as exc_info:
            _get_handler(
                format_type="test",
                registry=mock_registry,
                schema_map={"test": mock_schema},
                handler_type="write",
                error_class=WriteError,
                target="output.xlsx",
            )

        assert exc_info.value.source_or_target == "output.xlsx"
        assert exc_info.value.format_type == "test"


class TestGetReaderWriter:
    """Test the public get_reader and get_writer functions."""

    def test_get_reader_uses_get_handler(self):
        """Test get_reader delegates to _get_handler with correct parameters."""
        with patch(
            "fin_statement_model.io.core.registry._get_handler"
        ) as mock_get_handler:
            mock_get_handler.return_value = "reader_instance"

            result = get_reader("excel", source="test.xlsx", sheet_name="Sheet1")

            assert result == "reader_instance"
            mock_get_handler.assert_called_once_with(
                format_type="excel",
                registry=_reader_registry,
                schema_map=_READER_SCHEMA_MAP,
                handler_type="read",
                error_class=ReadError,
                source="test.xlsx",
                sheet_name="Sheet1",
            )

    def test_get_writer_uses_get_handler(self):
        """Test get_writer delegates to _get_handler with correct parameters."""
        with patch(
            "fin_statement_model.io.core.registry._get_handler"
        ) as mock_get_handler:
            mock_get_handler.return_value = "writer_instance"

            result = get_writer("excel", target="output.xlsx", sheet_name="Results")

            assert result == "writer_instance"
            mock_get_handler.assert_called_once_with(
                format_type="excel",
                registry=_writer_registry,
                schema_map=_WRITER_SCHEMA_MAP,
                handler_type="write",
                error_class=WriteError,
                target="output.xlsx",
                sheet_name="Results",
            )


class TestListFunctions:
    """Test the list_readers and list_writers functions."""

    def test_list_readers_returns_copy(self):
        """Test list_readers returns a copy of the registry."""
        readers_copy = list_readers()

        # Should be a dict
        assert isinstance(readers_copy, dict)

        # Modifying the copy shouldn't affect the original
        readers_copy["fake"] = "value"
        assert "fake" not in _readers

    def test_list_writers_returns_copy(self):
        """Test list_writers returns a copy of the registry."""
        writers_copy = list_writers()

        # Should be a dict
        assert isinstance(writers_copy, dict)

        # Modifying the copy shouldn't affect the original
        writers_copy["fake"] = "value"
        assert "fake" not in _writers
