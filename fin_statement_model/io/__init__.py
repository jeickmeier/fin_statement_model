"""Input/Output components for the Financial Statement Model.

This package provides a unified interface for reading and writing financial model
data from/to various formats using a registry-based approach.
"""

import logging
from typing import Union

from fin_statement_model.core.graph import Graph

from .base import DataReader, DataWriter
from .registry import get_reader, get_writer, list_readers, list_writers
from .exceptions import IOError, ReadError, WriteError, FormatNotSupportedError

# Configure logging for the io package
logger = logging.getLogger(__name__)

# --- Trigger Registration ---
# Import reader/writer modules to ensure their @register decorators run.
# This makes them available in the registry when the io package is imported.
try:
    from . import readers  # noqa: F401
    from . import writers  # noqa: F401
except ImportError:
    # This might happen during setup or if directories are missing
    logger.warning("Could not automatically import readers/writers")


# --- Facade Functions ---

# Define known keyword arguments for reader/writer initialization
# This helps separate config args from read/write specific args
_READER_INIT_KWARGS = {"api_key", "mapping_config"}
_WRITER_INIT_KWARGS = set()  # Currently no common writer init kwargs identified


def read_data(
    format_type: str, source: str, **kwargs: dict[str, Union[str, int, float, bool]]
) -> Graph:
    """Reads data from a source using the specified format.

    Keyword arguments passed to this function are divided between reader initialization
    (e.g., 'api_key', 'mapping_config') and the reader's `read()` method
    (e.g., 'sheet_name', 'statement_type'), based on predefined keys. Consult the
    specific reader's documentation for the exact parameters handled by each.

    Args:
        format_type (str): The format identifier (e.g., 'excel', 'csv', 'fmp', 'dict').
        source (str): The data source (e.g., file path, ticker symbol, dict, DataFrame).
        **kwargs: Additional keyword arguments. Arguments like 'api_key' or
                  'mapping_config' might be used to initialize the reader,
                  while others (e.g., 'sheet_name', 'statement_type') are passed
                  to the reader's `read()` method.

    Returns:
        Graph: A new Graph object populated with the read data.

    Raises:
        ReadError: If reading fails.
        FormatNotSupportedError: If the format_type is not registered.
        Exception: Other errors during reader initialization or reading.
    """
    logger.info(
        f"Attempting to read data using format '{format_type}' from source type '{type(source).__name__}'"
    )

    # Separate kwargs for init vs read
    init_kwargs = {k: v for k, v in kwargs.items() if k in _READER_INIT_KWARGS}
    read_kwargs = {k: v for k, v in kwargs.items() if k not in _READER_INIT_KWARGS}

    try:
        reader = get_reader(format_type, **init_kwargs)  # Pass only init kwargs
        return reader.read(source, **read_kwargs)  # Pass remaining kwargs to read
    except (IOError, FormatNotSupportedError):
        logger.exception("IO Error reading data")
        raise  # Re-raise specific IO errors
    except Exception as e:
        logger.exception(f"Unexpected error reading data with format '{format_type}'")
        # Wrap unexpected errors in ReadError for consistency?
        raise ReadError(
            "Unexpected error during read",
            source=str(source),
            reader_type=format_type,
            original_error=e,
        ) from e


def write_data(
    format_type: str,
    graph: Graph,
    target: object,
    **kwargs: dict[str, Union[str, int, float, bool]],
) -> object:
    """Writes graph data to a target using the specified format.

    Keyword arguments passed to this function are divided between writer initialization
    options and the writer's `write()` method, based on predefined keys. Consult the
    specific writer's documentation for the exact parameters handled by each.

    Args:
        format_type (str): The format identifier (e.g., 'excel', 'dataframe', 'dict').
        graph (Graph): The graph object containing data to write.
        target (object): The destination target (e.g., file path). Specific writers
                          might ignore this if they return data (like DataFrameWriter).
        **kwargs: Additional keyword arguments passed to the specific writer's
                  `write()` method (e.g., `sheet_name` for excel).

    Returns:
        object: The result of the write operation. For writers like DataFrameWriter
                or DictWriter, this is the created object. For file writers, it's None.

    Raises:
        WriteError: If writing fails.
        FormatNotSupportedError: If the format_type is not registered.
        Exception: Other errors during writer initialization or writing.
    """
    logger.info(
        f"Attempting to write graph data using format '{format_type}' to target type '{type(target).__name__}'"
    )

    # Separate kwargs for init vs write
    init_kwargs = {k: v for k, v in kwargs.items() if k in _WRITER_INIT_KWARGS}
    write_kwargs = {k: v for k, v in kwargs.items() if k not in _WRITER_INIT_KWARGS}

    try:
        writer = get_writer(format_type, **init_kwargs)  # Pass only init kwargs
        # Pass remaining kwargs to the write method
        return writer.write(graph, target, **write_kwargs)
    except (IOError, FormatNotSupportedError):
        logger.exception("IO Error writing data")
        raise  # Re-raise specific IO errors
    except Exception as e:
        logger.exception(f"Unexpected error writing data with format '{format_type}'")
        # Wrap unexpected errors
        raise WriteError(
            "Unexpected error during write",
            target=str(target),
            writer_type=format_type,
            original_error=e,
        ) from e


# --- Public API ---

__all__ = [
    # "get_reader", # Probably don't expose getters directly
    # "get_writer",
    # Base classes (optional exposure)
    "DataReader",
    "DataWriter",
    "FormatNotSupportedError",
    # Exceptions
    "IOError",
    "ReadError",
    "WriteError",
    # Registry functions (optional exposure)
    "list_readers",
    "list_writers",
    # Facade functions
    "read_data",
    "write_data",
]
