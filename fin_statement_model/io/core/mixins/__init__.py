# Composite namespace for IO mixins.

"""Composite namespace for IO mixins.

This package progressively extracts the very large legacy *mixins.py* module
into smaller, thematic sub-modules.  External import paths remain stable::

    from fin_statement_model.io.core.mixins import FileBasedReader, handle_read_errors

Nothing outside *io.core.mixins* should import the private ``_legacy_mixins``
module directly – it exists only for the migration window.
"""

# Future imports must come immediately after the module docstring.
from __future__ import annotations

# Import error-handling decorators first
from .error_handlers import (
    handle_read_errors,  # noqa: F401 re-export
    handle_write_errors,  # noqa: F401 re-export
)

from .mapping import MappingAwareMixin  # noqa: F401 re-export
from .validation import (
    ValidationMixin,
    ValidationResultCollector,
)  # noqa: F401 re-export
from .configuration import ConfigurationMixin  # noqa: F401 re-export
from .file_based_reader import FileBasedReader  # noqa: F401 re-export
from .value_extraction import (
    ValueExtractionMixin,
    DataFrameBasedWriter,
)  # noqa: F401 re-export
from ..base_table_writer import BaseTableWriter  # noqa: F401 re-export

__all__: list[str] = [
    # Core building blocks re-exported from legacy mixins
    # (sorted roughly alphabetically for readability)
    "ConfigurationMixin",
    "DataFrameBasedWriter",
    "FileBasedReader",
    "MappingAwareMixin",
    "ValidationMixin",
    "ValidationResultCollector",
    "ValueExtractionMixin",
    # Newly split error-handling utilities
    "handle_read_errors",
    "handle_write_errors",
]
