"""Statement-related I/O utilities.

This module provides helper functions related to financial statement I/O.
Its primary responsibilities are:
- Discovering built-in statement configuration files.
- Providing convenient wrappers to write formatted statement DataFrames to
  common file formats like Excel and JSON.
"""

import importlib.resources
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from fin_statement_model.io.exceptions import WriteError

logger = logging.getLogger(__name__)

# Built-in config package path constant (directory containing YAML/JSON configs)
# Default base path is "fin_statement_model.statements.configs" - end-users can
# drop YAML or JSON files in that package (or a sub-package added to
# ``__init__.py``) and they will be discovered automatically.

_BUILTIN_CONFIG_PACKAGE = "fin_statement_model.statements.configs"


def list_available_builtin_configs() -> list[str]:
    """List names of all built-in statement configuration mappings."""
    package_path = _BUILTIN_CONFIG_PACKAGE
    try:
        resource_path = importlib.resources.files(package_path)
        if not resource_path.is_dir():
            logger.warning(
                "Built-in config package path is not a directory: %s",
                package_path,
            )
            return []
        names = [
            Path(res.name).stem
            for res in resource_path.iterdir()
            if res.is_file() and Path(res.name).suffix.lower() in (".yaml", ".yml", ".json")
        ]
        return sorted(names)
    except (ModuleNotFoundError, FileNotFoundError):
        logger.exception("Built-in statement config path not found: %s", package_path)
        return []


# ===== Statement Writing =====


def write_statement_to_excel(statement_df: pd.DataFrame, file_path: str, **kwargs: Any) -> None:
    """Write a statement DataFrame to an Excel file."""
    try:
        kwargs.setdefault("index", False)
        statement_df.to_excel(file_path, **kwargs)
    except Exception as e:
        raise WriteError(
            message="Failed to export statement DataFrame to Excel",
            target=file_path,
            writer_type="excel",
            original_error=e,
        ) from e


def write_statement_to_json(
    statement_df: pd.DataFrame,
    file_path: str,
    orient: str = "columns",
    indent: int | None = None,
    **kwargs: Any,
) -> None:
    """Write a statement DataFrame to a JSON file.

    The `pandas` typing stubs restrict the accepted keyword arguments
    based on the selected *orient*.  In particular the *indent* argument
    is only valid for the "records" orient.  Passing it for other
    orientations triggers a static type error under ``--strict`` mode.
    The helper therefore forwards *indent* **only** when the chosen
    *orient* supports it.
    """
    try:
        if orient == "records" and indent is not None:
            statement_df.to_json(  # type: ignore[call-overload]
                file_path, orient=orient, indent=indent, **kwargs
            )
        else:
            statement_df.to_json(  # type: ignore[call-overload]
                file_path, orient=orient, **kwargs
            )
    except Exception as e:
        raise WriteError(
            message="Failed to export statement DataFrame to JSON",
            target=file_path,
            writer_type="json",
            original_error=e,
        ) from e


__all__ = [
    # Built-in config helpers
    "list_available_builtin_configs",
    # Statement writing
    "write_statement_to_excel",
    "write_statement_to_json",
]
