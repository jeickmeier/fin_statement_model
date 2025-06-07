"""Tests for IO utilities module."""

import pytest
from unittest.mock import Mock

from fin_statement_model.io.utils import (
    handle_read_errors,
    handle_write_errors,
    ValueExtractionMixin,
    ValidationResultCollector,
)
from fin_statement_model.io.exceptions import ReadError, WriteError
from fin_statement_model.core.graph import Graph


class TestHandleReadErrors:
    """Test the handle_read_errors decorator."""

    def test_successful_read(self):
        """Test decorator doesn't interfere with successful reads."""

        class MockReader:
            @handle_read_errors()
            def read(self, source, **kwargs):
                return {"data": "success"}

        reader = MockReader()
        result = reader.read("test.csv")
        assert result == {"data": "success"}

    def test_reraises_read_error(self):
        """Test decorator re-raises ReadError without modification."""

        class MockReader:
            @handle_read_errors()
            def read(self, source, **kwargs):
                raise ReadError("Original error", source="test.csv")

        reader = MockReader()
        with pytest.raises(ReadError) as exc_info:
            reader.read("test.csv")

        assert (
            str(exc_info.value) == "Original error involving source/target 'test.csv'"
        )

    def test_converts_file_not_found(self):
        """Test decorator converts FileNotFoundError to ReadError."""

        class MockReader:
            @handle_read_errors()
            def read(self, source, **kwargs):
                raise FileNotFoundError("No such file")

        reader = MockReader()
        with pytest.raises(ReadError) as exc_info:
            reader.read("missing.csv")

        error = exc_info.value
        assert "File not found: missing.csv" in str(error)
        assert error.source_or_target == "missing.csv"
        assert error.format_type == "MockReader"

    def test_converts_value_error(self):
        """Test decorator converts ValueError to ReadError."""

        class MockReader:
            @handle_read_errors()
            def read(self, source, **kwargs):
                raise ValueError("Invalid format")

        reader = MockReader()
        with pytest.raises(ReadError) as exc_info:
            reader.read("bad.csv")

        error = exc_info.value
        assert "Invalid value encountered: Invalid format" in str(error)

    def test_converts_generic_exception(self):
        """Test decorator converts generic exceptions to ReadError."""

        class MockReader:
            @handle_read_errors()
            def read(self, source, **kwargs):
                raise RuntimeError("Something went wrong")

        reader = MockReader()
        with pytest.raises(ReadError) as exc_info:
            reader.read("data.csv")

        error = exc_info.value
        assert "Failed to process source: Something went wrong" in str(error)
        assert isinstance(error.original_error, RuntimeError)


class TestHandleWriteErrors:
    """Test the handle_write_errors decorator."""

    def test_successful_write(self):
        """Test decorator doesn't interfere with successful writes."""

        class MockWriter:
            @handle_write_errors()
            def write(self, graph, target=None, **kwargs):
                return "Success"

        writer = MockWriter()
        graph = Mock(spec=Graph)
        result = writer.write(graph, "output.xlsx")
        assert result == "Success"

    def test_reraises_write_error(self):
        """Test decorator re-raises WriteError without modification."""

        class MockWriter:
            @handle_write_errors()
            def write(self, graph, target=None, **kwargs):
                raise WriteError("Original error", target="output.xlsx")

        writer = MockWriter()
        graph = Mock(spec=Graph)
        with pytest.raises(WriteError) as exc_info:
            writer.write(graph, "output.xlsx")

        assert (
            str(exc_info.value)
            == "Original error involving source/target 'output.xlsx'"
        )

    def test_converts_generic_exception(self):
        """Test decorator converts generic exceptions to WriteError."""

        class MockWriter:
            @handle_write_errors()
            def write(self, graph, target=None, **kwargs):
                raise RuntimeError("Write failed")

        writer = MockWriter()
        graph = Mock(spec=Graph)
        with pytest.raises(WriteError) as exc_info:
            writer.write(graph, "output.xlsx")

        error = exc_info.value
        assert "Failed to write data: Write failed" in str(error)
        assert error.source_or_target == "output.xlsx"
        assert error.format_type == "MockWriter"


