"""Filesystem-backed Template Registry implementation.

This module provides a minimal, *local-only* registry that can:
1. Persist a :class:`~fin_statement_model.core.graph.Graph` to disk as a
   :class:`~fin_statement_model.templates.models.TemplateBundle`.
2. Maintain a JSON index for quick discovery.
3. Retrieve previously registered bundles.

It purposefully **does not** implement cloning, diffing or remote storage - these
features will be introduced in later roadmap PRs.
"""

from collections.abc import Mapping, MutableMapping
import json
import logging
import os
from pathlib import Path
import tempfile
import threading  # thread-safety
from typing import Any, cast

from fin_statement_model.core.graph import Graph
from fin_statement_model.io import write_data
from fin_statement_model.templates.models import (
    TemplateBundle,
    TemplateMeta,
    _calculate_sha256_checksum,
)

logger = logging.getLogger(__name__)

__all__: list[str] = [
    "TemplateRegistry",
]

_INDEX_LOCK = threading.Lock()  # process-level lock safeguarding index writes

class TemplateRegistry:
    """Local filesystem-backed template registry (singleton-style class)."""

    _ENV_VAR: str = "FSM_TEMPLATES_PATH"
    _INDEX_FILE: str = "index.json"
    _STORE_DIR: str = "store"

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------
    @classmethod
    def _registry_root(cls) -> Path:
        """Return the root directory used to persist registry data.

        Precedence order:
        1. Environment variable ``FSM_TEMPLATES_PATH`` (absolute or relative).
        2. ``~/.fin_statement_model/templates`` default.
        The directory is created on first access with POSIX permissions ``0700``
        to ensure private storage of potentially sensitive financial data.
        """
        custom = os.getenv(cls._ENV_VAR)
        root = Path(custom).expanduser().resolve() if custom else Path.home() / ".fin_statement_model" / "templates"
        # `mkdir` is no-op if the directory already exists.
        root.mkdir(parents=True, exist_ok=True)
        try:
            root.chmod(0o700)
        except PermissionError:  # pragma: no cover - best effort on non-POSIX
            logger.debug("Unable to set registry root permissions; continuing anyway.")
        return root

    @classmethod
    def _index_path(cls) -> Path:
        return cls._registry_root() / cls._INDEX_FILE

    # ------------------------------------------------------------------
    # Index helpers
    # ------------------------------------------------------------------
    @classmethod
    def _load_index(cls) -> MutableMapping[str, str]:
        """Load registry index from disk or return empty mapping."""
        idx_path = cls._index_path()
        if not idx_path.exists():
            return {}
        try:
            with idx_path.open(encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                raise TypeError("Registry index JSON must be an object mapping template_id→relative_path.")
        except Exception:  # pragma: no cover - defensive, should never occur in tests
            logger.exception("Failed to parse registry index - resetting to empty.")
            return {}
        else:
            return data

    @classmethod
    def _atomic_write(cls, target: Path, payload: str) -> None:
        """Atomically write *payload* text to *target* path (600 perms)."""
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", dir=str(target.parent), delete=False, encoding="utf-8") as tmp:
            tmp.write(payload)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = Path(tmp.name)
        try:
            tmp_path.chmod(0o600)
        except PermissionError:  # pragma: no cover
            logger.debug("Unable to set permissions on temp file; continuing anyway.")
        # `Path.replace` is atomic on POSIX and Windows (NTFS)
        tmp_path.replace(target)

    @classmethod
    def _save_index(cls, index: Mapping[str, str]) -> None:
        """Persist *index* mapping atomically."""
        payload = json.dumps(index, indent=2, sort_keys=True)
        cls._atomic_write(cls._index_path(), payload)

    # ------------------------------------------------------------------
    # Public API - foundational subset (list / register / get)
    # ------------------------------------------------------------------
    @classmethod
    def list(cls) -> list[str]:
        """Return sorted list of registered template identifiers."""
        return sorted(cls._load_index())

    @classmethod
    def _resolve_next_version(cls, name: str, existing_index: Mapping[str, str]) -> str:
        """Return the next semantic version tag ("v<int>")."""
        prefix = f"{name}_v"
        max_ver = 0
        for key in existing_index:
            if key.startswith(prefix):
                try:
                    candidate = int(key[len(prefix) :])
                    max_ver = max(max_ver, candidate)
                except ValueError:
                    continue
        return f"v{max_ver + 1}"

    @classmethod
    def register_graph(
        cls,
        graph: Graph,
        *,
        name: str,
        version: str | None = None,
        meta: Mapping[str, Any] | None = None,
    ) -> str:
        """Register *graph* under *name* returning the full template identifier.

        Args:
            graph: Graph instance to persist.
            name: Template name, e.g. ``"lbo.standard"``.
            version: Explicit semantic version ("v1" / "v2"). If *None*, the
                next minor version is calculated automatically.
            meta: Optional additional metadata fields. Keys ``name``,
                ``version`` and ``category`` are filled in automatically and override
                duplicates.

        Returns:
            The canonical template identifier (e.g. ``"lbo.standard_v1"``).
        """
        if not name or not isinstance(name, str):
            raise TypeError("Template name must be a non-empty string.")

        with _INDEX_LOCK:
            index = cls._load_index()
            if version is None:
                version = cls._resolve_next_version(name, index)

            template_id = f"{name}_{version}"
            if template_id in index:
                raise ValueError(f"Template '{template_id}' already exists.")

            # ------------------------------------------------------------------
            # Build filesystem path (store/<name>/<version>/bundle.json)
            # ------------------------------------------------------------------
            rel_path = Path(cls._STORE_DIR) / Path(*name.split(".")) / version / "bundle.json"
            bundle_path = cls._registry_root() / rel_path
            bundle_path.parent.mkdir(parents=True, exist_ok=True)

            # ------------------------------------------------------------------
            # Serialize graph ➜ dict ➜ TemplateBundle ➜ JSON
            # ------------------------------------------------------------------
            graph_dict = cast("dict[str, Any]", write_data("graph_definition_dict", graph, target=None))
            checksum = _calculate_sha256_checksum(graph_dict)

            meta_payload: dict[str, Any] = {
                "name": name,
                "version": version,
                "category": meta.get("category") if meta else name.split(".")[0],
            }
            if meta:
                meta_payload.update(meta)

            bundle = TemplateBundle(meta=TemplateMeta.model_validate(meta_payload), graph_dict=graph_dict, checksum=checksum)
            payload = json.dumps(bundle.model_dump(mode="json"), indent=2)

            # Atomic write of bundle then update index
            cls._atomic_write(bundle_path, payload)

            # Update index in-memory and persist
            index[template_id] = rel_path.as_posix()
            cls._save_index(index)

            logger.info("Registered template '%s' (path=%s)", template_id, bundle_path)
            return template_id

    @classmethod
    def get(cls, template_id: str) -> TemplateBundle:
        """Return :class:`TemplateBundle` for *template_id*.

        Raises ``KeyError`` if *template_id* is unknown.
        """
        index = cls._load_index()
        try:
            rel = index[template_id]
        except KeyError as exc:  # pragma: no cover - explicit failure expected in tests
            raise KeyError(f"Template '{template_id}' not found in registry.") from exc
        bundle_path = cls._registry_root() / rel
        with bundle_path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        return TemplateBundle.model_validate(data)
