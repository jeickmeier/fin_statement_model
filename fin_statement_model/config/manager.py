"""Configuration manager for fin_statement_model.

This module provides the ConfigManager class that handles loading configurations
from multiple sources and merging them according to precedence rules.
"""

import os
from pathlib import Path
from typing import Any, Optional, List, Union, get_origin, get_args
import logging
from threading import Lock
from pydantic import BaseModel

from .models import Config
from fin_statement_model.core.errors import FinancialModelError

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Environment variable mapping utility
def generate_env_mappings(
    model: type[BaseModel], prefix: Optional[str] = None, path: list[str] | None = None
) -> dict[str, list[str]]:
    """Generate environment variable mappings for a Pydantic model."""
    from .manager import ConfigManager

    if prefix is None:
        prefix = ConfigManager.ENV_PREFIX.rstrip("_")
    if path is None:
        path = []

    mappings: dict[str, list[str]] = {}
    for field_name, field in model.model_fields.items():
        # Field annotation gives the declared type
        annotation = field.annotation
        origin = get_origin(annotation)
        # Handle Optional or Union types
        if origin is Union:
            args = get_args(annotation)
            nested = next(
                (
                    arg
                    for arg in args
                    if isinstance(arg, type) and issubclass(arg, BaseModel)
                ),
                None,
            )
            if nested:
                mappings.update(
                    generate_env_mappings(nested, prefix, path + [field_name])
                )
                continue
        # Nested BaseModel
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            mappings.update(
                generate_env_mappings(annotation, prefix, path + [field_name])
            )
        else:
            leaf_path = path + [field_name]
            env_name = prefix + "_" + "_".join(p.upper() for p in leaf_path)
            mappings[env_name] = leaf_path

    logger.debug(f"Generated {len(mappings)} environment variable mappings")
    return mappings


# ----------------------------------------------------------------------


class ConfigurationError(FinancialModelError):
    """Exception raised for configuration-related errors."""


