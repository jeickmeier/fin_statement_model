"""Tests for IO base implementations."""

import pytest
from unittest.mock import Mock, patch
import numpy as np

from fin_statement_model.io.base_implementations import (
    FileBasedReader,
    ConfigurableReaderMixin,
    DataFrameBasedWriter,
    BatchProcessingMixin,
)
from fin_statement_model.io.exceptions import ReadError, WriteError
from fin_statement_model.io.utils import handle_read_errors, handle_write_errors
from fin_statement_model.core.graph import Graph


class TestFileBasedReader:
    """Test the FileBasedReader base class."""

    def test_validate_file_exists_success(self, tmp_path):
        """Test file validation passes for existing file."""
        # Create a temporary file
        test_file = tmp_path / "test.csv"
        test_file.write_text("data")

        class TestReader(FileBasedReader):
            def read(self, source, **kwargs):
                return Graph()

        reader = TestReader()
        # Should not raise
        reader.validate_file_exists(str(test_file))

    def test_validate_file_exists_failure(self):
        """Test file validation fails for non-existent file."""

        class TestReader(FileBasedReader):
            def read(self, source, **kwargs):
                return Graph()

        reader = TestReader()
        with pytest.raises(ReadError) as exc_info:
            reader.validate_file_exists("/non/existent/file.csv")

        error = exc_info.value
        assert "File not found" in str(error)
        assert error.source_or_target == "/non/existent/file.csv"
        assert error.format_type == "TestReader"

    def test_validate_file_extension_success(self):
        """Test extension validation passes for valid extensions."""

        class TestReader(FileBasedReader):
            def read(self, source, **kwargs):
                return Graph()

        reader = TestReader()
        # Should not raise
        reader.validate_file_extension("data.csv", (".csv", ".txt"))
        reader.validate_file_extension("DATA.CSV", (".csv", ".txt"))  # Case insensitive

    def test_validate_file_extension_failure(self):
        """Test extension validation fails for invalid extensions."""

        class TestReader(FileBasedReader):
            def read(self, source, **kwargs):
                return Graph()

        reader = TestReader()
        with pytest.raises(ReadError) as exc_info:
            reader.validate_file_extension("data.xlsx", (".csv", ".txt"))

        error = exc_info.value
        assert "Invalid file extension" in str(error)
        assert "'.xlsx'" in str(error)
        assert "('.csv', '.txt')" in str(error)

    def test_concrete_implementation_with_decorator(self):
        """Test that concrete implementations can use the decorator."""

        class TestReader(FileBasedReader):
            @handle_read_errors()
            def read(self, source, **kwargs):
                raise ValueError("Test error")

        reader = TestReader()
        with pytest.raises(ReadError) as exc_info:
            reader.read("test.csv")

        # Decorator should convert ValueError to ReadError
        error = exc_info.value
        assert "Invalid value encountered: Test error" in str(error)

    def test_concrete_implementation_without_decorator(self):
        """Test that concrete implementations work without decorator (but don't get error conversion)."""

        class TestReader(FileBasedReader):
            def read(self, source, **kwargs):
                raise ValueError("Test error")

        reader = TestReader()
        # Without decorator, original exception is raised
        with pytest.raises(ValueError) as exc_info:
            reader.read("test.csv")

        assert str(exc_info.value) == "Test error"


class TestConfigurableReaderMixin:
    """Test the ConfigurableReaderMixin."""

    def test_get_config_value_with_config(self):
        """Test getting config value when config exists."""

        class TestConfig:
            sheet_name = "Sheet1"
            delimiter = ","

        class TestReader(ConfigurableReaderMixin):
            def __init__(self):
                self.cfg = TestConfig()

        reader = TestReader()
        assert reader.get_config_value("sheet_name") == "Sheet1"
        assert reader.get_config_value("delimiter") == ","
        assert reader.get_config_value("missing", "default") == "default"

    def test_get_config_value_without_config(self):
        """Test getting config value when no config exists."""

        class TestReader(ConfigurableReaderMixin):
            pass

        reader = TestReader()
        assert reader.get_config_value("anything", "default") == "default"

    def test_require_config_value_success(self):
        """Test requiring config value that exists."""

        class TestConfig:
            api_key = "secret123"

        class TestReader(ConfigurableReaderMixin):
            def __init__(self):
                self.cfg = TestConfig()

        reader = TestReader()
        assert reader.require_config_value("api_key") == "secret123"

    def test_require_config_value_missing_config(self):
        """Test requiring config value when no config exists."""

        class TestReader(ConfigurableReaderMixin):
            pass

        reader = TestReader()
        with pytest.raises(ReadError) as exc_info:
            reader.require_config_value("api_key")

        assert "missing configuration object" in str(exc_info.value)

    def test_require_config_value_missing_key(self):
        """Test requiring config value that doesn't exist."""

        class TestConfig:
            other_key = "value"

        class TestReader(ConfigurableReaderMixin):
            def __init__(self):
                self.cfg = TestConfig()

        reader = TestReader()
        with pytest.raises(ReadError) as exc_info:
            reader.require_config_value("api_key")

        assert "Required configuration value 'api_key' is missing" in str(exc_info.value)


