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

# Import specialized functions for convenience
from .specialized import (
    import_from_cells,
    load_adjustments_from_excel,
    export_adjustments_to_excel,
    list_available_builtin_configs,
    read_builtin_statement_config,
    read_statement_config_from_path,
    read_statement_configs_from_directory,
    write_statement_to_excel,
    write_statement_to_json,
)

# Configure logging for the io package
logger = logging.getLogger(__name__)

# --- Trigger Registration ---
# Import format modules to ensure their @register decorators run.
# This makes them available in the registry when the io package is imported.
try:
    from . import formats  # noqa: F401
    from . import specialized  # noqa: F401
except ImportError:
    # This might happen during setup or if directories are missing
    logger.warning("Could not automatically import formats/specialized modules")


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
    "read_builtin_statement_config",
    # Facade functions
    "read_data",
    "read_statement_config_from_path",
    "read_statement_configs_from_directory",
    "write_data",
    "write_statement_to_excel",
    "write_statement_to_json",
]
