"""Custom exceptions for the I/O subpackage.

This module defines a hierarchy of custom exception classes for handling errors
that occur within the `fin_statement_model.io` package. All exceptions inherit
from a common `IOError` base class, which in turn inherits from the library's
top-level `FinancialModelError`.

This allows for granular error handling, where callers can catch specific
exceptions like `ReadError` or `FormatNotSupportedError`, or catch all I/O-related
errors by trapping `IOError`.
"""

# Use absolute import based on project structure
from fin_statement_model.core.errors import FinancialModelError


class IOError(FinancialModelError):
    """Base exception for all Input/Output errors in the IO package."""

    def __init__(
        self,
        message: str,
        source_or_target: str | None = None,
        format_type: str | None = None,
        original_error: Exception | None = None,
    ):
        """Initializes the IOError.

        Args:
            message: The base error message.
            source_or_target: Optional identifier for the source (read) or target (write).
            format_type: Optional name of the format or handler involved.
            original_error: Optional underlying exception that caused the failure.
        """
        self.source_or_target = source_or_target
        self.format_type = format_type
        self.original_error = original_error

        context = []
        if source_or_target:
            context.append(f"source/target '{source_or_target}'")
        if format_type:
            context.append(f"format '{format_type}'")

        full_message = f"{message} involving {' and '.join(context)}" if context else message

        if original_error:
            full_message = f"{full_message}: {original_error!s}"

        super().__init__(full_message)


class ReadError(IOError):
    """Exception raised specifically for errors during data read/import operations."""

    def __init__(
        self,
        message: str,
        source: str | None = None,
        reader_type: str | None = None,
        original_error: Exception | None = None,
    ):
        """Initializes the ReadError.

        Args:
            message: The base error message.
            source: Optional identifier for the data source (e.g., file path, URL).
            reader_type: Optional name of the reader class used for importing.
            original_error: Optional underlying exception that caused the import failure.
        """
        super().__init__(
            message=message,
            source_or_target=source,
            format_type=reader_type,
            original_error=original_error,
        )


class WriteError(IOError):
    """Exception raised specifically for errors during data write/export operations."""

    def __init__(
        self,
        message: str,
        target: str | None = None,
        writer_type: str | None = None,
        original_error: Exception | None = None,
    ):
        """Initializes the WriteError.

        Args:
            message: The base error message.
            target: Optional identifier for the export destination (e.g., file path).
            writer_type: Optional name of the writer class being used.
            original_error: Optional underlying exception that caused the export failure.
        """
        super().__init__(
            message=message,
            source_or_target=target,
            format_type=writer_type,
            original_error=original_error,
        )


class FormatNotSupportedError(IOError):
    """Exception raised when a requested IO format is not registered or supported."""

    def __init__(self, format_type: str, operation: str = "read/write"):
        """Initializes the FormatNotSupportedError.

        Args:
            format_type: The requested format identifier (e.g., 'excel', 'json').
            operation: The operation being attempted ('read' or 'write').
        """
        message = f"Format '{format_type}' is not supported for {operation} operations."
        super().__init__(message=message, format_type=format_type)
