"""Input/Output components for the Financial Statement Model.

This package provides a unified interface for reading and writing financial model
data from/to various formats using a registry-based approach.
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
    # Registry functions
    "get_reader",
    "get_writer",
    "import_from_cells",
    "list_available_builtin_configs",
    "list_readers",
    "list_writers",
    "load_adjustments_from_excel",
    # Facade functions
    "read_data",
    "write_data",
    "write_statement_to_excel",
    "write_statement_to_json",
]
