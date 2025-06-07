"""Formatter for converting statement items to markdown table format."""

import logging
from typing import Any, Optional, Union

from fin_statement_model.io.formats.markdown.models import MarkdownStatementItem

logger = logging.getLogger(__name__)


class MarkdownTableFormatter:
    """Formats statement items into markdown table format.

    This class handles the table layout, column width calculations,
    and markdown-specific formatting like bold text for subtotals.
    """

    def __init__(self, indent_spaces: int = 4):
        """Initialize the formatter.

        Args:
            indent_spaces: Number of spaces per indentation level.
        """
        self.indent_spaces = indent_spaces

    def format_table(
        self,
        items: list[MarkdownStatementItem],
        periods: list[str],
        historical_periods: Optional[list[str]] = None,
        forecast_periods: Optional[list[str]] = None,
    ) -> list[str]:
        """Format items into markdown table lines.

        Args:
            items: List of MarkdownStatementItem objects to format.
            periods: List of all periods in order.
            historical_periods: List of historical period names.
            forecast_periods: List of forecast period names.

        Returns:
            List of strings representing the markdown table lines.
        """
        if not items:
            logger.warning("No items to format into table")
            return []

        # Convert to sets for faster lookup
        historical_set = set(historical_periods or [])
        forecast_set = set(forecast_periods or [])

        # Calculate column widths and format data
        max_desc_width, period_max_widths, formatted_lines = self._calculate_widths_and_format(
            items, periods
        )

        # Build the table
        output_lines = []

        # Build header row
        header_parts = ["Description".ljust(max_desc_width)]
        for period in periods:
            period_label = period
            if period in historical_set:
                period_label += " (H)"
            elif period in forecast_set:
                period_label += " (F)"
            header_parts.append(period_label.rjust(period_max_widths[period]))

        output_lines.append(f"| {' | '.join(header_parts)} |")

        # Add separator line
        separator_parts = ["-" * max_desc_width]
        separator_parts.extend("-" * period_max_widths[period] for period in periods)
        output_lines.append(f"| {' | '.join(separator_parts)} |")

        # Build data rows
        for line_data in formatted_lines:
            row_parts = [line_data["name"].ljust(max_desc_width)]
            for period in periods:
                value = line_data["values"].get(period, "")
                row_parts.append(value.rjust(period_max_widths[period]))
            output_lines.append(f"| {' | '.join(row_parts)} |")

        return output_lines

    def _calculate_widths_and_format(
        self, items: list[MarkdownStatementItem], periods: list[str]
    ) -> tuple[int, dict[str, int], list[dict[str, Any]]]:
        """Calculate column widths and format all data.

        Args:
            items: List of items to format.
            periods: List of periods.

        Returns:
            Tuple of (max_desc_width, period_max_widths, formatted_lines).
        """
        max_desc_width = 0
        period_max_widths = {p: 0 for p in periods}
        formatted_lines = []

        # First pass: format data and calculate max widths
        for item in items:
            indent = " " * (item["level"] * self.indent_spaces)
            name = f"{indent}{item['name']}"
            is_subtotal = item["is_subtotal"]
            is_contra = item.get("is_contra", False)
            values_formatted = {}

            # Apply markdown formatting for subtotals
            if is_subtotal:
                name = f"**{name}**"

            # Apply contra formatting if needed
            if is_contra:
                name = f"_{name}_"  # Italic for contra items

            max_desc_width = max(max_desc_width, len(name))

            # Format values for each period
            for period in periods:
                raw_value = item["values"].get(period)
                value_str = self._format_value(raw_value, item)

                # Apply markdown formatting for subtotals
                if is_subtotal:
                    value_str = f"**{value_str}**"
                elif is_contra:
                    value_str = f"_{value_str}_"  # Italic for contra items

                values_formatted[period] = value_str
                period_max_widths[period] = max(period_max_widths[period], len(value_str))

            formatted_lines.append(
                {
                    "name": name,
                    "values": values_formatted,
                    "is_subtotal": is_subtotal,
                    "is_contra": is_contra,
                }
            )

        return max_desc_width, period_max_widths, formatted_lines

    def _format_value(
        self, value: Union[float, int, str, None], item: MarkdownStatementItem
    ) -> str:
        """Format a single value for display in the table.

        Args:
            value: The value to format.
            item: The item containing formatting information.

        Returns:
            Formatted string representation of the value.
        """
        if value is None:
            return ""

        if isinstance(value, str):
            # Keep error strings and other text as-is
            return value

        if isinstance(value, float | int):
            # Use custom format if specified
            display_format = item.get("display_format")
            if display_format:
                try:
                    return format(value, display_format)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid display format '{display_format}': {e}")
                    # Fall back to default formatting

            # Default number formatting
            if isinstance(value, float):
                return f"{value:,.2f}"
            else:
                return f"{value:,}"

        # Fallback for any other type
        return str(value)
