"""Export service for financial statements.

Encapsulates export of formatted statements to various file formats.
"""

from typing import Any

from fin_statement_model.io.exceptions import WriteError
from fin_statement_model.statements.errors import StatementError

__all__ = ["ExportService"]


class ExportService:
    """Service to export formatted statements to files."""

    def __init__(self, manager: Any) -> None:
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
            WriteError: If writing the file fails.
        """
        try:
            df = self.manager.format_statement(statement_id, format_type="dataframe", **fmt_kwargs)
            df.to_excel(file_path, index=False)
        except StatementError as e:
            # Wrap statement lookup issues in WriteError for consistency
            raise WriteError(
                message="Failed to export statement",
                target=file_path,
                writer_type="excel",
                original_error=e,
            ) from e
        except Exception as e:
            raise WriteError(
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
            WriteError: If writing the file fails.
        """
        try:
            df = self.manager.format_statement(statement_id, format_type="dataframe", **fmt_kwargs)
            df.to_json(file_path, orient=orient)
        except StatementError as e:
            # Wrap statement lookup issues in WriteError for consistency
            raise WriteError(
                message="Failed to export statement",
                target=file_path,
                writer_type="json",
                original_error=e,
            ) from e
        except Exception as e:
            raise WriteError(
                message="Failed to export statement to JSON",
                target=file_path,
                format_type="json",
                original_error=e,
            ) from e
