"""Configuration file loader for statement configurations.

This module handles reading statement configuration files from disk,
delegating to the IO layer for actual file operations.
"""

import logging
from typing import Any

from fin_statement_model.io import (
    read_statement_config_from_path,
    read_statement_configs_from_directory,
)

logger = logging.getLogger(__name__)

__all__ = ["load_config_directory", "load_config_file"]


def load_config_file(config_path: str) -> dict[str, Any]:
    """Load a single statement configuration file.

    Args:
        config_path: Path to the configuration file.

    Returns:
        Dictionary containing the configuration data.

    Raises:
        ReadError: If the file cannot be read.
        FileNotFoundError: If the file doesn't exist.
    """
    try:
        return read_statement_config_from_path(config_path)
    except:
        logger.exception(f"Failed to load config file {config_path}")
        raise


def load_config_directory(config_dir: str) -> dict[str, dict[str, Any]]:
    """Load all statement configuration files from a directory.

    Args:
        config_dir: Path to the directory containing config files.

    Returns:
        Dictionary mapping config names to configuration data.

    Raises:
        ReadError: If any file cannot be read.
        FileNotFoundError: If the directory doesn't exist.
    """
    try:
        return read_statement_configs_from_directory(config_dir)
    except:
        logger.exception(f"Failed to load configs from directory {config_dir}")
        raise
