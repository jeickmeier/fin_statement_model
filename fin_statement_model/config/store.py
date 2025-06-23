"""Thread-safe runtime configuration store for the financial statement model.

This module provides the `ConfigStore` class, a thread-safe container that manages
the application's configuration state. It builds upon the stateless `ConfigLoader`
by adding a mutable in-memory layer for runtime overrides.

The primary public API is exposed through the singleton instance `_runtime_store`
and its helper functions:
- `get_config()`: Returns the currently active `Config` object.
- `update_config()`: Merges a dictionary of updates into the runtime configuration.

This module is the designated place for managing stateful configuration. It is
designed to be imported by other parts of the library that need to access or
modify the global configuration.

Example:
    >>> from fin_statement_model.config import get_config, update_config
    >>> original_level = get_config().logging.level
    >>> update_config({"logging": {"level": "DEBUG"}})
    >>> get_config().logging.level
    'DEBUG'
    >>> # Restore original config for subsequent tests
    >>> update_config({"logging": {"level": original_level}})
"""

from __future__ import annotations

import logging
from pathlib import Path
import tempfile
from threading import RLock
from typing import TYPE_CHECKING, Any

from fin_statement_model.utils.merge import deep_merge

from .loader import (
    ConfigLoader,
    ConfigurationError,  # re-export for convenience
)
from .logging_hook import apply_logging_config

if TYPE_CHECKING:
    from .models import Config

logger = logging.getLogger(__name__)

__all__ = [
    "ConfigStore",
    "ConfigurationError",
    "get_config",
    "update_config",
]


class ConfigStore:
    """Manage the *current* configuration plus runtime overrides.

    The store is intentionally lightweight - it defers all loading and merging
    logic to :class:`~fin_statement_model.config.loader.ConfigLoader`, adding
    only thread-safety and a cache layer.

    Instances of this class are not typically created directly. Instead, the
    module-level singleton `_runtime_store` is used via the `get_config` and
    `update_config` helpers.
    """

    def __init__(self, *, config_file: Path | None = None):
        """Create a new ConfigStore instance.

        Args:
            config_file: Optional path to an explicit configuration file that
                should be used as the primary source.  When *None*, the loader
                follows its default lookup strategy (cwd, env var, etc.).
        """
        self._lock: RLock = RLock()
        self._loader = ConfigLoader(config_file=config_file)
        self._runtime_overrides: dict[str, Any] = {}
        self._config: Config | None = None

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get(self) -> Config:
        """Return the effective configuration, loading on-demand.

        If the configuration has not yet been loaded, this method will trigger
        the `ConfigLoader` to build it from all sources (defaults, files, env).
        The result is cached. If `update()` has been called, the cache is
        invalidated and the configuration is reloaded on the next call to `get()`.

        Returns:
            The currently active, validated `Config` instance.
        """
        with self._lock:
            if self._config is None:
                self._config = self._loader.load(runtime_overrides=self._runtime_overrides)
                # Apply logging setup whenever we (re)load configuration
                apply_logging_config(self._config)
            return self._config

    def update(self, updates: dict[str, Any]) -> None:
        """Merge `updates` into runtime overrides and invalidate the cache.

        This method performs a deep merge of the provided dictionary into the
        existing runtime overrides. After the merge, it clears the internal

        configuration cache, ensuring that the next call to `get()` will
        re-evaluate the configuration with the new overrides applied.

        It also triggers the logging hook to immediately apply any changes
        to the logging configuration.

        Args:
            updates: A dictionary of configuration values to merge.
        """
        with self._lock:
            self._runtime_overrides = deep_merge(self._runtime_overrides, updates)
            # Reset cached config → will be lazily re-loaded on next *get*.
            self._config = None

            # Apply logging immediately after updating overrides
            cfg_after = self.get()
            apply_logging_config(cfg_after)

    # ------------------------------------------------------------------
    # Persistence helpers (identical semantics to original manager)
    # ------------------------------------------------------------------

    def save(self, to: Path | None = None) -> None:
        """Persist the *current* configuration to a YAML file atomically.

        This method writes the state of the *currently active* configuration
        (including all overrides) to a YAML file. The operation is atomic,
        meaning it first writes to a temporary file and then replaces the
        target, preventing corruption if the process is interrupted.

        Args:
            to: The file path to save to. If `None`, it uses the
                `config_file_path` from the loaded configuration, if available.

        Raises:
            ConfigurationError: If no target path can be determined.
        """
        cfg = self.get()
        target_path = to or cfg.config_file_path
        if target_path is None:
            raise ConfigurationError("No target path specified for saving configuration")

        try:
            tmp_fd, tmp_path_str = tempfile.mkstemp(dir=str(Path(target_path).parent))
            tmp_path = Path(tmp_path_str)
            with tmp_path.open("w", encoding="utf-8") as f:
                f.write(cfg.to_yaml())
            # Close and replace atomically
            import os

            os.close(tmp_fd)
            tmp_path.replace(target_path)
            logger.debug("Configuration saved to %s", target_path)
        except Exception:
            # logger.exception already logs the stack trace; include path context only
            logger.exception("Failed to save configuration to %s", target_path)
            raise

    # ------------------------------------------------------------------
    # Backwards-compat private helpers (used by test suite)
    # ------------------------------------------------------------------

    def _extract_env_overrides(self) -> dict[str, Any]:
        """Expose the loader's private env parsing helper for tests."""
        return self._loader._extract_env_overrides()

    def _load_file(self, path: Path) -> dict[str, Any]:
        """Forward to ConfigLoader._load_file for tests convenience."""
        return self._loader._load_file(path)


# ------------------------------------------------------------------
# Global singleton helpers (public API)
# ------------------------------------------------------------------


_runtime_store = ConfigStore()


def get_config() -> Config:
    """Return the effective global configuration singleton.

    This is the primary helper for accessing configuration throughout the library.
    It delegates to the `get()` method of the internal `_runtime_store` singleton.

    Returns:
        The active, validated `Config` instance.
    """
    return _runtime_store.get()


def update_config(updates: dict[str, Any]) -> None:
    """Apply `updates` to the global configuration singleton.

    This is the primary helper for modifying configuration at runtime. It performs
    a deep merge of the provided dictionary into the current runtime overrides.

    Args:
        updates: A dictionary of configuration values to merge.
    """
    _runtime_store.update(updates)
