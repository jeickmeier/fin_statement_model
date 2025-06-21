"""File-based reader helper class extracted from legacy mixins.

Provides shared validation helpers (`validate_file_exists`,
`validate_file_extension`) and declares the abstract `read()` method that
concrete file readers (CSV, Excel, etc.) implement.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any

from fin_statement_model.core.graph import Graph
from fin_statement_model.io.exceptions import ReadError
from fin_statement_model.io.core.base import DataReader


class FileBasedReader(DataReader, ABC):
    """Base class for readers that ingest data from the filesystem."""

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    def validate_file_exists(self, path: str) -> None:  # noqa: D401
        if not os.path.exists(path):
            raise ReadError(
                f"File not found: {path}",
                source=path,
                reader_type=self.__class__.__name__,
            )

    def validate_file_extension(
        self, path: str, valid_extensions: tuple[str, ...]
    ) -> None:  # noqa: D401
        if not path.lower().endswith(valid_extensions):
            raise ReadError(
                f"Invalid file extension. Expected one of {valid_extensions}, got '{os.path.splitext(path)[1]}'",
                source=path,
                reader_type=self.__class__.__name__,
            )

    # ------------------------------------------------------------------
    # Abstract API
    # ------------------------------------------------------------------
    @abstractmethod
    def read(self, source: str, **kwargs: Any) -> Graph:  # noqa: D401
        """Subclasses must implement file reading logic and return a Graph."""