class TestDataFrameBasedWriter:
    """Test the DataFrameBasedWriter base class."""

    def setup_method(self):
        """Set up test fixtures."""

        class TestWriter(DataFrameBasedWriter):
            def write(self, graph, target=None, **kwargs):
                return self.extract_graph_data(graph)

        self.writer = TestWriter()

    def test_extract_graph_data_basic(self):
        """Test basic data extraction from graph."""
        # Create a mock graph with nodes
        graph = Mock(spec=Graph)
        graph.periods = ["2022", "2023"]

        node1 = Mock()
        node1.values = {"2022": 100.0, "2023": 110.0}

        node2 = Mock()
        node2.calculate = Mock(side_effect=lambda p: 200.0 if p == "2022" else 220.0)

        graph.nodes = {"revenue": node1, "costs": node2}

        # Extract data
        data = self.writer.extract_graph_data(graph)

        assert data["revenue"]["2022"] == 100.0
        assert data["revenue"]["2023"] == 110.0
        assert data["costs"]["2022"] == 200.0
        assert data["costs"]["2023"] == 220.0

    def test_extract_graph_data_with_include_nodes(self):
        """Test data extraction with specific nodes."""
        graph = Mock(spec=Graph)
        graph.periods = ["2022"]

        node1 = Mock()
        node1.values = {"2022": 100.0}

        node2 = Mock()
        node2.values = {"2022": 200.0}

        graph.nodes = {"revenue": node1, "costs": node2}

        # Extract only revenue
        data = self.writer.extract_graph_data(graph, include_nodes=["revenue"])

        assert "revenue" in data
        assert "costs" not in data

    def test_extract_graph_data_missing_nodes_warning(self):
        """Test warning for missing requested nodes."""
        graph = Mock(spec=Graph)
        graph.periods = ["2022"]
        graph.nodes = {}

        with patch("fin_statement_model.io.base_implementations.logger") as mock_logger:
            data = self.writer.extract_graph_data(graph, include_nodes=["missing"])
            mock_logger.warning.assert_called_with(
                "Requested nodes not found in graph: ['missing']"
            )

        assert len(data) == 0

    def test_extract_graph_data_handles_none_values(self):
        """Test handling of None values."""
        graph = Mock(spec=Graph)
        graph.periods = ["2022"]

        node = Mock()
        # Mock extract_node_value to return None
        self.writer.extract_node_value = Mock(return_value=None)

        graph.nodes = {"revenue": node}

        data = self.writer.extract_graph_data(graph)

        # None should be converted to NaN
        assert np.isnan(data["revenue"]["2022"])

    def test_concrete_implementation_with_decorator(self):
        """Test that concrete implementations can use the decorator."""

        class TestWriter(DataFrameBasedWriter):
            @handle_write_errors()
            def write(self, graph, target=None, **kwargs):
                raise RuntimeError("Write failed")

        writer = TestWriter()
        graph = Mock(spec=Graph)

        with pytest.raises(WriteError) as exc_info:
            writer.write(graph, "output.xlsx")

        # Decorator should convert RuntimeError to WriteError
        error = exc_info.value
        assert "Failed to write data: Write failed" in str(error)

    def test_concrete_implementation_without_decorator(self):
        """Test that concrete implementations work without decorator."""

        class TestWriter(DataFrameBasedWriter):
            def write(self, graph, target=None, **kwargs):
                raise RuntimeError("Write failed")

        writer = TestWriter()
        graph = Mock(spec=Graph)

        # Without decorator, original exception is raised
        with pytest.raises(RuntimeError) as exc_info:
            writer.write(graph, "output.xlsx")

        assert str(exc_info.value) == "Write failed"


class TestBatchProcessingMixin:
    """Test the BatchProcessingMixin."""

    def test_process_in_batches(self):
        """Test processing items in batches."""
        processor = BatchProcessingMixin(batch_size=3)

        items = list(range(10))

        def process_func(batch):
            return [x * 2 for x in batch]

        results = processor.process_in_batches(items, process_func)

        assert results == [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]
        assert processor.get_progress() == (10, 10)

    def test_process_with_progress_callback(self):
        """Test progress callback is called."""
        processor = BatchProcessingMixin(batch_size=2)

        items = list(range(6))
        progress_calls = []

        def progress_callback(processed, total):
            progress_calls.append((processed, total))

        def process_func(batch):
            return batch

        processor.process_in_batches(items, process_func, progress_callback)

        # Should be called after each batch
        assert progress_calls == [(2, 6), (4, 6), (6, 6)]

    def test_logging_on_large_batches(self):
        """Test that progress is logged for large datasets."""
        processor = BatchProcessingMixin(batch_size=10)

        # Create enough items to trigger logging (batch_size * 10)
        items = list(range(101))

        def process_func(batch):
            return batch

        with patch("fin_statement_model.io.base_implementations.logger") as mock_logger:
            processor.process_in_batches(items, process_func)

            # Should log at 100 items processed
            mock_logger.info.assert_called()
            call_args = mock_logger.info.call_args[0][0]
            assert "Processed 100/101 items" in call_args
            assert "99.0%" in call_args
