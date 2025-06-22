"""Facade functions for simplified IO operations.

This module provides the main public API for reading and writing data,
abstracting away the complexity of the registry system.
"""

import logging
from typing import Any

from fin_statement_model.core.graph import Graph
from .registry import get_reader, get_writer

# Keep import solely for re-export in docstrings – alias with underscore to
# silence linter about unused names.
from fin_statement_model.io.exceptions import (  # noqa: F401
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

    # Build the constructor-time config strictly from the *config* argument.
    # Runtime-specific options stay in **read_kwargs** and are forwarded untouched.
    if config is None:
        config_kwargs: dict[str, Any] = {"source": source, "format_type": format_type}
    else:
        if isinstance(config, dict):
            config_kwargs = config.copy()
        elif hasattr(config, "model_dump"):
            # The `model_dump` method is provided by Pydantic's BaseModel.
            config_kwargs = config.model_dump()
        else:
            config_kwargs = dict(config.__dict__)
        config_kwargs.update({"source": source, "format_type": format_type})

    reader = get_reader(**config_kwargs)
    return reader.read(config_kwargs["source"], **read_kwargs)


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

    # Build constructor-time config strictly from *config* argument.
    if config is None:
        config_kwargs: dict[str, Any] = {"target": target, "format_type": format_type}
    else:
        if isinstance(config, dict):
            config_kwargs = config.copy()
        elif hasattr(config, "model_dump"):
            # Pydantic v2 models – see note above.
            config_kwargs = config.model_dump()
        else:
            config_kwargs = dict(config.__dict__)
        config_kwargs.update({"target": target, "format_type": format_type})

    writer = get_writer(**config_kwargs)
    return writer.write(graph, target, **write_kwargs)


__all__ = ["read_data", "write_data"]