class ConfigManager:
    """Manages configuration loading and merging from multiple sources.

    Configuration precedence (highest to lowest):
    1. Runtime updates via update_config()
    2. Environment variables (FSM_* prefix)
    3. User config file (fsm_config.yaml in current directory or specified path)
    4. Project config file (.fsm_config.yaml in project root)
    5. Default configuration

    Example:
        >>> config = ConfigManager()
        >>> config.get().logging.level
        'WARNING'
        >>> config.update({'logging': {'level': 'DEBUG'}})
        >>> config.get().logging.level
        'DEBUG'
    """

    # Environment variable prefix
    ENV_PREFIX = "FSM_"

    # Default config file names
    USER_CONFIG_FILE = "fsm_config.yaml"
    PROJECT_CONFIG_FILE = ".fsm_config.yaml"

    def __init__(self, config_file: Optional[Path] = None):
        """Initialize the configuration manager.

        Args:
            config_file: Optional path to a configuration file.
                        If not provided, searches for default config files.
        """
        self._lock = Lock()
        self._config: Optional[Config] = None
        self._runtime_overrides: dict[str, Any] = {}
        self._config_file = config_file

    def get(self) -> Config:
        """Get the current configuration.

        Returns:
            The merged configuration object.
        """
        with self._lock:
            if self._config is None:
                self._load_config()
            return self._config

    def update(self, updates: dict[str, Any]) -> None:
        """Update configuration with runtime values.

        Args:
            updates: Dictionary of configuration updates.
                    Can be nested, e.g., {'logging': {'level': 'DEBUG'}}
        """
        with self._lock:
            self._runtime_overrides = self._deep_merge(self._runtime_overrides, updates)
            self._config = None  # Force reload on next get()

    def reset(self) -> None:
        """Reset configuration to defaults."""
        with self._lock:
            self._runtime_overrides = {}
            self._config = None

    def _load_config(self) -> None:
        """Load and merge configuration from all sources."""
        # Start with defaults
        config_dict = Config().to_dict()

        # Layer 1: Project config file
        project_config = self._find_project_config()
        if project_config:
            logger.debug(f"Loading project config from {project_config}")
            config_dict = self._deep_merge(config_dict, self._load_file(project_config))

        # Layer 2: User config file
        user_config = self._find_user_config()
        if user_config:
            logger.debug(f"Loading user config from {user_config}")
            config_dict = self._deep_merge(config_dict, self._load_file(user_config))

        # Layer 3: Environment variables
        env_config = self._load_from_env()
        if env_config:
            logger.debug("Loading config from environment variables")
            config_dict = self._deep_merge(config_dict, env_config)

        # Layer 4: Runtime overrides
        if self._runtime_overrides:
            logger.debug("Applying runtime overrides")
            config_dict = self._deep_merge(config_dict, self._runtime_overrides)

        # Create and validate final config
        self._config = Config.from_dict(config_dict)

        # Apply logging configuration immediately
        self._apply_logging_config()

    def _find_project_config(self) -> Optional[Path]:
        """Find project-level configuration file."""
        # Look for .fsm_config.yaml in parent directories
        current = Path.cwd()
        while current != current.parent:
            config_path = current / self.PROJECT_CONFIG_FILE
            if config_path.exists():
                return config_path
            current = current.parent
        return None

    def _find_user_config(self) -> Optional[Path]:
        """Find user configuration file."""
        if self._config_file and self._config_file.exists():
            return self._config_file

        # Check current directory
        user_config = Path.cwd() / self.USER_CONFIG_FILE
        if user_config.exists():
            return user_config

        # Check home directory
        home_config = Path.home() / f".{self.USER_CONFIG_FILE}"
        if home_config.exists():
            return home_config

        return None

    def _load_file(self, path: Path) -> dict[str, Any]:
        """Load configuration from file."""
        try:
            if path.suffix in [".yaml", ".yml"]:
                import yaml

                return yaml.safe_load(path.read_text()) or {}
            elif path.suffix == ".json":
                import json

                return json.loads(path.read_text())
            else:
                raise ConfigurationError(
                    f"Unsupported config file format: {path.suffix}"
                )
        except Exception as e:
            raise ConfigurationError(f"Failed to load config from {path}: {e}") from e

    def _load_from_env(self) -> dict[str, Any]:
        """Load configuration from environment variables.

        Environment variables are mapped to config paths:
        FSM_LOGGING_LEVEL -> logging.level
        FSM_IO_DEFAULT_EXCEL_SHEET -> io.default_excel_sheet
        FSM_API_FMP_API_KEY -> api.fmp_api_key

        Mappings are now generated dynamically from the Config model.
        """
        config = {}

        # Generate mappings dynamically from the Config model
        env_mappings = generate_env_mappings(Config)
        # Import helper to parse raw environment variable values
        from .helpers import parse_env_value

        for env_key, config_path in env_mappings.items():
            if env_key in os.environ:
                # Parse the raw environment variable string into proper type
                raw_value = os.environ[env_key]
                value = parse_env_value(raw_value)

                # Build nested dictionary with the parsed value
                current = config
                for key in config_path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                current[config_path[-1]] = value

        return config

    def _deep_merge(
        self, base: dict[str, Any], update: dict[str, Any]
    ) -> dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()

        for key, value in update.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _apply_logging_config(self) -> None:
        """Apply logging configuration to the library."""
        if self._config:
            from fin_statement_model import logging_config

            logging_config.setup_logging(
                level=self._config.logging.level,
                format_string=self._config.logging.format,
                detailed=self._config.logging.detailed,
                log_file_path=(
                    str(self._config.logging.log_file_path)
                    if self._config.logging.log_file_path
                    else None
                ),
            )


# Global configuration instance
_config_manager = ConfigManager()


def get_config() -> Config:
    """Get the current global configuration.

    Returns:
        The current configuration object.
    """
    return _config_manager.get()


def update_config(updates: dict[str, Any]) -> None:
    """Update the global configuration.

    Args:
        updates: Dictionary of configuration updates.
    """
    _config_manager.update(updates)


def reset_config() -> None:
    """Reset configuration to defaults."""
    _config_manager.reset()
