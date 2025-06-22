"""Tests for the markdown models."""

from fin_statement_model.statements.formatting.markdown.models import (
    MarkdownStatementItem,
)


class TestMarkdownStatementItem:
    """Test cases for MarkdownStatementItem TypedDict."""

    def test_create_basic_item(self):
        """Test creating a basic MarkdownStatementItem."""
        item = MarkdownStatementItem(
            name="Revenue",
            values={"2023": 1000.0, "2024": 1100.0},
            level=0,
            is_subtotal=False,
            sign_convention=1,
            display_format=None,
            units=None,
            display_scale_factor=1.0,
            is_contra=False,
        )

        assert item["name"] == "Revenue"
        assert item["values"]["2023"] == 1000.0
        assert item["values"]["2024"] == 1100.0
        assert item["level"] == 0
        assert item["is_subtotal"] is False
        assert item["sign_convention"] == 1
        assert item["display_format"] is None
        assert item["units"] is None
        assert item["display_scale_factor"] == 1.0
        assert item["is_contra"] is False

    def test_create_subtotal_item(self):
        """Test creating a subtotal item with formatting."""
        item = MarkdownStatementItem(
            name="Total Revenue",
            values={"2023": 5000.0},
            level=1,
            is_subtotal=True,
            sign_convention=-1,
            display_format=",.0f",
            units="USD thousands",
            display_scale_factor=0.001,
            is_contra=False,
        )

        assert item["name"] == "Total Revenue"
        assert item["is_subtotal"] is True
        assert item["sign_convention"] == -1
        assert item["display_format"] == ",.0f"
        assert item["units"] == "USD thousands"
        assert item["display_scale_factor"] == 0.001

    def test_create_contra_item(self):
        """Test creating a contra item."""
        item = MarkdownStatementItem(
            name="Sales Returns",
            values={"2023": -100.0},
            level=1,
            is_subtotal=False,
            sign_convention=1,
            display_format=None,
            units=None,
            display_scale_factor=1.0,
            is_contra=True,
        )

        assert item["name"] == "Sales Returns"
        assert item["is_contra"] is True
        assert item["values"]["2023"] == -100.0

    def test_values_with_mixed_types(self):
        """Test item with mixed value types."""
        item = MarkdownStatementItem(
            name="Test Item",
            values={
                "2021": 100,  # int
                "2022": 200.5,  # float
                "2023": "N/A",  # string
                "2024": None,  # None
            },
            level=0,
            is_subtotal=False,
            sign_convention=1,
            display_format=None,
            units=None,
            display_scale_factor=1.0,
            is_contra=False,
        )

        assert isinstance(item["values"]["2021"], int)
        assert isinstance(item["values"]["2022"], float)
        assert isinstance(item["values"]["2023"], str)
        assert item["values"]["2024"] is None

    def test_item_as_dict(self):
        """Test that MarkdownStatementItem behaves as a dict."""
        item = MarkdownStatementItem(
            name="Test",
            values={},
            level=0,
            is_subtotal=False,
            sign_convention=1,
            display_format=None,
            units=None,
            display_scale_factor=1.0,
            is_contra=False,
        )

        # Should be able to access like a dict
        assert "name" in item
        assert len(item) == 9  # All fields

        # Should be able to iterate
        keys = list(item.keys())
        assert "name" in keys
        assert "values" in keys
        assert "level" in keys

    def test_optional_fields(self):
        """Test that optional fields can be None."""
        item = MarkdownStatementItem(
            name="Test",
            values={},
            level=0,
            is_subtotal=False,
            sign_convention=1,
            display_format=None,  # Optional
            units=None,  # Optional
            display_scale_factor=1.0,
            is_contra=False,
        )

        assert item["display_format"] is None
        assert item["units"] is None
