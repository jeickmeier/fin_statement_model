"""Data models for markdown formatting (relocated from io.formats.markdown.models)."""

from typing import TypedDict


class MarkdownStatementItem(TypedDict):
    """Representation of a financial statement line item for Markdown output."""

    name: str
    values: dict[str, float | int | str | None]
    level: int
    is_subtotal: bool
    sign_convention: int  # 1 for normal, -1 for inverted
    display_format: str | None
    units: str | None
    display_scale_factor: float
    is_contra: bool
