"""Tests for the registry base class."""

import pytest

from fin_statement_model.io.core.registry import HandlerRegistry
from fin_statement_model.io.exceptions import FormatNotSupportedError


class MockHandler:
    """Mock handler class for testing."""


class AnotherMockHandler:
    """Another mock handler class for testing."""


class TestHandlerRegistry:
    """Test the HandlerRegistry base class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.registry = HandlerRegistry[MockHandler]("test")

    def test_init(self):
        """Test registry initialization."""
        registry = HandlerRegistry[MockHandler]("reader")
        assert registry._handler_type == "reader"
        assert len(registry) == 0
        assert registry._registry == {}

    def test_register_decorator(self):
        """Test the register decorator."""

        @self.registry.register("format1")
        class TestHandler(MockHandler):
            pass

        assert "format1" in self.registry
        assert self.registry.get("format1") is TestHandler

    def test_register_multiple_formats(self):
        """Test registering multiple formats."""

        @self.registry.register("format1")
        class Handler1(MockHandler):
            pass

        @self.registry.register("format2")
        class Handler2(MockHandler):
            pass

        assert len(self.registry) == 2
        assert self.registry.get("format1") is Handler1
        assert self.registry.get("format2") is Handler2

    def test_register_same_class_twice(self):
        """Test re-registering the same class is allowed."""

        class TestHandler(MockHandler):
            pass

        # First registration
        self.registry.register("format1")(TestHandler)

        # Re-register same class should work
        self.registry.register("format1")(TestHandler)

        assert self.registry.get("format1") is TestHandler

    def test_register_different_class_same_format(self):
        """Test registering a different class for same format raises error."""

        @self.registry.register("format1")
        class Handler1(MockHandler):
            pass

        with pytest.raises(ValueError) as exc_info:

            @self.registry.register("format1")
            class Handler2(MockHandler):
                pass

        assert "already registered" in str(exc_info.value)
        assert "format1" in str(exc_info.value)

    def test_get_registered_format(self):
        """Test getting a registered format."""

        @self.registry.register("format1")
        class TestHandler(MockHandler):
            pass

        result = self.registry.get("format1")
        assert result is TestHandler

    def test_get_unregistered_format(self):
        """Test getting an unregistered format raises error."""
        with pytest.raises(FormatNotSupportedError) as exc_info:
            self.registry.get("unknown")

        assert exc_info.value.format_type == "unknown"
        assert "test operations" in str(exc_info.value)

    def test_list_formats(self):
        """Test listing all registered formats."""

        @self.registry.register("format1")
        class Handler1(MockHandler):
            pass

        @self.registry.register("format2")
        class Handler2(MockHandler):
            pass

        formats = self.registry.list_formats()
        assert len(formats) == 2
        assert formats["format1"] is Handler1
        assert formats["format2"] is Handler2

        # Ensure it's a copy
        formats["format3"] = MockHandler
        assert "format3" not in self.registry

    def test_is_registered(self):
        """Test checking if a format is registered."""
        assert not self.registry.is_registered("format1")

        @self.registry.register("format1")
        class TestHandler(MockHandler):
            pass

        assert self.registry.is_registered("format1")
        assert not self.registry.is_registered("format2")

    def test_unregister(self):
        """Test unregistering a format."""

        @self.registry.register("format1")
        class TestHandler(MockHandler):
            pass

        # Unregister existing format
        removed = self.registry.unregister("format1")
        assert removed is TestHandler
        assert "format1" not in self.registry

        # Unregister non-existent format
        removed = self.registry.unregister("format1")
        assert removed is None

    def test_clear(self):
        """Test clearing all registrations."""

        @self.registry.register("format1")
        class Handler1(MockHandler):
            pass

        @self.registry.register("format2")
        class Handler2(MockHandler):
            pass

        assert len(self.registry) == 2

        self.registry.clear()

        assert len(self.registry) == 0
        assert "format1" not in self.registry
        assert "format2" not in self.registry

    def test_contains_operator(self):
        """Test the 'in' operator support."""
        assert "format1" not in self.registry

        @self.registry.register("format1")
        class TestHandler(MockHandler):
            pass

        assert "format1" in self.registry
        assert "format2" not in self.registry

    def test_len_operator(self):
        """Test the len() operator support."""
        assert len(self.registry) == 0

        @self.registry.register("format1")
        class Handler1(MockHandler):
            pass

        assert len(self.registry) == 1

        @self.registry.register("format2")
        class Handler2(MockHandler):
            pass

        assert len(self.registry) == 2

        self.registry.unregister("format1")
        assert len(self.registry) == 1

    def test_handler_type_in_messages(self):
        """Test that handler_type is used in error messages."""
        reader_registry = HandlerRegistry[MockHandler]("reader")
        writer_registry = HandlerRegistry[MockHandler]("writer")

        # Test FormatNotSupportedError message
        with pytest.raises(FormatNotSupportedError) as exc_info:
            reader_registry.get("unknown")
        assert "reader operations" in str(exc_info.value)

        with pytest.raises(FormatNotSupportedError) as exc_info:
            writer_registry.get("unknown")
        assert "writer operations" in str(exc_info.value)

        # Test ValueError message for duplicate registration
        @reader_registry.register("format1")
        class Handler1(MockHandler):
            pass

        with pytest.raises(ValueError) as exc_info:

            @reader_registry.register("format1")
            class Handler2(MockHandler):
                pass

        assert "Reader format type" in str(exc_info.value)
