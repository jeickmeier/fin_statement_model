# Composite namespace for IO mixins.

"""Composite namespace for IO mixins.

This sub-package contains the building-block mixins shared by all I/O
readers and writers.  The original monolithic *mixins.py* has been split
into smaller thematic modules to comply with the ≤300-LOC rule and to
improve discoverability.  External import paths remain stable::

    from fin_statement_model.io.core.mixins import FileBasedReader, handle_read_errors

⚠️  **MRO Guidance**
    Concrete readers *must* inherit in the following order so helpers are
    available where expected:

    1. ``MappingAwareMixin`` – provides `_get_mapping()` which relies on…
    2. ``ConfigurationMixin`` – supplies `get_config_value()`
    3. Your reader class or `DataFrameReaderBase`

Placing `ConfigurationMixin` before `MappingAwareMixin` will still work at
runtime but breaks static type-checking – follow the order above to avoid
surprises.

The transitional private module ``_legacy_mixins`` has been removed.
Import it directly **no longer works**.
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
    "BaseTableWriter",
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
