"""Configuration manager for fin_statement_model.

This module provides utilities to load and merge application configuration from:
    1. Default settings
    2. Project-level config file (.fsm_config.yaml)
    3. User-level config file (fsm_config.yaml)
    4. Environment variables (FSM_* prefix)
    5. Runtime overrides

Example:
    >>> from fin_statement_model.config.manager import ConfigManager, get_config, update_config
    >>> cm = ConfigManager()
    >>> cfg = cm.get()
    >>> cfg.logging.level
    'WARNING'
    >>> update_config({'logging': {'level': 'DEBUG'}})
    >>> get_config().logging.level
    'DEBUG'
"""

from pathlib import Path
from typing import Any, Optional, cast
import logging
from threading import Lock

from .models import Config
from fin_statement_model.core.errors import FinStatementModelError

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------


class ConfigurationError(FinStatementModelError):
    """Exception raised for configuration-related errors.

    Examples:
        >>> raise ConfigurationError('Invalid config')
        Traceback (most recent call last):
            ...
        fin_statement_model.core.errors.FinStatementModelError: Invalid config
    """


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

            # Persist changes if auto_save_config is enabled and we know target path
            cfg_after = self.get()
            if cfg_after.auto_save_config and cfg_after.config_file_path:
                try:
                    self.save(cfg_after.config_file_path)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Failed to auto-save configuration: %s", exc)

            # Re-apply logging immediately after update
            self.reconfigure_logging()

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
        env_overrides = self._extract_env_overrides()
        if env_overrides:
            logger.debug("Applying environment variable overrides")
            config_dict = self._deep_merge(config_dict, env_overrides)

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

        Examples:
            >>> from fin_statement_model.config.manager import ConfigManager
            >>> cm = ConfigManager()
            >>> isinstance(cm._find_project_config(), (type(None), Path))
            True
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

        Examples:
            >>> from fin_statement_model.config.manager import ConfigManager
            >>> cm = ConfigManager()
            >>> isinstance(cm._find_user_config(), (type(None), Path))
            True
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

        Examples:
            >>> from pathlib import Path
            >>> from fin_statement_model.config.manager import ConfigManager
            >>> cm = ConfigManager()
            >>> # cm._load_file(Path('somefile.yaml'))  # doctest: +SKIP
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

    def _deep_merge(
        self, base: dict[str, Any], update: dict[str, Any]
    ) -> dict[str, Any]:
        """Recursively merge two dictionaries with `update` taking precedence.

        Args:
            base: The base dictionary.
            update: The dictionary with override values.

        Returns:
            A new dictionary with merged values.

        Examples:
            >>> from fin_statement_model.config.manager import ConfigManager
            >>> cm = ConfigManager()
            >>> cm._deep_merge({'a': 1, 'b': {'c': 2}}, {'b': {'c': 3}, 'd': 4})
            {'a': 1, 'b': {'c': 3}, 'd': 4}
        """
        result = base.copy()

        for key, value in update.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            # If both are lists, append unique items preserving order
            elif (
                key in result
                and isinstance(result[key], list)
                and isinstance(value, list)
            ):
                combined = result[key] + [
                    item for item in value if item not in result[key]
                ]
                result[key] = combined
            else:
                result[key] = value

        return result

    # ------------------------------------------------------------------
    # .env loading utilities

    def _load_dotenv(self) -> None:
        """Populate os.environ from the first `.env` file found upward.

        Searches upward from current directory to filesystem root, loading
        `key=value` pairs, skipping comments and blanks. Existing env vars
        are not overwritten. Also maps `FMP_API_KEY` to `FSM_API__FMP_API_KEY`
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
                        # via the namespaced FSM_API__FMP_API_KEY expected by the Config
                        if (
                            "FMP_API_KEY" in os.environ
                            and "FSM_API__FMP_API_KEY" not in os.environ
                        ):
                            os.environ["FSM_API__FMP_API_KEY"] = os.environ[
                                "FMP_API_KEY"
                            ]
                            logger.debug(
                                "Mapped FMP_API_KEY → FSM_API__FMP_API_KEY for config integration"
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

    # ------------------------------------------------------------------
    # Environment variable helpers

    def _extract_env_overrides(self) -> dict[str, Any]:
        """Convert FSM_* environment variables to config overrides.

        Rules:
        - Keys start with ENV_PREFIX ("FSM_")
        - Remainder converted to lowercase path with dots: FSM_LOGGING__LEVEL → logging.level
        - Double underscore (__) denotes nested separation; single underscore also allowed but
          double underscore takes precedence to avoid issues with values containing underscores.
        - Values parsed via helpers.parse_env_value.

        Returns:
            Nested dictionary of config overrides from environment variables.

        Examples:
            >>> import os
            >>> os.environ['FSM_LOGGING__LEVEL'] = 'DEBUG'
            >>> from fin_statement_model.config.manager import ConfigManager
            >>> cm = ConfigManager()
            >>> overrides = cm._extract_env_overrides()
            >>> overrides['logging']['level']
            'DEBUG'
        """
        import os
        from fin_statement_model.config.helpers import parse_env_value

        overrides: dict[str, Any] = {}

        prefix_len = len(self.ENV_PREFIX)
        for key, raw_value in os.environ.items():
            if not key.startswith(self.ENV_PREFIX):
                continue

            path_str = key[prefix_len:]

            # Normalise path: prefer double underscores as separator, fallback to single
            parts = [p.lower() for p in path_str.split("__")]
            if len(parts) == 1:
                parts = [p.lower() for p in path_str.split("_")]

            value = parse_env_value(raw_value)

            # Build nested dictionary
            current = overrides
            for segment in parts[:-1]:
                current = current.setdefault(segment, {})
            current[parts[-1]] = value

        return overrides

    # ------------------------------------------------------------------
    # Persistence helpers

    def save(self, to: Optional[Path] = None) -> None:
        """Persist the current configuration to disk atomically.

        Args:
            to: Target path. If None, uses the originally located user config file.

        Examples:
            >>> from pathlib import Path
            >>> from fin_statement_model.config.manager import ConfigManager
            >>> cm = ConfigManager()
            >>> # cm.save(Path('myconfig.yaml'))  # doctest: +SKIP
        """
        with self._lock:
            cfg = self.get()

            # Determine path
            target_path = to or cfg.config_file_path
            if target_path is None:
                raise ConfigurationError(
                    "No target path specified for saving configuration"
                )

            try:
                import tempfile
                import os

                tmp_fd, tmp_path_str = tempfile.mkstemp(
                    dir=str(Path(target_path).parent)
                )
                tmp_path = Path(tmp_path_str)
                with Path(tmp_path).open("w", encoding="utf-8") as f:
                    f.write(cfg.to_yaml())
                os.close(tmp_fd)
                os.replace(tmp_path, target_path)
                logger.debug("Configuration saved to %s", target_path)
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to save configuration to %s: %s", target_path, exc)
                raise

    def reconfigure_logging(self) -> None:
        """Reapply logging configuration based on current config.

        Examples:
            >>> from fin_statement_model.config.manager import ConfigManager
            >>> cm = ConfigManager()
            >>> cm.reconfigure_logging()  # No error if config is not loaded
        """
        with self._lock:
            if self._config is None:
                return
            self._apply_logging_config()


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

    Examples:
        >>> from fin_statement_model.config.manager import update_config, get_config
        >>> update_config({'logging': {'level': 'DEBUG'}})
        >>> get_config().logging.level
        'DEBUG'
    """
    _config_manager.update(updates)


# Removed reset() method: use context manager for test isolation
