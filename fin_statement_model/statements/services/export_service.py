"""Export service for financial statements.

Encapsulates export of formatted statements to various file formats.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fin_statement_model.statements.manager import StatementManager

from fin_statement_model.statements.errors import StatementError
from fin_statement_model.core.errors import ExportError

__all__ = ["ExportService"]


class ExportService:
    """Service to export formatted statements to files."""

    def __init__(self, manager: StatementManager) -> None:
        """Initialize the ExportService.

        Args:
            manager: The StatementManager instance used for formatting.
        """
        self.manager = manager

    def to_excel(self, statement_id: str, file_path: str, **fmt_kwargs: dict[str, object]) -> None:
        """Export a statement to an Excel file.

        Args:
            statement_id: The ID of the statement to export.
            file_path: Path to save the Excel file.
            **fmt_kwargs: Additional arguments passed to the formatter.

        Raises:
            StatementError: If the statement ID is invalid.
            ExportError: If writing the file fails.
        """
        try:
            df = self.manager.format_statement(statement_id, format_type="dataframe", **fmt_kwargs)
            df.to_excel(file_path, index=False)
        except StatementError:
            # Propagate statement lookup issues
            raise
        except Exception as e:
            raise ExportError(
                message="Failed to export statement to Excel",
                target=file_path,
                format_type="excel",
                original_error=e,
            ) from e

    def to_json(
        self,
        statement_id: str,
        file_path: str,
        orient: str = "columns",
        **fmt_kwargs: dict[str, object],
    ) -> None:
        """Export a statement to a JSON file.

        Args:
            statement_id: The ID of the statement to export.
            file_path: Path to save the JSON file.
            orient: JSON orientation (default "columns").
            **fmt_kwargs: Additional arguments passed to the formatter.

        Raises:
            StatementError: If the statement ID is invalid.
            ExportError: If writing the file fails.
        """
        try:
            df = self.manager.format_statement(statement_id, format_type="dataframe", **fmt_kwargs)
            df.to_json(file_path, orient=orient)
        except StatementError:
            raise
        except Exception as e:
            raise ExportError(
                message="Failed to export statement to JSON",
                target=file_path,
                format_type="json",
                original_error=e,
            ) from e
