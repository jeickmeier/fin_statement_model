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

import os
from pathlib import Path
from typing import Any, Optional, Union, get_origin, get_args, cast
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
    """Generate environment variable mappings for a Pydantic model.

    Recursively traverse the fields of a Pydantic BaseModel class to map
    environment variable names to config path segments.

    Args:
        model: The Pydantic model class to inspect.
        prefix: Optional prefix for environment variable names; defaults to
            the ConfigManager.ENV_PREFIX without trailing underscore.
        path: Internal parameter for recursive calls representing the
            current path of nested model fields.

    Returns:
        A dict mapping environment variable names to lists of config path
        segments, e.g. {'FSM_DATABASE_HOST': ['database', 'host']}.

    Examples:
        >>> from fin_statement_model.config.manager import generate_env_mappings
        >>> mappings = generate_env_mappings(Config)
        >>> 'FSM_LOGGING_LEVEL' in mappings
        True
    """
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
                    generate_env_mappings(nested, prefix, [*path, field_name])
                )
                continue
        # Nested BaseModel
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            mappings.update(
                generate_env_mappings(annotation, prefix, [*path, field_name])
            )
        else:
            leaf_path = [*path, field_name]
            env_name = prefix + "_" + "_".join(p.upper() for p in leaf_path)
            mappings[env_name] = leaf_path

    logger.debug(f"Generated {len(mappings)} environment variable mappings")
    return mappings


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
            self._runtime_overrides = self._deep_merge(self._runtime_overrides, updates)
            self._config = None  # Force reload on next get()

    def reset(self) -> None:
        """Clear runtime overrides and reset configuration to defaults.

        After calling this, the next `get()` will rebuild config from base sources.
        """
        with self._lock:
            self._runtime_overrides = {}
            self._config = None

    def _load_config(self) -> None:
        """Load and merge configuration from all supported sources.

        Reads default settings, then merges in project-level and user-level config
        files, environment variable overrides, and runtime overrides, in order.
        Finally, validates the result into a `Config` object and applies logging.
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

    def _load_from_env(self) -> dict[str, Any]:
        """Load configuration overrides from environment variables.

        Generates env var to config path mappings from the Config model,
        parses raw values, and builds nested override dict.

        Returns:
            A nested dict of config values set via environment variables.
        """
        config: dict[str, Any] = {}

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
        """Recursively merge two dictionaries with `update` taking precedence.

        Args:
            base: Original dict.
            update: Dict of new values to merge.

        Returns:
            A new dict representing the deep merge of base and update.
        """
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
        """Configure library logging based on current settings.

        Reads logging configuration from `self._config` and applies it via
        `logging_config.setup_logging()`.
        """
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
                    except Exception as err:  # noqa: BLE001  (broad but safe here)
                        logger.warning(
                            "Failed to load .env file %s: %s", candidate, err
                        )
                else:
                    # Ascend to parent directory, stop at filesystem root
                    if current.parent == current:
                        break
                    current = current.parent
        except Exception as err:  # noqa: BLE001
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


def reset_config() -> None:
    """Reset the global configuration singleton to defaults.

    Clears runtime overrides so that subsequent `get_config()` calls rebuild
    from static sources.
    """
    _config_manager.reset()
