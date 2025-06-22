"""Formatter for converting statement items to markdown table format.

Moved from `io.formats.markdown.formatter`.
"""

from __future__ import annotations

import logging
from typing import Optional, Union, Any

from .models import MarkdownStatementItem  # updated path

logger = logging.getLogger(__name__)


class MarkdownTableFormatter:
    """Formats statement items into markdown table format."""

    def __init__(self, indent_spaces: int = 4):
        self.indent_spaces = indent_spaces

    def format_table(
        self,
        items: list[MarkdownStatementItem],
        periods: list[str],
        historical_periods: Optional[list[str]] = None,
        forecast_periods: Optional[list[str]] = None,
    ) -> list[str]:
        if not items:
            logger.warning("No items to format into table")
            return []
        hist_set = set(historical_periods or [])
        fc_set = set(forecast_periods or [])
        max_desc, period_widths, lines = self._calculate_widths_and_format(
            items, periods
        )
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
    ) -> tuple[int, dict[str, int], list[dict[str, Any]]]:  # noqa: D401
        max_desc = 0
        period_widths = {p: 0 for p in periods}
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
            formatted.append(
                {
                    "name": name,
                    "values": vals,
                    "is_subtotal": is_sub,
                    "is_contra": is_contra,
                }
            )
        return max_desc, period_widths, formatted

    def _format_value(
        self, value: Union[float, int, str, None], item: MarkdownStatementItem
    ) -> str:  # noqa: D401
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float)):
            fmt = item.get("display_format")
            if fmt:
                try:
                    return format(value, fmt)
                except Exception:  # noqa: BLE001
                    logger.warning("Invalid display_format '%s'", fmt)
            return f"{value:,.2f}" if isinstance(value, float) else f"{value:,}"
        return str(value)
