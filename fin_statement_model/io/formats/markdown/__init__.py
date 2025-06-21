"""Markdown format IO shim importing new markdown utilities.

This sub-package used to host all Markdown helpers. They have been
moved to ``fin_statement_model.statements.formatting.markdown`` but to
avoid breaking existing import paths (including tests) we re-export the
key symbols from the new location here.
"""

from fin_statement_model.statements.formatting.markdown import (
    MarkdownStatementRenderer,
    MarkdownTableFormatter,
    MarkdownNotesBuilder,
)

# Local writer (still resides in this package)
from .writer import MarkdownWriter

# Dataclass/TypedDict with no behaviour remains here for now.
from .models import MarkdownStatementItem

__all__ = [
    "MarkdownNotesBuilder",
    "MarkdownStatementItem",
    "MarkdownStatementRenderer",
    "MarkdownTableFormatter",
    "MarkdownWriter",
]
