"""Format service for financial statements.

Delegates formatting requests to DataFrameFormatter or HtmlFormatter.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fin_statement_model.statements.services.formatting_service import (
    DataFrameFormatter,
    HtmlFormatter,
)
from fin_statement_model.statements.errors import StatementError

logger = logging.getLogger(__name__)

__all__ = ["FormatService"]

if TYPE_CHECKING:
    from fin_statement_model.statements.manager import StatementManager
    import pandas as pd


class FormatService:
    """Service to format statements into various formats."""

    def __init__(self, manager: StatementManager) -> None:
        """Initialize the FormatService.

        Args:
            manager: The StatementManager instance used for data and formatting.
        """
        self.manager = manager

    def format(
        self,
        statement_id: str,
        format_type: str = "dataframe",
        **fmt_kwargs: dict[str, object],
    ) -> pd.DataFrame | str:
        """Format a statement into the specified format.

        Args:
            statement_id: The ID of the statement to format.
            format_type: "dataframe" or "html".
            **fmt_kwargs: Additional arguments for the formatter.

        Returns:
            The formatted statement (DataFrame or HTML string).

        Raises:
            StatementError: If the statement ID is invalid or format_type is unsupported.
        """
        if format_type == "dataframe":
            return DataFrameFormatter(self.manager.get_statement(statement_id)).generate(
                self.manager.build_data_dictionary(statement_id), **fmt_kwargs
            )
        elif format_type == "html":
            return HtmlFormatter(self.manager.get_statement(statement_id)).generate(
                self.manager.build_data_dictionary(statement_id), **fmt_kwargs
            )
        else:
            raise StatementError(
                message=f"Unsupported format type: {format_type}",
                statement_id=statement_id,
            )
