"""Reader functions for statement configuration files.

Handles locating, reading, and parsing JSON/YAML configuration files
into raw Python dictionaries.
"""

import json
import yaml
import logging
import os
from pathlib import Path
from typing import Any, Optional

from fin_statement_model.io.exceptions import ReadError

logger = logging.getLogger(__name__)

__all__ = [
    "read_statement_config_from_path",
    "list_available_builtin_configs",
    "read_builtin_statement_config",
]

def read_statement_config_from_path(config_path: str) -> dict[str, Any]:
    """Reads and parses a statement configuration file from a given path.

    Supports JSON and YAML formats.

    Args:
        config_path: Absolute or relative path to the configuration file.

    Returns:
        The parsed configuration data as a dictionary.

    Raises:
        ReadError: If the file is not found, has an unsupported extension,
                   or cannot be parsed.
    """
    path = Path(config_path)

    if not path.exists() or not path.is_file():
        raise ReadError(
            message="Configuration file not found or is not a file",
            target=config_path,
        )

    extension = path.suffix.lower()
    config_data = {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            if extension == ".json":
                config_data = json.load(f)
            elif extension in [".yaml", ".yml"]:
                config_data = yaml.safe_load(f)
            else:
                raise ReadError(
                    message="Unsupported file extension for statement config",
                    target=config_path,
                    details=f"Use .json, .yaml, or .yml instead of {extension}",
                )
        logger.debug(f"Successfully read and parsed config file: {config_path}")
        return config_data

    except json.JSONDecodeError as e:
        logger.exception(f"Error parsing JSON configuration file {config_path}")
        raise ReadError(
            message="Invalid JSON format in configuration file",
            target=config_path,
            original_error=e,
            details=f"JSON decode error at line {e.lineno}, column {e.colno}: {e.msg}",
        ) from e
    except yaml.YAMLError as e:
        logger.exception(f"Error parsing YAML configuration file {config_path}")
        details = str(e)
        if hasattr(e, "problem_mark"):
            mark = e.problem_mark
            if mark:
                details = (
                    f"YAML parse error near line {mark.line + 1}, column {mark.column + 1}: "
                    f"{getattr(e, 'problem', '')}"
                )
        raise ReadError(
            message="Invalid YAML format in configuration file",
            target=config_path,
            original_error=e,
            details=details,
        ) from e
    except IOError as e:
        logger.exception(f"IO Error reading configuration file {config_path}")
        raise ReadError(
            message="Failed to read configuration file",
            target=config_path,
            original_error=e,
        ) from e
    except Exception as e:
        logger.exception(f"Unexpected error loading configuration from {config_path}")
        raise ReadError(
            message="Unexpected error loading configuration file",
            target=config_path,
            original_error=e,
        ) from e


def _get_builtin_mapping_dir() -> Path:
    """Return path to built-in mapping directory, using env var override if set.

    Assumes mappings live in 'statements/config/mappings' relative to this file's
    grandparent directory (io/). This might need adjustment depending on packaging.
    Alternatively, use importlib.resources if mappings are package data.
    """
    mapping_env = os.getenv("FIN_STATEMENTS_MAPPING_DIR")
    if mapping_env:
        return Path(mapping_env)

    # Calculate path relative to this file (io/readers/statement_config_reader.py)
    # Go up two levels (to fin_statement_model/) then down to statements/config/mappings
    try:
        # More robust: Use __file__ of a known module in the expected location
        # Example: from fin_statement_model import statements
        # mapping_dir = Path(statements.__file__).parent / "config" / "mappings"
        # Less robust but simpler for now:
        this_file_dir = Path(__file__).parent # io/readers
        package_root = this_file_dir.parent.parent # fin_statement_model/
        mapping_dir = package_root / "statements" / "config" / "mappings"
        return mapping_dir
    except Exception as e:
        logger.error(f"Could not determine built-in mapping directory: {e}")
        # Fallback or raise error
        return Path("./fin_statement_model/statements/config/mappings") # Example fallback

def list_available_builtin_configs() -> list[str]:
    """List the names of all built-in statement configuration mappings available.

    Returns:
        List[str]: List of mapping names (filename without extension).
    """
    mapping_dir = _get_builtin_mapping_dir()
    if not mapping_dir.exists() or not mapping_dir.is_dir():
        logger.warning(f"Built-in mapping directory not found or not a directory: {mapping_dir}")
        return []
    try:
        names = [
            p.stem
            for p in mapping_dir.iterdir()
            if p.is_file() and p.suffix.lower() in (".yaml", ".yml", ".json")
        ]
        return sorted(names)
    except OSError as e:
        logger.error(f"Error listing built-in configs in {mapping_dir}: {e}")
        return []

def read_builtin_statement_config(name: str) -> dict[str, Any]:
    """Reads and parses a built-in statement configuration by name.

    Searches for <name>.yaml, <name>.yml, or <name>.json in the built-in
    mappings directory.

    Args:
        name: The name of the built-in configuration (filename without extension).

    Returns:
        The parsed configuration data as a dictionary.

    Raises:
        ReadError: If no matching configuration file is found or if reading/parsing fails.
    """
    mapping_dir = _get_builtin_mapping_dir()
    found_path: Optional[Path] = None

    for ext in (".yaml", ".yml", ".json"):
        path_to_check = mapping_dir / f"{name}{ext}"
        if path_to_check.exists() and path_to_check.is_file():
            found_path = path_to_check
            break

    if found_path:
        logger.debug(f"Found built-in config '{name}' at: {found_path}")
        # Delegate reading and parsing to the main function
        return read_statement_config_from_path(str(found_path))
    else:
        logger.warning(f"Built-in statement config '{name}' not found in {mapping_dir}")
        raise ReadError(
            message=f"Built-in statement config '{name}' not found",
            target=str(mapping_dir),
            details=f"No file found for '{name}' with .yaml, .yml, or .json extension.",
        ) 