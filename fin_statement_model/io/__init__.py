"""Input/Output components for the Financial Statement Model.

This package provides a unified interface for reading and writing financial model
data from/to various formats using a registry-based approach.

The subpackages are organized as follows:
- `core`: Contains the foundational components, including base classes, the
  handler registry, and shared mixins.
- `formats`: Provides concrete reader and writer implementations for specific
  data formats (e.g., CSV, Excel, API).
- `adjustments`, `graph`, `statements`: Offer specialized, high-level I/O
  functions for specific use cases.
"""

import logging

from .core import (
    DataReader,
    DataWriter,
    get_reader,
    get_writer,
    list_readers,
    list_writers,
    read_data,
    write_data,
)
from .exceptions import IOError, ReadError, WriteError, FormatNotSupportedError
from . import formats  # noqa: F401

# Import convenient helpers from new sub-packages (adjustments, graph, statements)
from .graph import import_from_cells  # noqa: F401
from .adjustments import (
    load_adjustments_from_excel,
    export_adjustments_to_excel,
)
from .statements import (
    list_available_builtin_configs,
    write_statement_to_excel,
    write_statement_to_json,
)

# Configure logging for the io package
logger = logging.getLogger(__name__)

# --- Public API ---

__all__ = [
    # Base classes
    "DataReader",
    "DataWriter",
    # Exceptions
    "FormatNotSupportedError",
    "IOError",
    "ReadError",
    "WriteError",
    # Specialized functions
    "export_adjustments_to_excel",
    "import_from_cells",
    "list_available_builtin_configs",
    "load_adjustments_from_excel",
    "write_statement_to_excel",
    "write_statement_to_json",
    # Registry functions
    "get_reader",
    "get_writer",
    "list_readers",
    "list_writers",
    # Facade functions
    "read_data",
    "write_data",
]
