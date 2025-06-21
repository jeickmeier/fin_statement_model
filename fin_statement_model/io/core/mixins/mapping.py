"""Name-mapping utilities for IO readers.

This module hosts :class:`MappingAwareMixin`, extracted from the original
*mixins.py* file, with no behaviour changes.  It provides

1. Loading of YAML mapping files shipped under
   ``fin_statement_model/io/config/mappings`` (reader-specific default).
2. Runtime merging of default ↔ user-supplied mappings.
3. Helper to convert source column names to canonical node names.

The mixin delegates configuration access to :class:`ConfigurationMixin` – the
class must therefore appear *before* ConfigurationMixin in the MRO of concrete
readers (as already done throughout the codebase).
"""

from __future__ import annotations

from typing import ClassVar, Optional, cast
import importlib.resources
import logging

import yaml

from fin_statement_model.io.core.types import MappingConfig

logger = logging.getLogger(__name__)


class MappingAwareMixin:  # pylint: disable=too-many-public-methods
    """Reader mixin that adds YAML-driven name-mapping support."""

    # Cache of *raw* mapping YAML payload (keyed by concrete subclass name)
    _default_mappings_cache: ClassVar[dict[str, MappingConfig]] = {}

    # ---------------------------------------------------------------------
    # Methods intended for subclass override
    # ---------------------------------------------------------------------
    @classmethod
    def _get_default_mapping_path(cls) -> Optional[str]:
        """Return relative YAML path of default mappings or *None* if absent."""
        return None

    # ---------------------------------------------------------------------
    # Public helpers
    # ---------------------------------------------------------------------
    @classmethod
    def _load_default_mappings(cls) -> MappingConfig:  # noqa: D401
        """Load (and cache) mapping definitions shipped with the reader.

        Returns the parsed YAML structure (scoped or flat).  On failure an
        empty dict is returned and an *error* is logged.
        """
        cache_key = cls.__name__
        if cache_key in cls._default_mappings_cache:
            return cls._default_mappings_cache[cache_key]

        mapping_path = cls._get_default_mapping_path()
        if not mapping_path:
            cls._default_mappings_cache[cache_key] = {}
            return {}

        try:
            yaml_text = (
                importlib.resources.files("fin_statement_model.io.config.mappings")
                .joinpath(mapping_path)
                .read_text(encoding="utf-8")
            )
            parsed = yaml.safe_load(yaml_text) or {}
            cls._default_mappings_cache[cache_key] = parsed
            logger.debug("Loaded default mappings for %s", cls.__name__)
            return parsed
        except Exception:  # noqa: BLE001 – catch all file/YAML errors
            logger.exception("Failed to load default mappings for %s", cls.__name__)
            cls._default_mappings_cache[cache_key] = {}
            return {}

    # ------------------------------------------------------------------
    # Instance-level helpers (require ConfigurationMixin in MRO)
    # ------------------------------------------------------------------
    def _get_mapping(
        self, context_key: Optional[str] = None
    ) -> dict[str, str]:  # noqa: D401
        """Return *flat* mapping dict after merging defaults + user config."""
        default_map = self._load_default_mappings()
        user_cfg: MappingConfig = self.get_config_value("mapping_config")  # type: ignore[attr-defined]

        mapping = self._normalize_mapping(default_map, context_key)
        if user_cfg:
            mapping.update(self._normalize_mapping(user_cfg, context_key))
        return mapping

    @staticmethod
    def _apply_mapping(source_name: str, mapping: dict[str, str]) -> str:  # noqa: D401
        """Translate *source_name* into canonical form using *mapping*."""
        return mapping.get(source_name, source_name)

    # ------------------------------------------------------------------
    # Static utility (former io.core.utils.normalize_mapping)
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_mapping(
        mapping_config: MappingConfig | None = None, context_key: str | None = None
    ) -> dict[str, str]:
        """Flatten scoped/flat mapping into simple dict."""
        if mapping_config is None:
            return {}

        if None not in mapping_config:
            return {str(k): v for k, v in mapping_config.items() if isinstance(v, str)}

        scoped = mapping_config  # mapping is *scoped*: {None: {..}, "ctx": {..}}

        scoped_any = cast(dict[object, object], scoped)
        default_raw = scoped_any.get(None)
        default: dict[str, str]
        if isinstance(default_raw, dict):
            default = {str(k): str(v) for k, v in default_raw.items()}
        else:
            default = {}

        if (
            context_key
            and context_key in scoped
            and isinstance(scoped_any.get(context_key), dict)
        ):
            ctx_dict = cast(dict[str, str], scoped_any[context_key])
            merged = {**default, **{str(k): str(v) for k, v in ctx_dict.items()}}
            return merged
        return default


__all__ = ["MappingAwareMixin"]
