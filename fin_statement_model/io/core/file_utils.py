"""fin_statement_model.io.core.file_utils

Filesystem-related helper utilities shared across IO readers.

These helpers were previously duplicated across multiple reader
implementations (`CsvReader`, `ExcelReader`, `_FileValidationMixin`, …).
Centralising them avoids copy-paste and keeps behaviour consistent.

All helpers raise :class:`fin_statement_model.io.exceptions.ReadError`
for recoverable user-facing errors (missing file, unsupported
extension).  Callers can optionally supply the *reader_type* to improve
error messages.
"""

from __future__ import annotations

import os
from typing import Tuple

from fin_statement_model.io.exceptions import ReadError

__all__ = [
    "validate_file_exists",
    "validate_file_extension",
]


def _format_reader(reader_type: str | None) -> str:
    """Return a reader type string suitable for ReadError."""
    return reader_type or "FileReader"


def validate_file_exists(path: str, *, reader_type: str | None = None) -> None:
    """Ensure *path* points to an existing file.

    Args:
        path: File path to validate.
        reader_type: Optional reader type for :class:`ReadError` context.

    Raises:
        ReadError: If *path* does not exist on the filesystem.
    """
    if not os.path.exists(path):
        raise ReadError(
            f"File not found: {path}",
            source=path,
            reader_type=_format_reader(reader_type),
        )


def validate_file_extension(
    path: str,
    valid_extensions: Tuple[str, ...] | None,
    *,
    reader_type: str | None = None,
) -> None:
    """Validate that *path* ends with one of *valid_extensions*.

    An empty or *None* *valid_extensions* tuple disables the check – this
    supports readers that do not restrict extensions.

    Args:
        path: File path to validate.
        valid_extensions: Tuple of allowed extensions (case-insensitive). If
            ``None`` or empty, the function returns immediately.
        reader_type: Optional reader type for :class:`ReadError` context.

    Raises:
        ReadError: If the extension of *path* is not in *valid_extensions*.
    """
    if not valid_extensions:
        return

    if not path.lower().endswith(valid_extensions):
        raise ReadError(
            (
                "Invalid file extension. Expected one of "
                f"{valid_extensions}, got '{os.path.splitext(path)[1]}'"
            ),
            source=path,
            reader_type=_format_reader(reader_type),
        )
