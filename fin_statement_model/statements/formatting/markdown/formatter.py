"""Formatter for converting statement items to markdown table format.

Moved from `io.formats.markdown.formatter`.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import MarkdownStatementItem

logger = logging.getLogger(__name__)


class MarkdownTableFormatter:
    """Formats statement items into markdown table format."""

    def __init__(self, indent_spaces: int = 4):
        """Create a new table formatter.

        Args:
            indent_spaces: Number of spaces used per hierarchy level when
                indenting descriptions.
        """
        self.indent_spaces = indent_spaces

    def format_table(
        self,
        items: list[MarkdownStatementItem],
        periods: list[str],
        historical_periods: list[str] | None = None,
        forecast_periods: list[str] | None = None,
    ) -> list[str]:
        """Return a Markdown table representing *items* for *periods*.

        Args:
            items: Pre-rendered items coming from
                :class:`~fin_statement_model.statements.formatting.markdown.renderer.MarkdownStatementRenderer`.
            periods: Ordered list of period labels (columns).
            historical_periods: Sub-set of *periods* considered *historical* -
                appended with "(H)" in the header.
            forecast_periods: Sub-set of *periods* considered *forecast* -
                appended with "(F)" in the header.

        Returns:
            A list of strings where each element represents one Markdown table
            row (header, separator and data rows).
        """
        if not items:
            logger.warning("No items to format into table")
            return []
        hist_set = set(historical_periods or [])
        fc_set = set(forecast_periods or [])
        max_desc, period_widths, lines = self._calculate_widths_and_format(items, periods)
        out: list[str] = []
        header = ["Description".ljust(max_desc)]
        for p in periods:
            label = p + (" (H)" if p in hist_set else " (F)" if p in fc_set else "")
            header.append(label.rjust(period_widths[p]))
        out.append(f"| {' | '.join(header)} |")
        sep = ["-" * max_desc] + ["-" * period_widths[p] for p in periods]
        out.append(f"| {' | '.join(sep)} |")
        for ld in lines:
            row = [ld["name"].ljust(max_desc)]
            row.extend(ld["values"].get(p, "").rjust(period_widths[p]) for p in periods)
            out.append(f"| {' | '.join(row)} |")
        return out

    def _calculate_widths_and_format(
        self, items: list[MarkdownStatementItem], periods: list[str]
    ) -> tuple[int, dict[str, int], list[dict[str, Any]]]:
        max_desc = 0
        period_widths = dict.fromkeys(periods, 0)
        formatted = []
        for item in items:
            indent = " " * (item["level"] * self.indent_spaces)
            name = f"{indent}{item['name']}"
            is_sub = item["is_subtotal"]
            is_contra = item.get("is_contra", False)
            if is_sub:
                name = f"**{name}**"
            if is_contra:
                name = f"_{name}_"
            max_desc = max(max_desc, len(name))
            vals: dict[str, str] = {}
            for p in periods:
                raw = item["values"].get(p)
                v = self._format_value(raw, item)
                if is_sub:
                    v = f"**{v}**"
                elif is_contra:
                    v = f"_{v}_"
                vals[p] = v
                period_widths[p] = max(period_widths[p], len(v))
            formatted.append({
                "name": name,
                "values": vals,
                "is_subtotal": is_sub,
                "is_contra": is_contra,
            })
        return max_desc, period_widths, formatted

    def _format_value(self, value: float | int | str | None, item: MarkdownStatementItem) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, int | float):
            fmt = item.get("display_format")
            if fmt:
                try:
                    return format(value, fmt)
                except (ValueError, TypeError) as exc:
                    logger.warning("Invalid display_format '%s': %s", fmt, exc)
            return f"{value:,.2f}" if isinstance(value, float) else f"{value:,}"
        return str(value)
