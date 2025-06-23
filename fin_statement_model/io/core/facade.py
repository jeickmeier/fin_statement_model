"""High-level facade functions for simplified I/O operations.

This module provides the main public entry points for all data reading and writing
tasks. The `read_data` and `write_data` functions act as a simplified facade
over the underlying registry and handler system, providing a convenient and
consistent way to perform I/O without needing to interact directly with specific
reader or writer classes.

These functions are the recommended way for end-users to interact with the I/O
subsystem.
"""

import logging
from typing import Any

from fin_statement_model.core.graph import Graph

from .registry import get_reader, get_writer

# Keep import solely for re-export in docstrings - alias with underscore to
# silence linter about unused names.

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
        config: Optional dictionary or Pydantic model instance for reader
            configuration (e.g., `api_key`, `delimiter`, `sheet_name`).
        **read_kwargs: Additional keyword arguments passed directly to the
            reader's `.read()` method (e.g., `periods`). Consult the specific
            reader's documentation for available options.

    Returns:
        Graph: A new Graph object populated with the read data.

    Raises:
        ReadError: If reading fails.
        FormatNotSupportedError: If the format_type is not registered.
        Exception: Other errors during reader initialization or reading.

    Examples:
        Reading a CSV file with a custom delimiter:
        ```python
        # from fin_statement_model.io import read_data
        # # Assume 'my_data.csv' exists and is pipe-delimited
        # graph = read_data(
        #     format_type="csv",
        #     source="my_data.csv",
        #     config={"delimiter": "|"}
        # )
        ```

        Reading from the FMP API:
        ```python
        # from fin_statement_model.io import read_data
        # graph = read_data(
        #     format_type="fmp",
        #     source="AAPL",
        #     config={
        #         "statement_type": "income_statement",
        #         "api_key": "YOUR_API_KEY",
        #     }
        # )
        ```
    """
    logger.info("Attempting to read data using format '%s' from source type '%s'", format_type, type(source).__name__)

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
        config: Optional dictionary or Pydantic model for writer
            configuration (e.g., `sheet_name`, `recalculate`).
        **write_kwargs: Additional keyword arguments passed directly to the
            writer's `.write()` method. Consult the specific writer's
            documentation for available options.

    Returns:
        object: The result of the write operation. For writers like DataFrameWriter
                or DictWriter, this is the created object. For file writers, it's None.

    Raises:
        WriteError: If writing fails.
        FormatNotSupportedError: If the format_type is not registered.
        Exception: Other errors during writer initialization or writing.

    Examples:
        Writing graph data to an Excel file:
        ```python
        # from fin_statement_model.io import write_data
        # from fin_statement_model.core import Graph
        # g = Graph(periods=["2023"])
        # # ... populate graph with nodes ...
        # write_data(
        #     format_type="excel",
        #     graph=g,
        #     target="output.xlsx",
        #     config={"sheet_name": "MyData"}
        # )
        ```

        Getting data as a dictionary:
        ```python
        # from fin_statement_model.io import write_data
        # from fin_statement_model.core import Graph
        # g = Graph(periods=["2023"])
        # # ... populate graph with nodes ...
        # data_dict = write_data(
        #     format_type="dict",
        #     graph=g,
        #     target=None  # Target is ignored for dict writer
        # )
        ```
    """
    logger.info(
        "Attempting to write graph data using format '%s' to target type '%s'", format_type, type(target).__name__
    )

    # Build constructor-time config strictly from *config* argument.
    if config is None:
        config_kwargs: dict[str, Any] = {"target": target, "format_type": format_type}
    else:
        if isinstance(config, dict):
            config_kwargs = config.copy()
        elif hasattr(config, "model_dump"):
            # Pydantic v2 models - see note above.
            config_kwargs = config.model_dump()
        else:
            config_kwargs = dict(config.__dict__)
        config_kwargs.update({"target": target, "format_type": format_type})

    writer = get_writer(**config_kwargs)
    return writer.write(graph, target, **write_kwargs)


__all__ = ["read_data", "write_data"]
