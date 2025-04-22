"""Loader for statement configuration files and built-in mappings.

Provides:
  - load_statement_config: load any JSON/YAML config via StatementConfig
  - list_built_in_statements: list mapping file names in config/mappings/
  - load_built_in_statement: load a named mapping from config/mappings/
"""

import logging
import os
from pathlib import Path

from fin_statement_model.statements.errors import ConfigurationError
from fin_statement_model.statements.config.config import StatementConfig
from fin_statement_model.statements.structure import StatementStructure

logger = logging.getLogger(__name__)

# Directory where built-in mapping files live (allow override via env var)
this_dir = Path(__file__).parent


def _get_mapping_dir() -> Path:
    """Return path to mapping directory, using FIN_STATEMENTS_MAPPING_DIR if set."""
    mapping_env = os.getenv("FIN_STATEMENTS_MAPPING_DIR")
    if mapping_env:
        return Path(mapping_env)
    return this_dir / "mappings"


__all__ = [
    "list_built_in_statements",
    "load_built_in_statement",
    "load_statement_config",
]


def load_statement_config(config_path: str) -> StatementStructure:
    """Load a statement structure from a JSON or YAML file at any path.

    Args:
        config_path: Path to .json, .yaml, or .yml file defining the statement

    Returns:
        StatementStructure: Parsed statement structure

    Raises:
        ConfigurationError: If the file cannot be parsed or is invalid
    """
    try:
        cfg = StatementConfig(config_path=config_path)
        return cfg.build_statement_structure()
    except Exception as e:
        if isinstance(e, ConfigurationError):
            raise
        logger.exception(f"Error loading statement config from {config_path}")
        raise ConfigurationError(
            message="Failed to load statement configuration",
            config_path=config_path,
            errors=[str(e)],
        ) from e


def list_built_in_statements() -> list[str]:
    """List the names of all built-in statement mappings available.

    Returns:
        List[str]: List of mapping names (filename without extension)
    """
    mapping_dir = _get_mapping_dir()
    if not mapping_dir.exists():
        return []
    names = [
        p.stem
        for p in mapping_dir.iterdir()
        if p.is_file() and p.suffix.lower() in (".yaml", ".yml", ".json")
    ]
    return sorted(names)


def load_built_in_statement(name: str) -> StatementStructure:
    """Load a built-in statement by name from the config/mappings directory.

    Args:
        name: Mapping name (filename without extension)

    Returns:
        StatementStructure: Parsed statement structure

    Raises:
        ConfigurationError: If no such mapping exists or parsing fails
    """
    mapping_dir = _get_mapping_dir()
    for ext in (".yaml", ".yml", ".json"):
        path = mapping_dir / f"{name}{ext}"
        if path.exists():
            return load_statement_config(str(path))
    raise ConfigurationError(
        message=f"Built-in statement '{name}' not found",
        config_path=str(mapping_dir),
        errors=[f"No file for '{name}' with .yaml, .yml, or .json extension"],
    )
