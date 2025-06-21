"""Markdown formatting utilities (moved from io.formats.markdown)."""

from __future__ import annotations

# Re-export from legacy location to keep diff small during move
# from fin_statement_model.io.formats.markdown.formatter import MarkdownTableFormatter as _Formatter
# from fin_statement_model.io.formats.markdown.renderer import MarkdownStatementRenderer as _Renderer
# from fin_statement_model.io.formats.markdown.notes import MarkdownNotesBuilder as _Notes
#
# MarkdownTableFormatter = _Formatter
# MarkdownStatementRenderer = _Renderer
# MarkdownNotesBuilder = _Notes

from .formatter import MarkdownTableFormatter
from .renderer import MarkdownStatementRenderer
from .notes import MarkdownNotesBuilder

__all__ = [
    "MarkdownTableFormatter",
    "MarkdownStatementRenderer",
    "MarkdownNotesBuilder",
]
