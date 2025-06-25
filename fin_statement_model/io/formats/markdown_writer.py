"""Data writer for exporting financial statements to Markdown format.

This module provides the `MarkdownWriter`, a `DataWriter` implementation that
renders a `StatementStructure` into a formatted Markdown table. It is designed
to produce human-readable reports of financial statements.
"""

import logging

from fin_statement_model.io.config.models import MarkdownWriterConfig
from fin_statement_model.io.core.base import DataWriter
from fin_statement_model.io.core.registry import register_writer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Markdown writer removed
# ---------------------------------------------------------------------------
# The previous implementation of ``MarkdownWriter`` depended on the now
# deleted ``fin_statement_model.statements`` package.  Rather than attempting
# to preserve partial functionality, we register a *stub* writer that raises a
# clear ``ImportError`` upon instantiation.  This keeps the public registry
# stable - calls to ``get_writer('markdown')`` will still resolve - while
# signalling unambiguously that Markdown export is currently unsupported.
# ---------------------------------------------------------------------------


@register_writer("markdown", schema=MarkdownWriterConfig)
class MarkdownWriter(DataWriter):
    """Stub Markdown writer.

    Attempts to instantiate this class will raise ``ImportError`` because the
    underlying implementation was removed together with the legacy statements
    module.  The class remains registered to avoid breaking dynamic plugin
    discovery mechanisms that expect a writer named ``'markdown'``.
    """

    def __init__(self, *_: object, **__: object) -> None:
        """Initialize stub and immediately raise ``ImportError``.

        The actual Markdown exporting capabilities have been removed together
        with the legacy ``fin_statement_model.statements`` package.  A stub is
        kept so that dynamic plugin discovery via :pyfunc:`~fin_statement_model.io.core.get_writer`
        continues to resolve the ``'markdown'`` identifier without breaking
        existing user code.  Instantiating the stub unambiguously signals that
        the functionality is currently unavailable.
        """
        message = (
            "MarkdownWriter has been removed because its implementation relied on the "
            "deprecated 'fin_statement_model.statements' package. Markdown export will "
            "be re-introduced in a future release."
        )
        logger.error(message)
        raise ImportError(message)
