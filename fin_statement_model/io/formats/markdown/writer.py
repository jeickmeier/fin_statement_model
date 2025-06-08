"""Writes a financial statement graph to a Markdown table."""

import logging
from typing import Any, Optional, TypedDict, Union

from fin_statement_model.core.graph import Graph
from fin_statement_model.io.core.base import DataWriter
from fin_statement_model.io.config.models import BaseWriterConfig
from fin_statement_model.io.exceptions import WriteError
from fin_statement_model.io.core.registry import register_writer
from fin_statement_model.statements.structure import StatementStructure
from fin_statement_model.io.formats.markdown.renderer import MarkdownStatementRenderer
from fin_statement_model.io.formats.markdown.formatter import MarkdownTableFormatter
from fin_statement_model.io.formats.markdown.notes import MarkdownNotesBuilder

logger = logging.getLogger(__name__)


class MarkdownWriterConfig(BaseWriterConfig):
    """Configuration specific to the Markdown writer."""

    indent_spaces: int = 4  # Number of spaces per indentation level
    # Add other Markdown-specific config options here if needed


# Legacy structure for backward compatibility
class StatementItem(TypedDict):
    """Represents a line item with its values for Markdown output."""

    name: str
    # value: Union[float, int, str, None] # Replaced single value
    values: dict[str, Union[float, int, str, None]]  # Values per period
    level: int
    is_subtotal: bool  # Indicates if the row is a subtotal or section header


@register_writer("markdown")
class MarkdownWriter(DataWriter):
    """Writes a financial statement structure to a Markdown table."""

    def __init__(self, config: Optional[MarkdownWriterConfig] = None):
        """Initializes the MarkdownWriter."""
        self.config = config or MarkdownWriterConfig(
            format_type="markdown", target=None
        )
        logger.debug(f"Initialized MarkdownWriter with config: {self.config}")

    def _format_value(self, value: Union[float, int, str, None]) -> str:
        """Formats the value for display in the table."""
        if value is None:
            return ""
        if isinstance(value, float | int):
            # Basic number formatting, could be enhanced (e.g., commas)
            return f"{value:,.2f}" if isinstance(value, float) else str(value)
        return str(value)

    def write(self, graph: Graph, target: Any = None, **kwargs: Any) -> str:
        """Write financial statement to markdown.

        Args:
            graph: The Graph object containing the financial data.
            target: Ignored by this writer (returns string).
            **kwargs: Additional options including:
                - statement_structure: The StatementStructure to render

        Returns:
            String containing the formatted statement in Markdown.

        Raises:
            WriteError: If 'statement_structure' is not provided.
        """
        logger.info(
            f"Writing graph to Markdown format (target ignored: {target}) using kwargs: {kwargs.keys()}"
        )

        try:
            statement_structure = kwargs.get("statement_structure")
            if statement_structure is None:
                raise WriteError("Must provide 'statement_structure' argument.")
            filtered_kwargs = {
                k: v for k, v in kwargs.items() if k != "statement_structure"
            }
            return self._write_with_structure(
                graph, statement_structure, **filtered_kwargs
            )
        except NotImplementedError as nie:
            logger.exception("Markdown write failed")
            raise WriteError(
                message=f"Markdown writer requires graph traversal logic: {nie}",
                target=target,
                writer_type="markdown",
                original_error=nie,
            ) from nie
        except Exception as e:
            logger.exception("Error writing Markdown for graph", exc_info=True)
            raise WriteError(
                message=f"Failed to generate Markdown table: {e}",
                target=target,
                writer_type="markdown",
                original_error=e,
            ) from e

    def _write_with_structure(
        self, graph: Graph, statement_structure: StatementStructure, **kwargs: Any
    ) -> str:
        """Write using the new StatementStructure approach.

        Args:
            graph: The Graph object containing financial data.
            statement_structure: The StatementStructure to render.
            **kwargs: Additional options.

        Returns:
            Formatted markdown string.
        """
        # Use renderer to process structure
        renderer = MarkdownStatementRenderer(graph, self.config.indent_spaces)
        items = renderer.render_structure(
            statement_structure,
            historical_periods=set(kwargs.get("historical_periods", [])),
            forecast_periods=set(kwargs.get("forecast_periods", [])),
        )

        if not items:
            logger.warning("No statement items generated from structure.")
            return ""

        # Format into markdown table
        formatter = MarkdownTableFormatter(self.config.indent_spaces)
        table_lines = formatter.format_table(
            items,
            periods=renderer.periods,
            historical_periods=kwargs.get("historical_periods"),
            forecast_periods=kwargs.get("forecast_periods"),
        )

        # Add notes sections
        notes_builder = MarkdownNotesBuilder()
        notes_lines = notes_builder.build_notes(
            graph=graph,
            forecast_configs=kwargs.get("forecast_configs"),
            adjustment_filter=kwargs.get("adjustment_filter"),
        )

        return "\n".join(table_lines + notes_lines)
