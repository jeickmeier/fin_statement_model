"""Facade functions for simplified IO operations.

This module provides the main public API for reading and writing data,
abstracting away the complexity of the registry system.
"""

import logging
import os
from typing import Any

from fin_statement_model.core.graph import Graph
from .registry import get_reader, get_writer
from fin_statement_model.io.exceptions import (
    IOError,
    ReadError,
    WriteError,
    FormatNotSupportedError,
)

logger = logging.getLogger(__name__)


def read_data(
    format_type: str,
    source: Any,
    *,
    config: dict[str, Any] | Any | None = None,
    **read_kwargs: Any,
) -> Graph:
    """Reads data from a source using the specified format.

    This function acts as a facade for the underlying reader implementations.
    It uses the `format_type` to look up the appropriate reader class in the registry.
    The `source` and `**kwargs` are combined and validated against the specific
    reader's Pydantic configuration model (e.g., `CsvReaderConfig`).

    The validated configuration is used to initialize the reader instance.
    The `source` (which might be the original object for dict/dataframe formats, or
    the validated string path/ticker otherwise) and the original `**kwargs` are then
    passed to the reader instance's `.read()` method, which handles format-specific
    read-time options.

    Args:
        format_type (str): The format identifier (e.g., 'excel', 'csv', 'fmp', 'dict').
        source (Any): The data source. Its type depends on `format_type`:
            - `str`: file path (for 'excel', 'csv'), ticker symbol (for 'fmp').
            - `pd.DataFrame`: for 'dataframe'.
            - `dict`: for 'dict'.
        **kwargs: Additional keyword arguments used for reader configuration (e.g.,
            `api_key`, `delimiter`, `sheet_name`, `mapping_config`) and potentially
            passed to the reader's `.read()` method (e.g., `periods`). Consult the
            specific reader's Pydantic config model and `.read()` docstring.

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

    # ------------------------------------------------------------
    # Back-compat: if caller passed schema keys at top level, we keep
    # previous behaviour and treat everything as config.  If `config`
    # param provided we use that for constructor validation while the
    # remaining kwargs are forwarded to .read().
    # ------------------------------------------------------------
    if config is not None:
        if not isinstance(config, dict):
            # allow Pydantic model or other objects
            cfg_payload: Any = config
        else:
            cfg_payload = config.copy()
        cfg_payload.update({"source": source, "format_type": format_type})
        config_kwargs = cfg_payload
    else:
        # legacy path – treat *all* kwargs as part of config
        config_kwargs = {**read_kwargs, "source": source, "format_type": format_type}

    try:
        # Pass the config kwargs directly to get_reader
        reader = get_reader(**config_kwargs)

        # Determine the actual source object for the read method
        actual_source = (
            source if format_type in ("dict", "dataframe") else config_kwargs["source"]
        )

        # Pass the determined source and the original kwargs (excluding config keys potentially)
        # to the read method. Specific readers handle relevant kwargs.
        return reader.read(actual_source, **read_kwargs)
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
    target: Any,
    *,
    config: dict[str, Any] | Any | None = None,
    **write_kwargs: Any,
) -> object:
    """Writes graph data to a target using the specified format.

    Similar to `read_data`, this acts as a facade for writer implementations.
    It uses `format_type` to find the writer class in the registry.
    The `target` and `**kwargs` are combined and validated against the specific
    writer's Pydantic configuration model (e.g., `ExcelWriterConfig`).

    The validated configuration initializes the writer instance.
    The original `graph`, `target`, and `**kwargs` are then passed to the writer
    instance's `.write()` method for format-specific write-time options.

    Args:
        format_type (str): The format identifier (e.g., 'excel', 'dataframe', 'dict').
        graph (Graph): The graph object containing data to write.
        target (Any): The destination target. Its type depends on `format_type`:
            - `str`: file path (usually required for file-based writers like 'excel').
            - Ignored: for writers that return objects (like 'dataframe', 'dict').
        **kwargs: Additional keyword arguments used for writer configuration (e.g.,
            `sheet_name`, `recalculate`) and potentially passed to the writer's
            `.write()` method. Consult the specific writer's Pydantic config model
            and `.write()` docstring.

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

    # Separate constructor config vs runtime write kwargs --------
    if config is not None:
        cfg_payload = config if not isinstance(config, dict) else config.copy()
        if isinstance(cfg_payload, dict):
            cfg_payload.update({"target": target, "format_type": format_type})
        config_kwargs = cfg_payload
    else:
        # legacy: treat all kwargs as config
        config_kwargs = {**write_kwargs, "target": target, "format_type": format_type}

    try:
        # Pass the config kwargs directly to get_writer
        writer = get_writer(**config_kwargs)
        # Now call write with all writer-specific kwargs
        result = writer.write(graph, target, **write_kwargs)

        # If the writer returns a string and target is a path, write it to the file.
        if isinstance(result, str) and isinstance(target, str):
            try:
                # Ensure target directory exists
                dir_path = os.path.dirname(target)
                if dir_path:
                    os.makedirs(dir_path, exist_ok=True)
                logger.debug(
                    f"Writing string result from writer '{type(writer).__name__}' to file: {target}"
                )
                with open(target, "w", encoding="utf-8") as f:
                    f.write(result)
                return None  # Consistent return for file writers
            except OSError as e:
                logger.exception(
                    f"Failed to write writer output to target file: {target}"
                )
                raise WriteError(
                    f"Failed to write writer output to file: {target}",
                    target=target,
                    writer_type=format_type,
                    original_error=e,
                ) from e
        else:
            # Otherwise, return the original result (e.g., DataFrame, dict)
            return result
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


__all__ = ["read_data", "write_data"]