class TestValueExtractionMixin:
    """Test the ValueExtractionMixin class."""

    def setup_method(self):
        """Set up test fixtures."""

        class TestExtractor(ValueExtractionMixin):
            pass

        self.extractor = TestExtractor()

    def test_extract_calculated_value(self):
        """Test extracting value using calculate method."""
        node = Mock()
        node.calculate = Mock(return_value=100.5)
        node.values = {"2023": 50.0}

        result = self.extractor.extract_node_value(node, "2023", calculate=True)
        assert result == 100.5
        node.calculate.assert_called_once_with("2023")

    def test_extract_stored_value_when_calculate_false(self):
        """Test extracting stored value when calculate is False."""
        node = Mock()
        node.calculate = Mock(return_value=100.5)
        node.values = {"2023": 50.0}

        result = self.extractor.extract_node_value(node, "2023", calculate=False)
        assert result == 50.0
        node.calculate.assert_not_called()

    def test_fallback_to_stored_value(self):
        """Test falling back to stored value when calculate fails."""
        node = Mock()
        node.calculate = Mock(side_effect=Exception("Calc error"))
        node.values = {"2023": 75.0}

        result = self.extractor.extract_node_value(node, "2023", calculate=True)
        assert result is None  # Returns None on exception

    def test_extract_missing_value(self):
        """Test extracting value for missing period."""
        node = Mock()
        node.values = {"2023": 50.0}

        result = self.extractor.extract_node_value(node, "2024", calculate=False)
        assert result is None

    def test_extract_non_numeric_value(self):
        """Test handling non-numeric values."""
        node = Mock()
        node.calculate = Mock(return_value="not a number")
        node.values = {"2023": "also not a number"}

        result = self.extractor.extract_node_value(node, "2023", calculate=True)
        assert result is None

    def test_extract_from_node_without_methods(self):
        """Test extracting from node without calculate method or values."""
        node = object()  # Plain object without attributes

        result = self.extractor.extract_node_value(node, "2023")
        assert result is None

    def test_convert_int_to_float(self):
        """Test that integer values are converted to float."""
        node = Mock()
        node.calculate = Mock(return_value=100)

        result = self.extractor.extract_node_value(node, "2023")
        assert result == 100.0
        assert isinstance(result, float)


class TestValidationResultCollector:
    """Test the ValidationResultCollector class."""

    def test_add_valid_result(self):
        """Test adding valid results."""
        collector = ValidationResultCollector()
        collector.add_result("item1", True, "Valid item")

        assert len(collector.results) == 1
        assert len(collector.errors) == 0
        assert not collector.has_errors()

    def test_add_invalid_result(self):
        """Test adding invalid results."""
        collector = ValidationResultCollector()
        collector.add_result("item1", False, "Invalid format")

        assert len(collector.results) == 1
        assert len(collector.errors) == 1
        assert collector.has_errors()
        assert collector.errors[0] == "item1: Invalid format"

    def test_add_warning(self):
        """Test adding warnings."""
        collector = ValidationResultCollector()
        collector.add_result("item1", True, "Valid but warning: deprecated")

        assert len(collector.results) == 1
        assert len(collector.warnings) == 1
        assert not collector.has_errors()
        assert collector.warnings[0] == "item1: Valid but warning: deprecated"

    def test_get_summary(self):
        """Test getting validation summary."""
        collector = ValidationResultCollector()
        collector.add_result("item1", True, "Valid")
        collector.add_result("item2", False, "Invalid")
        collector.add_result("item3", True, "Valid with warning: check this")
        collector.add_result("item4", False, "Another error")

        summary = collector.get_summary()

        assert summary["total"] == 4
        assert summary["valid"] == 2
        assert summary["invalid"] == 2
        assert summary["error_rate"] == 0.5
        assert len(summary["errors"]) == 2
        assert len(summary["warnings"]) == 1

    def test_empty_summary(self):
        """Test summary with no results."""
        collector = ValidationResultCollector()
        summary = collector.get_summary()

        assert summary["total"] == 0
        assert summary["valid"] == 0
        assert summary["invalid"] == 0
        assert summary["error_rate"] == 0.0
        assert len(summary["errors"]) == 0
        assert len(summary["warnings"]) == 0
