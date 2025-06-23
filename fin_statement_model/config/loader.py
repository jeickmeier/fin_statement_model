"""Pure configuration loading/merging logic for `fin_statement_model`.

This module is intentionally **side-effect free** except for *reading* the
filesystem and environment variables. It does **not** mutate global state or
re-configure logging.

Its primary export is the `ConfigLoader` class, which is responsible for:
1.  Discovering configuration files (`.fsm_config.yaml`, `fsm_config.yaml`).
2.  Loading `.env` files.
3.  Parsing environment variables (prefixed with `FSM_`).
4.  Merging all sources in the correct order of precedence.
5.  Returning a validated `Config` object.

This class is used internally by the `ConfigStore` and is not typically
instantiated directly by end-users.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, cast
import logging
import os

from fin_statement_model.core.errors import FinStatementModelError
from fin_statement_model.utils.merge import deep_merge

from .models import Config
from .access import parse_env_value
from .access import parse_env_var

logger = logging.getLogger(__name__)

__all__ = [
    "ConfigurationError",
    "ConfigLoader",
]


class ConfigurationError(FinStatementModelError):
    """Exception raised for configuration-related errors."""


class ConfigLoader:
    """Load and merge configuration from all supported sources.

    The loader is **stateless**: each call to `load()` inspects the environment
    and filesystem afresh, returning a fully validated `Config` object. It
    follows a strict precedence order:
    Defaults < Project Config < User Config < .env < Environment < Runtime Overrides.
    """

    # --- Constants ---------------------------------------------------------
    ENV_PREFIX = "FSM_"
    USER_CONFIG_FILE = "fsm_config.yaml"
    PROJECT_CONFIG_FILE = ".fsm_config.yaml"

    # ---------------------------------------------------------------------
    # Construction helpers
    # ---------------------------------------------------------------------

    def __init__(self, config_file: Optional[Path] = None):
        """Create a new :class:`ConfigLoader`.

        Args:
            config_file: Optional path explicitly pointing to the *user* config
                file that should override the discovery algorithm.
        """
        self._config_file = config_file

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------

    def load(self, runtime_overrides: Optional[dict[str, Any]] | None = None) -> Config:
        """Load, merge, and validate configuration from all sources.

        This is the main entry point for the class. It orchestrates the
        layered merge and returns the final, validated configuration.

        Args:
            runtime_overrides: A dictionary of values to be merged with the
                highest precedence, overriding all other sources.

        Returns:
            A validated `Config` instance representing the effective configuration.
        """
        # Ensure .env variables are made available before we inspect os.environ.
        self._load_dotenv()

        # Start with defaults defined by the *Config* pydantic model.
        config_dict: dict[str, Any] = Config(
            project_name="fin_statement_model",
            config_file_path=None,
            auto_save_config=False,
        ).to_dict()

        # Layer 1 – project-level config
        if (project_cfg := self._find_project_config()) is not None:
            logger.debug("Loading project config from %s", project_cfg)
            config_dict = deep_merge(config_dict, self._load_file(project_cfg))

        # Layer 2 – user-level config
        if (user_cfg := self._find_user_config()) is not None:
            logger.debug("Loading user config from %s", user_cfg)
            config_dict = deep_merge(config_dict, self._load_file(user_cfg))

        # Layer 3 – environment overrides
        env_overrides = self._extract_env_overrides()
        if env_overrides:
            logger.debug("Applying environment variable overrides")
            config_dict = deep_merge(config_dict, env_overrides)

        # Layer 4 – runtime overrides
        if runtime_overrides:
            logger.debug("Applying runtime overrides (in-memory)")
            config_dict = deep_merge(config_dict, runtime_overrides)

        # Validate and return
        return Config.from_dict(config_dict)

    # ---------------------------------------------------------------------
    # Discovery helpers (private)
    # ---------------------------------------------------------------------

    def _find_project_config(self) -> Optional[Path]:
        """Locate the project-level config file (``.fsm_config.yaml``)."""
        current = Path.cwd()
        while current != current.parent:
            candidate = current / self.PROJECT_CONFIG_FILE
            if candidate.exists():
                return candidate
            current = current.parent
        return None

    def _find_user_config(self) -> Optional[Path]:
        """Locate the user-level config file (``fsm_config.yaml``)."""
        if self._config_file and self._config_file.exists():
            return self._config_file

        # Look in current working directory first
        cwd_cfg = Path.cwd() / self.USER_CONFIG_FILE
        if cwd_cfg.exists():
            return cwd_cfg

        # Fallback to *home*.
        home_cfg = Path.home() / f".{self.USER_CONFIG_FILE}"
        if home_cfg.exists():
            return home_cfg
        return None

    # ------------------------------------------------------------------
    # File loaders (static)
    # ------------------------------------------------------------------

    @staticmethod
    def _load_file(path: Path) -> dict[str, Any]:
        """Load configuration from a YAML or JSON file."""
        try:
            if path.suffix in {".yaml", ".yml"}:
                import yaml

                result = yaml.safe_load(path.read_text()) or {}
                return cast(dict[str, Any], result)
            if path.suffix == ".json":
                import json

                result = json.loads(path.read_text())
                return cast(dict[str, Any], result)
            raise ConfigurationError(f"Unsupported config file format: {path.suffix}")
        except Exception as exc:  # noqa: BLE001
            raise ConfigurationError(
                f"Failed to load config from {path}: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Environment variable helpers (static)
    # ------------------------------------------------------------------

    @classmethod
    def _extract_env_overrides(cls) -> dict[str, Any]:
        """Convert ``FSM_*`` environment variables into a nested dict."""
        overrides: dict[str, Any] = {}

        for key, raw_value in os.environ.items():
            if not key.startswith(cls.ENV_PREFIX):
                continue

            parts = parse_env_var(key, prefix=cls.ENV_PREFIX)
            value = parse_env_value(raw_value)

            current: dict[str, Any] = overrides
            for segment in parts[:-1]:
                current = current.setdefault(segment, {})
            current[parts[-1]] = value

        return overrides

    # ------------------------------------------------------------------
    # .env handling (static)
    # ------------------------------------------------------------------

    @staticmethod
    def _load_dotenv() -> None:  # noqa: C901
        """Populate ``os.environ`` from the first ``.env`` file found upward."""
        try:
            current = Path.cwd()
            while True:
                candidate = current / ".env"
                if candidate.exists() and candidate.is_file():
                    try:
                        for raw_line in candidate.read_text().splitlines():
                            line = raw_line.strip()
                            # Skip blanks & comments
                            if not line or line.startswith("#"):
                                continue
                            if "=" not in line:
                                continue
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip().strip("'\"")
                            if key and key not in os.environ:
                                os.environ[key] = value
                        logger.debug("Loaded environment variables from %s", candidate)

                        # Backwards-compat mapping for FMP_API_KEY
                        if (
                            "FMP_API_KEY" in os.environ
                            and "FSM_API__FMP_API_KEY" not in os.environ
                        ):
                            os.environ["FSM_API__FMP_API_KEY"] = os.environ[
                                "FMP_API_KEY"
                            ]
                        break  # only first .env counts
                    except Exception as err:  # noqa: BLE001
                        logger.warning(
                            "Failed to load .env file %s: %s", candidate, err
                        )
                # ascend until root
                if current.parent == current:
                    break
                current = current.parent
        except Exception as err:  # noqa: BLE001
            logger.debug("_load_dotenv encountered an error: %s", err, exc_info=False)
