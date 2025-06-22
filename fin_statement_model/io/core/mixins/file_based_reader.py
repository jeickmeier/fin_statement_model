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
    """Base class for readers that ingest data from the filesystem.

    Concrete subclasses **should** declare a class attribute
    ``file_extensions`` with the tuple of valid extensions, e.g.::

        class CsvReader(FileBasedReader):
            file_extensions = (".csv", ".txt")

    The :pymeth:`validate_file_extension` helper will automatically use this
    attribute when *valid_extensions* is omitted, removing the need for each
    reader to repeat the tuple in every call site.
    """

    # Default to *no* restriction – subclasses override
    file_extensions: tuple[str, ...] | None = None

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    def validate_file_exists(self, path: str) -> None:
        """Check if a file exists at the given path."""
        if not os.path.exists(path):
            raise ReadError(
                f"File not found: {path}",
                source=path,
                reader_type=self.__class__.__name__,
            )

    def validate_file_extension(
        self, path: str, valid_extensions: tuple[str, ...] | None = None
    ) -> None:
        """Validate *path* ends with an allowed extension.

        Args:
            path: The file path to validate.
            valid_extensions: **Rarely needed.**  By default the method falls
                back to the calling subclass' :pyattr:`file_extensions` class
                attribute.  Passing a tuple here is only required for edge
                cases (e.g. runtime-determined extensions) and should **not**
                be used from normal reader implementations – this keeps the
                extension contract declarative and discoverable at the class
                definition site.
        """
        exts = (
            valid_extensions if valid_extensions is not None else self.file_extensions
        )
        if not exts:
            # Nothing to validate against
            return
        if not path.lower().endswith(exts):
            raise ReadError(
                f"Invalid file extension. Expected one of {exts}, got '{os.path.splitext(path)[1]}'",
                source=path,
                reader_type=self.__class__.__name__,
            )

    # ------------------------------------------------------------------
    # Abstract API
    # ------------------------------------------------------------------
    @abstractmethod
    def read(self, source: str, **kwargs: Any) -> Graph:
        """Read data from a file and return a Graph.

        Subclasses must implement the file reading logic and return a `Graph`
        object populated with the data from the source file.

        Args:
            source: The path to the source file.
            **kwargs: Additional format-specific options for reading.

        Returns:
            A `Graph` object.
        """
        raise NotImplementedError
