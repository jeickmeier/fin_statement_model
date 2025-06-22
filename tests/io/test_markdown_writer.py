"""Tests for the MarkdownWriter class."""

import pytest
from unittest.mock import Mock, patch

from fin_statement_model.core.graph import Graph
from fin_statement_model.io.formats.markdown_writer import MarkdownWriter
from fin_statement_model.io.config.models import MarkdownWriterConfig
from fin_statement_model.io.exceptions import WriteError
from fin_statement_model.statements.structure import StatementStructure


class TestMarkdownWriter:
    """Test cases for MarkdownWriter."""

    def test_init_default_config(self):
        """Test writer initialization with default config."""
        writer = MarkdownWriter()
        assert writer.config.format_type == "markdown"
        assert writer.config.target is None
        assert writer.config.indent_spaces == 4  # Default from pydantic

    def test_init_custom_config(self):
        """Test writer initialization with custom config."""
        config = MarkdownWriterConfig(
            format_type="markdown",
            target="output.md",
            indent_spaces=2,
        )
        writer = MarkdownWriter(config)
        assert writer.config.format_type == "markdown"
        assert writer.config.target == "output.md"
        assert writer.config.indent_spaces == 2

    def test_format_value_none(self):
        """Test formatting None values."""
        writer = MarkdownWriter()
        result = writer._format_value(None)
        assert result == ""

    def test_format_value_string(self):
        """Test formatting string values."""
        writer = MarkdownWriter()
        result = writer._format_value("test")
        assert result == "test"

    def test_format_value_integer(self):
        """Test formatting integer values."""
        writer = MarkdownWriter()
        result = writer._format_value(1000)
        assert result == "1000"

    def test_format_value_float(self):
        """Test formatting float values."""
        writer = MarkdownWriter()
        result = writer._format_value(1234.56)
        assert result == "1,234.56"

    def test_write_without_statement_structure(self):
        """Test write fails when statement_structure is not provided."""
        writer = MarkdownWriter()
        graph = Mock(spec=Graph)

        with pytest.raises(WriteError) as exc_info:
            writer.write(graph)

        assert "Must provide 'statement_structure' argument" in str(exc_info.value)

    @patch("fin_statement_model.io.formats.markdown_writer.MarkdownStatementRenderer")
    @patch("fin_statement_model.io.formats.markdown_writer.MarkdownTableFormatter")
    @patch("fin_statement_model.io.formats.markdown_writer.MarkdownNotesBuilder")
    def test_write_with_statement_structure(
        self, mock_notes_builder, mock_formatter, mock_renderer
    ):
        """Test successful write with statement structure."""
        # Setup mocks
        mock_graph = Mock(spec=Graph)
        mock_structure = Mock(spec=StatementStructure)

        # Mock renderer
        mock_renderer_instance = Mock()
        mock_renderer.return_value = mock_renderer_instance
        mock_items = [{"name": "Revenue", "values": {"2023": 1000}}]
        mock_renderer_instance.render_structure.return_value = mock_items
        mock_renderer_instance.periods = ["2023"]

        # Mock formatter
        mock_formatter_instance = Mock()
        mock_formatter.return_value = mock_formatter_instance
        mock_table_lines = [
            "| Description | 2023 |",
            "| --- | --- |",
            "| Revenue | 1000 |",
        ]
        mock_formatter_instance.format_table.return_value = mock_table_lines

        # Mock notes builder
        mock_notes_instance = Mock()
        mock_notes_builder.return_value = mock_notes_instance
        mock_notes_lines = ["", "## Notes", "- Test note"]
        mock_notes_instance.build_notes.return_value = mock_notes_lines

        # Execute
        writer = MarkdownWriter()
        result = writer.write(mock_graph, statement_structure=mock_structure)

        # Verify
        expected = "\n".join(mock_table_lines + mock_notes_lines)
        assert result == expected

        # Verify calls
        mock_renderer.assert_called_once_with(mock_graph, writer.config.indent_spaces)
        mock_renderer_instance.render_structure.assert_called_once()
        mock_formatter_instance.format_table.assert_called_once()
        mock_notes_instance.build_notes.assert_called_once()

    @patch("fin_statement_model.io.formats.markdown_writer.MarkdownStatementRenderer")
    def test_write_with_empty_items(self, mock_renderer):
        """Test write with empty items returns empty string."""
        # Setup mocks
        mock_graph = Mock(spec=Graph)
        mock_structure = Mock(spec=StatementStructure)

        # Mock renderer returning empty items
        mock_renderer_instance = Mock()
        mock_renderer.return_value = mock_renderer_instance
        mock_renderer_instance.render_structure.return_value = []
        mock_renderer_instance.periods = []

        # Execute
        writer = MarkdownWriter()
        result = writer.write(mock_graph, statement_structure=mock_structure)

        # Verify
        assert result == ""

    @patch("fin_statement_model.io.formats.markdown_writer.MarkdownStatementRenderer")
    @patch("fin_statement_model.io.formats.markdown_writer.MarkdownTableFormatter")
    @patch("fin_statement_model.io.formats.markdown_writer.MarkdownNotesBuilder")
    def test_write_with_periods_and_configs(
        self, mock_notes_builder, mock_formatter, mock_renderer
    ):
        """Test write with historical/forecast periods and configs."""
        # Setup mocks
        mock_graph = Mock(spec=Graph)
        mock_structure = Mock(spec=StatementStructure)

        # Mock renderer
        mock_renderer_instance = Mock()
        mock_renderer.return_value = mock_renderer_instance
        mock_items = [{"name": "Revenue", "values": {"2023": 1000, "2024": 1100}}]
        mock_renderer_instance.render_structure.return_value = mock_items
        mock_renderer_instance.periods = ["2023", "2024"]

        # Mock formatter
        mock_formatter_instance = Mock()
        mock_formatter.return_value = mock_formatter_instance
        mock_formatter_instance.format_table.return_value = []

        # Mock notes builder
        mock_notes_instance = Mock()
        mock_notes_builder.return_value = mock_notes_instance
        mock_notes_instance.build_notes.return_value = []

        # Execute with additional kwargs
        writer = MarkdownWriter()
        historical_periods = ["2023"]
        forecast_periods = ["2024"]
        forecast_configs = {"test": "config"}

        def adjustment_filter_func(x):
            return True

        writer.write(
            mock_graph,
            statement_structure=mock_structure,
            historical_periods=historical_periods,
            forecast_periods=forecast_periods,
            forecast_configs=forecast_configs,
            adjustment_filter=adjustment_filter_func,
        )

        # Verify renderer called with correct periods
        mock_renderer_instance.render_structure.assert_called_once()
        call_args = mock_renderer_instance.render_structure.call_args
        assert call_args[1]["historical_periods"] == set(historical_periods)
        assert call_args[1]["forecast_periods"] == set(forecast_periods)

        # Verify formatter called with periods
        mock_formatter_instance.format_table.assert_called_once()
        formatter_call_args = mock_formatter_instance.format_table.call_args
        assert formatter_call_args[1]["historical_periods"] == historical_periods
        assert formatter_call_args[1]["forecast_periods"] == forecast_periods

        # Verify notes builder called with configs
        mock_notes_instance.build_notes.assert_called_once_with(
            graph=mock_graph,
            forecast_configs=forecast_configs,
            adjustment_filter=adjustment_filter_func,
        )

    def test_write_with_exception_handling(self):
        """Test write handles exceptions properly."""
        writer = MarkdownWriter()
        mock_graph = Mock(spec=Graph)
        mock_structure = Mock(spec=StatementStructure)

        # Mock renderer to raise an exception
        with patch(
            "fin_statement_model.io.formats.markdown_writer.MarkdownStatementRenderer"
        ) as mock_renderer:
            mock_renderer.side_effect = Exception("Test error")

            with pytest.raises(WriteError) as exc_info:
                writer.write(mock_graph, statement_structure=mock_structure)

            assert "Failed to generate Markdown table" in str(exc_info.value)
            assert "Test error" in str(exc_info.value)

    def test_write_with_not_implemented_error(self):
        """Test write handles NotImplementedError specifically."""
        writer = MarkdownWriter()
        mock_graph = Mock(spec=Graph)
        mock_structure = Mock(spec=StatementStructure)

        # Mock renderer to raise NotImplementedError
        with patch(
            "fin_statement_model.io.formats.markdown_writer.MarkdownStatementRenderer"
        ) as mock_renderer:
            mock_renderer.side_effect = NotImplementedError(
                "Graph traversal not implemented"
            )

            with pytest.raises(WriteError) as exc_info:
                writer.write(mock_graph, statement_structure=mock_structure)

            assert "Markdown writer requires graph traversal logic" in str(
                exc_info.value
            )

    def test_write_target_is_ignored(self):
        """Test that the target parameter is ignored by the writer."""
        writer = MarkdownWriter()
        mock_graph = Mock(spec=Graph)
        mock_structure = Mock(spec=StatementStructure)

        with patch(
            "fin_statement_model.io.formats.markdown_writer.MarkdownStatementRenderer"
        ) as mock_renderer:
            mock_renderer_instance = Mock()
            mock_renderer.return_value = mock_renderer_instance
            mock_renderer_instance.render_structure.return_value = []
            mock_renderer_instance.periods = []

            # Pass a target, but it should be ignored
            result = writer.write(
                mock_graph,
                target="should_be_ignored.md",
                statement_structure=mock_structure,
            )

            # Result should still be a string, not written to file
            assert isinstance(result, str)
