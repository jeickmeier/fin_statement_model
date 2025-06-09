"""Statement-related IO utilities for built-in configs and writing formatted statement data."""

import json
import yaml
import logging
import importlib.resources
from pathlib import Path
from typing import Any

import pandas as pd

from fin_statement_model.io.exceptions import ReadError, WriteError

logger = logging.getLogger(__name__)

# Built-in config package path constant (directory containing YAML/JSON configs)
# Default base path is "fin_statement_model.statements.configs" – end-users can
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
                f"Built-in config package path is not a directory: {package_path}"
            )
            return []
        names = [
            Path(res.name).stem
            for res in resource_path.iterdir()
            if res.is_file()
            and Path(res.name).suffix.lower() in (".yaml", ".yml", ".json")
        ]
        return sorted(names)
    except (ModuleNotFoundError, FileNotFoundError):
        logger.warning(f"Built-in statement config path not found: {package_path}")
        return []


def read_builtin_statement_config(name: str) -> dict[str, Any]:
    """Read and parse a built-in statement config by name."""
    package_path = _BUILTIN_CONFIG_PACKAGE
    found = None
    content = None
    for ext in (".yaml", ".yml", ".json"):
        try:
            path = importlib.resources.files(package_path).joinpath(f"{name}{ext}")
            if path.is_file():
                content = path.read_text(encoding="utf-8")
                found = ext
                break
        except Exception:
            continue
    if not content or not found:
        raise ReadError(
            message=f"Built-in statement config '{name}' not found in {package_path}",
            source=package_path,
        )
    try:
        if found == ".json":
            return json.loads(content)
        return yaml.safe_load(content)
    except Exception as e:
        raise ReadError(
            message=f"Failed to parse built-in statement config '{name}'",
            source=f"{package_path}/{name}{found}",
            original_error=e,
        ) from e


# ===== Statement Writing =====


def write_statement_to_excel(
    statement_df: pd.DataFrame, file_path: str, **kwargs: Any
) -> None:
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
    **kwargs: Any,
) -> None:
    """Write a statement DataFrame to a JSON file."""
    try:
        statement_df.to_json(file_path, orient=orient, **kwargs)
    except Exception as e:
        raise WriteError(
            message="Failed to export statement DataFrame to JSON",
            target=file_path,
            writer_type="json",
            original_error=e,
        ) from e


__all__ = [
    # Built-in configs
    "list_available_builtin_configs",
    "read_builtin_statement_config",
    # Statement writing
    "write_statement_to_excel",
    "write_statement_to_json",
]
