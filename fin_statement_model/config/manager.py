"""Configuration manager for fin_statement_model.

This module provides utilities to load and merge application configuration from:
    1. Default settings
    2. Project-level config file (.fsm_config.yaml)
    3. User-level config file (fsm_config.yaml)
    4. Environment variables (FSM_* prefix)
    5. Runtime overrides

Example:
    >>> from fin_statement_model.config.manager import ConfigManager
    >>> cm = ConfigManager()
    >>> cfg = cm.get()
    >>> cfg.logging.level
    'WARNING'
"""

import logging
from pathlib import Path
from threading import Lock
from typing import Any, Optional, cast

from fin_statement_model.core.errors import FinancialModelError
from fin_statement_model.utils.dicts import deep_merge

from .models import Config

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------


class ConfigurationError(FinancialModelError):
    """Exception raised for configuration-related errors."""


class ConfigManager:
    """Manage application configuration from multiple sources.

    Loads and merges configuration with the following precedence (highest to lowest):
        1. Runtime updates via `update()`
        2. Environment variables (FSM_* prefix)
        3. User config file (fsm_config.yaml or specified path)
        4. Project config file (.fsm_config.yaml in project root)
        5. Default configuration

    This class is thread-safe.

    Examples:
        >>> from fin_statement_model.config.manager import ConfigManager
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
            config_file: Optional path to a configuration file. If not provided,
                the manager will search for default config files in the
                current directory or home directory.
        """
        self._lock = Lock()
        self._config: Optional[Config] = None
        self._runtime_overrides: dict[str, Any] = {}
        self._config_file = config_file

    def get(self) -> Config:
        """Return the current merged configuration.

        Loads and merges configuration sources on first call or after an
        update/reset operation.

        Returns:
            A validated `Config` object representing the current configuration.

        Examples:
            >>> from fin_statement_model.config.manager import ConfigManager
            >>> cm = ConfigManager()
            >>> cfg = cm.get()
            >>> isinstance(cfg, Config)
            True
        """
        with self._lock:
            if self._config is None:
                self._load_config()
            assert self._config is not None
            return self._config

    def update(self, updates: dict[str, Any]) -> None:
        """Apply runtime overrides to the configuration.

        Merges the provided updates into existing runtime overrides and
        forces a reload on the next `get()` call.

        Args:
            updates: Nested dictionary of configuration keys and values to override.

        Examples:
            >>> cm = ConfigManager()
            >>> cm.update({'logging': {'level': 'DEBUG'}})
        """
        with self._lock:
            self._runtime_overrides = deep_merge(self._runtime_overrides, updates)
            self._config = None  # Force reload on next get()

    def _load_config(self) -> None:
        """Load and merge configuration from all supported sources.

        Reads default settings, then merges in project-level and user-level config
        files, environment variable overrides, and runtime overrides, in order.
        Finally, validates the result into a `Config` object.
        """
        # Load environment variables from a .env file (if present) before any
        # configuration layers are processed. This allows users to keep secrets
        # like API keys in a `.env` file without explicitly exporting them in
        # the shell. Values already present in the process environment are NOT
        # overwritten.
        self._load_dotenv()

        # Start with defaults
        config_dict = Config(
            project_name="fin_statement_model",
            config_file_path=None,
            auto_save_config=False,
        ).to_dict()

        # Layer 1: Project config file
        project_config = self._find_project_config()
        if project_config:
            logger.debug(f"Loading project config from {project_config}")
            config_dict = deep_merge(config_dict, self._load_file(project_config))

        # Layer 2: User config file
        user_config = self._find_user_config()
        if user_config:
            logger.debug(f"Loading user config from {user_config}")
            config_dict = deep_merge(config_dict, self._load_file(user_config))

        # Layer 4: Runtime overrides
        if self._runtime_overrides:
            logger.debug("Applying runtime overrides")
            config_dict = deep_merge(config_dict, self._runtime_overrides)

        # Create and validate final config
        self._config = Config.from_dict(config_dict)

    def _find_project_config(self) -> Optional[Path]:
        """Locate the project-level config file (.fsm_config.yaml).

        Searches upward from the current working directory to the filesystem root.

        Returns:
            Path to the project config file if found, otherwise None.
        """
        # Look for .fsm_config.yaml in parent directories
        current = Path.cwd()
        while current != current.parent:
            config_path = current / self.PROJECT_CONFIG_FILE
            if config_path.exists():
                return config_path
            current = current.parent
        return None

    def _find_user_config(self) -> Optional[Path]:
        """Locate the user-level config file (fsm_config.yaml).

        Checks an explicitly provided path, then the current directory, then
        the home directory.

        Returns:
            Path to the user config file if found, otherwise None.
        """
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
        """Load configuration values from a YAML or JSON file.

        Args:
            path: Path to the config file (.yaml, .yml, or .json).

        Returns:
            A dict of configuration values loaded from the file.

        Raises:
            ConfigurationError: If the file format is unsupported or loading fails.
        """
        try:
            if path.suffix in [".yaml", ".yml"]:
                import yaml

                result = yaml.safe_load(path.read_text()) or {}
                return cast(dict[str, Any], result)
            elif path.suffix == ".json":
                import json

                result = json.loads(path.read_text())
                return cast(dict[str, Any], result)
            else:
                raise ConfigurationError(
                    f"Unsupported config file format: {path.suffix}"
                )
        except Exception as e:
            raise ConfigurationError(f"Failed to load config from {path}: {e}") from e

    # ------------------------------------------------------------------
    # .env loading utilities

    def _load_dotenv(self) -> None:
        """Populate os.environ from the first `.env` file found upward.

        Searches upward from current directory to filesystem root, loading
        `key=value` pairs, skipping comments and blanks. Existing env vars
        are not overwritten. Also maps `FMP_API_KEY` to `FSM_API_FMP_API_KEY`
        for backward compatibility.
        """
        try:
            import os
            from pathlib import Path

            current = Path.cwd()
            while True:
                candidate = current / ".env"
                if candidate.exists() and candidate.is_file():
                    try:
                        for raw_line in candidate.read_text().splitlines():
                            line = raw_line.strip()
                            # Skip blanks and comments
                            if not line or line.startswith("#"):
                                continue
                            if "=" not in line:
                                continue
                            key, value = line.split("=", 1)
                            key = key.strip()
                            # Remove any surrounding quotes from the value
                            value = value.strip().strip("'\"")
                            if key and key not in os.environ:
                                os.environ[key] = value
                        logger.debug("Loaded environment variables from %s", candidate)

                        # Special fallback: if a generic FMP_API_KEY is defined, expose it
                        # via the namespaced FSM_API_FMP_API_KEY expected by the Config
                        # model. This provides compatibility with existing environment
                        # setups without forcing users to duplicate variables.
                        if (
                            "FMP_API_KEY" in os.environ
                            and "FSM_API_FMP_API_KEY" not in os.environ
                        ):
                            os.environ["FSM_API_FMP_API_KEY"] = os.environ[
                                "FMP_API_KEY"
                            ]
                            logger.debug(
                                "Mapped FMP_API_KEY → FSM_API_FMP_API_KEY for config integration"
                            )
                        break  # Stop searching after the first .env file
                    except Exception as err:
                        logger.warning(
                            "Failed to load .env file %s: %s", candidate, err
                        )
                else:
                    # Ascend to parent directory, stop at filesystem root
                    if current.parent == current:
                        break
                    current = current.parent
        except Exception as err:
            # Never fail config loading due to .env issues
            logger.debug("_load_dotenv encountered an error: %s", err, exc_info=False)


# Global configuration instance
_config_manager = ConfigManager()


def get_config() -> Config:
    """Get the global configuration singleton.

    Returns:
        The `Config` object managed by the global ConfigManager.

    Examples:
        >>> from fin_statement_model.config.manager import get_config
        >>> cfg = get_config()
        >>> cfg.logging.level
        'WARNING'
    """
    return _config_manager.get()


def update_config(updates: dict[str, Any]) -> None:
    """Apply runtime overrides to the global configuration.

    Args:
        updates: Nested dict of configuration keys and values to override.
    """
    _config_manager.update(updates)


# Removed reset() method: use context manager for test isolation
