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
# Avoid importing fin_statement_model.statements at module import time to
# prevent circular dependencies.  Provide lightweight *wrapper* functions
# that import the heavy implementation lazily on first use.

from .graph import import_from_cells  # noqa: F401
from .adjustments import (
    load_adjustments_from_excel,
    export_adjustments_to_excel,
)

from pathlib import Path
from typing import Any, Union

import pandas as pd


def list_available_builtin_configs() -> list[str]:  # noqa: D401
    """Return the IDs of statement configs bundled with the library."""

    from fin_statement_model.statements import list_available_builtin_configs as _impl

    return _impl()


def write_statement_to_excel(
    df: "pd.DataFrame",  # noqa: D401
    target: Union[str, Path],
    **kwargs: Any,
) -> None:
    """Persist a single statement DataFrame to an Excel file.

    This helper is intentionally lightweight and avoids additional
    dependencies by delegating directly to ``pandas.DataFrame.to_excel``.

    Args:
        df: The pandas ``DataFrame`` representing the statement.  Rows should
            correspond to line items, columns to periods.
        target: Destination path of the ``.xlsx`` file. Missing parent
            directories are created automatically.
        **kwargs: Additional keyword arguments forwarded verbatim to
            ``DataFrame.to_excel`` (e.g., ``sheet_name``, ``engine``).
    """

    output_path = Path(target)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_excel(output_path, index=False, **kwargs)


def write_statement_to_json(
    df: "pd.DataFrame",  # noqa: D401
    target: Union[str, Path],
    *,
    orient: str = "records",
    indent: int = 2,
    **kwargs: Any,
) -> None:
    """Persist a single statement DataFrame to a JSON file.

    Args:
        df: The pandas ``DataFrame`` representing the statement.
        target: Destination path of the ``.json`` file.
        orient: JSON orientation (see ``pandas.DataFrame.to_json`` docs).
        indent: Number of spaces for indentation (only used for ``orient != 'split'``).
        **kwargs: Additional keyword arguments forwarded to
            ``DataFrame.to_json``.
    """

    output_path = Path(target)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_json(output_path, orient=orient, indent=indent, **kwargs)


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
