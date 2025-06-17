"""Tests for the MarkdownTableFormatter class."""

from fin_statement_model.io.formats.markdown.formatter import MarkdownTableFormatter
from fin_statement_model.io.formats.markdown.models import MarkdownStatementItem


class TestMarkdownTableFormatter:
    """Test cases for MarkdownTableFormatter."""

    def test_init(self):
        """Test formatter initialization."""
        formatter = MarkdownTableFormatter()
        assert formatter.indent_spaces == 4

        formatter = MarkdownTableFormatter(indent_spaces=2)
        assert formatter.indent_spaces == 2

    def test_format_table_empty_items(self):
        """Test formatting with empty items list."""
        formatter = MarkdownTableFormatter()
        result = formatter.format_table([], ["2023", "2024"])
        assert result == []

    def test_format_table_basic(self):
        """Test basic table formatting."""
        formatter = MarkdownTableFormatter()
        items = [
            MarkdownStatementItem(
                name="Revenue",
                values={"2023": 1000.0, "2024": 1100.0},
                level=0,
                is_subtotal=False,
            ),
            MarkdownStatementItem(
                name="Cost of Goods Sold",
                values={"2023": 600.0, "2024": 650.0},
                level=0,
                is_subtotal=False,
            ),
            MarkdownStatementItem(
                name="Gross Profit",
                values={"2023": 400.0, "2024": 450.0},
                level=0,
                is_subtotal=True,
            ),
        ]
        periods = ["2023", "2024"]

        result = formatter.format_table(items, periods)

        assert len(result) > 3  # Header, separator, and data rows
        assert "Description" in result[0]
        assert "2023" in result[0]
        assert "2024" in result[0]
        assert "Revenue" in result[2]
        assert "**Gross Profit**" in result[4]  # Subtotal should be bold

    def test_format_table_with_historical_forecast_periods(self):
        """Test formatting with historical and forecast period markers."""
        formatter = MarkdownTableFormatter()
        items = [
            MarkdownStatementItem(
                name="Revenue",
                values={"2023": 1000.0, "2024": 1100.0, "2025": 1200.0},
                level=0,
                is_subtotal=False,
            )
        ]
        periods = ["2023", "2024", "2025"]
        historical_periods = ["2023", "2024"]
        forecast_periods = ["2025"]

        result = formatter.format_table(
            items, periods, historical_periods, forecast_periods
        )

        header = result[0]
        assert "2023 (H)" in header
        assert "2024 (H)" in header
        assert "2025 (F)" in header

    def test_format_table_with_indentation(self):
        """Test formatting with indented items."""
        formatter = MarkdownTableFormatter(indent_spaces=4)
        items = [
            MarkdownStatementItem(
                name="Revenue",
                values={"2023": 1000.0},
                level=0,
                is_subtotal=False,
            ),
            MarkdownStatementItem(
                name="Product Sales",
                values={"2023": 800.0},
                level=1,
                is_subtotal=False,
            ),
            MarkdownStatementItem(
                name="Service Revenue",
                values={"2023": 200.0},
                level=1,
                is_subtotal=False,
            ),
        ]
        periods = ["2023"]

        result = formatter.format_table(items, periods)

        # Check indentation is applied
        for line in result:
            if "Product Sales" in line:
                assert "    Product Sales" in line  # 4 spaces indent
            if "Service Revenue" in line:
                assert "    Service Revenue" in line

    def test_format_table_with_contra_items(self):
        """Test formatting with contra items (should be italic)."""
        formatter = MarkdownTableFormatter()
        items = [
            MarkdownStatementItem(
                name="Gross Revenue",
                values={"2023": 1100.0},
                level=0,
                is_subtotal=False,
            ),
            MarkdownStatementItem(
                name="Sales Returns",
                values={"2023": -100.0},
                level=0,
                is_subtotal=False,
                is_contra=True,
            ),
            MarkdownStatementItem(
                name="Net Revenue",
                values={"2023": 1000.0},
                level=0,
                is_subtotal=True,
            ),
        ]
        periods = ["2023"]

        result = formatter.format_table(items, periods)

        # Contra item should be italic
        for line in result:
            if "Sales Returns" in line:
                assert "_Sales Returns_" in line

    def test_format_value_none(self):
        """Test formatting None values."""
        formatter = MarkdownTableFormatter()
        item = MarkdownStatementItem(name="Test", values={}, level=0, is_subtotal=False)
        result = formatter._format_value(None, item)
        assert result == ""

    def test_format_value_string(self):
        """Test formatting string values."""
        formatter = MarkdownTableFormatter()
        item = MarkdownStatementItem(name="Test", values={}, level=0, is_subtotal=False)
        result = formatter._format_value("N/A", item)
        assert result == "N/A"

    def test_format_value_with_custom_format(self):
        """Test formatting with custom display format."""
        formatter = MarkdownTableFormatter()
        item = MarkdownStatementItem(
            name="Test",
            values={},
            level=0,
            is_subtotal=False,
            display_format=".1%",
        )
        result = formatter._format_value(0.125, item)
        assert result == "12.5%"

    def test_format_value_invalid_custom_format(self):
        """Test formatting with invalid custom format falls back to default."""
        formatter = MarkdownTableFormatter()
        item = MarkdownStatementItem(
            name="Test",
            values={},
            level=0,
            is_subtotal=False,
            display_format="invalid_format",
        )
        result = formatter._format_value(1234.56, item)
        assert result == "1,234.56"  # Falls back to default

    def test_format_value_integer(self):
        """Test formatting integer values."""
        formatter = MarkdownTableFormatter()
        item = MarkdownStatementItem(name="Test", values={}, level=0, is_subtotal=False)
        result = formatter._format_value(1000000, item)
        assert result == "1,000,000"

    def test_format_value_float(self):
        """Test formatting float values."""
        formatter = MarkdownTableFormatter()
        item = MarkdownStatementItem(name="Test", values={}, level=0, is_subtotal=False)
        result = formatter._format_value(1234.567, item)
        assert result == "1,234.57"

    def test_calculate_widths_and_format(self):
        """Test width calculation and formatting logic."""
        formatter = MarkdownTableFormatter()
        items = [
            MarkdownStatementItem(
                name="Short",
                values={"2023": 100.0},
                level=0,
                is_subtotal=False,
            ),
            MarkdownStatementItem(
                name="Very Long Description Here",
                values={"2023": 1000000.0},
                level=0,
                is_subtotal=False,
            ),
        ]
        periods = ["2023"]

        max_desc_width, period_widths, formatted_lines = (
            formatter._calculate_widths_and_format(items, periods)
        )

        assert max_desc_width >= len("Very Long Description Here")
        assert period_widths["2023"] >= len("1,000,000.00")
        assert len(formatted_lines) == 2

    def test_format_table_mixed_value_types(self):
        """Test formatting with mixed value types."""
        formatter = MarkdownTableFormatter()
        items = [
            MarkdownStatementItem(
                name="Revenue",
                values={"2023": 1000.0, "2024": "N/A", "2025": None},
                level=0,
                is_subtotal=False,
            ),
        ]
        periods = ["2023", "2024", "2025"]

        result = formatter.format_table(items, periods)

        # Should handle all value types gracefully
        assert len(result) >= 3
        data_row = result[2]
        assert "1,000.00" in data_row
        assert "N/A" in data_row
        # None values should show as empty
