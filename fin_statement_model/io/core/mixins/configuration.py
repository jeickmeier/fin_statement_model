"""Configuration utilities extracted from the legacy *mixins.py*.

Provides :class:`ConfigurationMixin` that supplies readers/writers with
helper methods for validating and accessing their pydantic configuration
objects, handling runtime overrides and env-var fallbacks.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional, TYPE_CHECKING

from fin_statement_model.io.exceptions import ReadError
from fin_statement_model.config.access import parse_env_value

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover – import solely for type checking
    from .validation import ValidationResultCollector


class ConfigurationMixin:  # pylint: disable=too-many-public-methods
    """Mixin that offers safe, validated access to reader/writer config objects."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401
        super().__init__(*args, **kwargs)

        # ------------------------------------------------------------------
        # Internal state
        # ------------------------------------------------------------------
        # _config_context – free-form metadata that *callers* can attach to the
        # mixin to improve log messages and error reporting (e.g. ticker="AAPL",
        # operation="api_read").  It **does not** influence behaviour besides
        # being emitted via :pymeth:`ValidationResultCollector` summaries.
        #
        # _config_overrides – runtime key→value map injected via
        # :pymeth:`set_config_override`.  When present, it *silently* overrides
        # the value returned by :pymeth:`get_config_value`.  This mechanism is
        # only required when the same reader/writer instance is reused with
        # different per-call overrides (see planned batched-API support).
        #
        # Both attributes are **advanced** features.  They are kept private and
        # undocumented in the public API.  If you are maintaining code outside
        # this package, prefer passing per-call kwargs to `.read()` / `.write()`
        # instead of using overrides directly.
        # ------------------------------------------------------------------

        self._config_context: dict[str, Any] = {}
        self._config_overrides: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Context helpers
    # ------------------------------------------------------------------
    def set_config_context(self, **context: Any) -> None:
        """Set key-value pairs in the configuration context."""
        self._config_context.update(context)

    def get_config_context(self) -> dict[str, Any]:
        """Get a copy of the configuration context."""
        return self._config_context.copy()

    # ------------------------------------------------------------------
    # Override helpers
    # ------------------------------------------------------------------
    def set_config_override(self, key: str, value: Any) -> None:
        """Set a runtime configuration override."""
        self._config_overrides[key] = value

    def clear_config_overrides(self) -> None:
        """Clear all runtime configuration overrides."""
        self._config_overrides.clear()

    # ------------------------------------------------------------------
    # Value retrieval
    # ------------------------------------------------------------------
    def get_config_value(
        self,
        key: str,
        default: Any = None,
        *,
        required: bool = False,
        value_type: Optional[type] = None,
        validator: Optional[Callable[[Any], bool]] = None,
    ) -> Any:
        """Get a configuration value, with optional validation."""
        # ------------------------------------------------------------------
        # Defensive guard – ensure internal attributes exist even if the
        # concrete reader/writer forgot to call ``ConfigurationMixin.__init__``
        # in its own ``__init__`` implementation.  This avoids cryptic
        # AttributeError crashes (see issue #csv_reader_init) and degrades
        # gracefully by falling back to an empty override/context mapping.
        # ------------------------------------------------------------------
        if not hasattr(self, "_config_overrides"):
            # Late-initialise missing attributes to keep behaviour predictable.
            self._config_overrides = {}
        if not hasattr(self, "_config_context"):
            self._config_context = {}

        # Override precedence
        if key in self._config_overrides:
            value = self._config_overrides[key]
        elif hasattr(self, "cfg") and self.cfg is not None:
            value = getattr(self.cfg, key, default)
        else:
            value = default

        # Required check
        if required and value is None:
            raise ReadError(
                f"Required configuration value '{key}' is missing",
                reader_type=self.__class__.__name__,
            )

        # Type coercion
        if (
            value is not None
            and value_type is not None
            and not isinstance(value, value_type)
        ):
            try:
                value = value_type(value)
            except (ValueError, TypeError) as exc:
                raise ReadError(
                    f"Configuration value '{key}' has invalid type. Expected {value_type.__name__}, got {type(value).__name__}",
                    reader_type=self.__class__.__name__,
                    original_error=exc,
                ) from exc

        # Custom validator
        if value is not None and validator is not None:
            try:
                if not validator(value):
                    raise ReadError(
                        f"Configuration value '{key}' failed validation",
                        reader_type=self.__class__.__name__,
                    )
            except Exception as exc:
                raise ReadError(
                    f"Configuration validation error for '{key}': {exc}",
                    reader_type=self.__class__.__name__,
                    original_error=exc,
                ) from exc

        return value

    def require_config_value(
        self,
        key: str,
        *,
        value_type: Optional[type] = None,
        validator: Optional[Callable[[Any], bool]] = None,
    ) -> Any:
        """Get a required configuration value."""
        return self.get_config_value(
            key, required=True, value_type=value_type, validator=validator
        )

    # ------------------------------------------------------------------
    # Env var fallback helper
    # ------------------------------------------------------------------
    def get_config_with_env_fallback(
        self,
        key: str,
        env_var: str,
        *,
        default: Any = None,
        value_type: Optional[type] = None,
    ) -> Any:
        """Get a configuration value, falling back to an environment variable."""
        import os

        value = self.get_config_value(key)

        # Fallback to environment variable if config value is missing
        if value is None:
            env_raw = os.getenv(env_var)
            if env_raw is not None:
                value = parse_env_value(env_raw)

        # Apply default as last resort
        if value is None:
            value = default

        if (
            value is not None
            and value_type is not None
            and not isinstance(value, value_type)
        ):
            try:
                value = value_type(value)
            except (ValueError, TypeError):
                logger.warning(
                    "Failed to convert %s value '%s' to %s; using as-is",
                    key,
                    value,
                    value_type.__name__,
                )
        return value

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------
    def validate_configuration(self) -> "ValidationResultCollector":
        """Validate the handler's configuration object."""
        collector = ValidationResultCollector(context=self._config_context)
        if not hasattr(self, "cfg") or self.cfg is None:
            collector.add_result(
                "configuration", False, "Missing configuration object", "structure"
            )
            return collector
        try:
            if hasattr(self.cfg, "model_validate"):
                collector.add_result(
                    "configuration", True, "Configuration object is valid", "structure"
                )
            else:
                collector.add_result(
                    "configuration",
                    True,
                    "Configuration object exists (non-Pydantic)",
                    "structure",
                )
        except Exception as exc:  # noqa: BLE001
            collector.add_result(
                "configuration",
                False,
                f"Configuration validation failed: {exc}",
                "validation",
            )
        return collector

    def get_effective_configuration(self) -> dict[str, Any]:
        """Get the effective configuration, including overrides."""
        cfg_dict: dict[str, Any] = {}
        if hasattr(self, "cfg") and self.cfg is not None:
            if hasattr(self.cfg, "model_dump"):
                cfg_dict = self.cfg.model_dump()
            elif hasattr(self.cfg, "__dict__"):
                cfg_dict = vars(self.cfg).copy()
        cfg_dict.update(self._config_overrides)
        return cfg_dict

    def merge_configurations(self, *configs: Any) -> dict[str, Any]:
        """Recursively merge multiple configuration sources.

        This helper converts all supported *config* objects into plain
        dictionaries and then applies :func:`fin_statement_model.utils.merge.deep_merge`
        to ensure a consistent, **deep** merge semantics across the code-base.

        Args:
            *configs: Arbitrary configuration objects. Supported types are
                ``dict``-like, Pydantic models (``.model_dump``) and objects with
                a ``__dict__`` attribute.

        Returns:
            A new dictionary representing the recursively merged configuration.
        """

        from fin_statement_model.utils.merge import (
            deep_merge,
        )  # Local import to avoid circular deps

        merged: dict[str, Any] = {}

        for cfg in configs:
            if cfg is None:
                continue

            # ------------------------------------------------------------------
            # Normalise input → plain dict
            # ------------------------------------------------------------------
            if hasattr(cfg, "model_dump"):
                cfg_dict = cfg.model_dump()
            elif isinstance(cfg, dict):
                cfg_dict = cfg
            elif hasattr(cfg, "__dict__"):
                cfg_dict = vars(cfg)
            else:
                logger.warning(
                    "Unsupported configuration type for merge: %s", type(cfg)
                )
                continue

            # ------------------------------------------------------------------
            # Deep-merge into the accumulator
            # ------------------------------------------------------------------
            merged = deep_merge(merged, cfg_dict)

        return merged


__all__ = ["ConfigurationMixin"]
