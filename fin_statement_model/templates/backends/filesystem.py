from __future__ import annotations

"""File-system backed storage backend.

This backend reproduces the historical behaviour of persisting template
bundles under ``~/.fin_statement_model/templates`` (or the location specified
by the ``FSM_TEMPLATES_PATH`` environment variable).  The implementation is
largely adapted from the pre-refactor `TemplateRegistry` logic so that there
are *no functional regressions*.
"""

from collections.abc import Mapping
import json
import logging
import os
from pathlib import Path
import tempfile
import threading
from typing import MutableMapping

from fin_statement_model.templates.models import TemplateBundle
from .base import StorageBackend

logger = logging.getLogger(__name__)

__all__: list[str] = ["FileSystemStorageBackend"]


class FileSystemStorageBackend(StorageBackend):
    """Local file-system persistence identical to the legacy implementation."""

    _ENV_VAR: str = "FSM_TEMPLATES_PATH"
    _INDEX_FILE: str = "index.json"
    _STORE_DIR: str = "store"

    # Dedicated process-local lock – strong enough for most single host
    # scenarios.  The same limitations as the historical implementation apply
    # (it does *not* serialise access across multiple Python interpreters).
    _lock: threading.Lock = threading.Lock()

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------
    @classmethod
    def _registry_root(cls) -> Path:
        """Return path to the directory holding the registry data."""
        custom = os.getenv(cls._ENV_VAR)
        root = Path(custom).expanduser().resolve() if custom else Path.home() / ".fin_statement_model" / "templates"
        root.mkdir(parents=True, exist_ok=True)
        try:
            root.chmod(0o700)
        except PermissionError:  # pragma: no cover – best-effort only
            logger.debug("Unable to set registry root permissions; continuing anyway.")
        return root

    @classmethod
    def _index_path(cls) -> Path:
        return cls._registry_root() / cls._INDEX_FILE

    # ------------------------------------------------------------------
    # Index handling
    # ------------------------------------------------------------------
    @classmethod
    def _load_index(cls) -> MutableMapping[str, str]:
        path = cls._index_path()
        if not path.exists():
            return {}
        try:
            with path.open(encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                raise TypeError("Registry index JSON must be an object mapping template_id→relative_path.")
        except Exception:  # pragma: no cover – defensive reset
            logger.exception("Failed to parse registry index – resetting to empty.")
            return {}
        return data

    @classmethod
    def _atomic_write(cls, target: Path, payload: str) -> None:
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
        tmp_path.replace(target)

    @classmethod
    def _save_index(cls, index: Mapping[str, str]) -> None:
        cls._atomic_write(cls._index_path(), json.dumps(index, indent=2, sort_keys=True))

    # ------------------------------------------------------------------
    # Security helpers
    # ------------------------------------------------------------------
    @classmethod
    def _resolve_bundle_path(cls, rel: str | Path) -> Path:
        rel_path = Path(rel)
        if rel_path.is_absolute():
            raise ValueError("Registry index contains absolute bundle path – potential security risk.")
        if any(part == ".." for part in rel_path.parts):
            raise ValueError("Registry index contains path traversal components (..).")

        root = cls._registry_root().resolve()
        abs_path = (root / rel_path).resolve()
        abs_path.relative_to(root)  # raises if outside root
        return abs_path

    # ------------------------------------------------------------------
    # StorageBackend implementation
    # ------------------------------------------------------------------
    def list(self) -> list[str]:
        with self._lock:
            return sorted(self._load_index())

    def load(self, template_id: str) -> TemplateBundle:
        idx = self._load_index()
        try:
            rel = idx[template_id]
        except KeyError as exc:
            raise KeyError(f"Template '{template_id}' not found in registry.") from exc

        bundle_path = self._resolve_bundle_path(rel)
        with bundle_path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        return TemplateBundle.model_validate(data)

    def save(self, bundle: TemplateBundle) -> str:  # noqa: D401 – concise name preferred
        template_id = f"{bundle.meta.name}_{bundle.meta.version}"
        rel_path = Path(self._STORE_DIR) / Path(*bundle.meta.name.split(".")) / bundle.meta.version / "bundle.json"
        bundle_path = self._registry_root() / rel_path

        with self._lock:
            idx = self._load_index()
            if template_id in idx:
                raise ValueError(f"Template '{template_id}' already exists.")

            bundle_path.parent.mkdir(parents=True, exist_ok=True)
            self._atomic_write(bundle_path, json.dumps(bundle.model_dump(mode="json"), indent=2))
            idx[template_id] = rel_path.as_posix()
            self._save_index(idx)

        logger.info("Registered template '%s' (path=%s)", template_id, bundle_path)
        return template_id

    def delete(self, template_id: str) -> None:  # noqa: D401 – concise name preferred
        with self._lock:
            idx = self._load_index()
            rel_path = idx.pop(template_id, None)
            self._save_index(idx)
            if rel_path is None:
                logger.debug("Template '%s' not found – nothing to delete.", template_id)
                return

            # Best-effort clean-up of the bundle JSON and empty parent dirs
            try:
                abs_path = self._resolve_bundle_path(rel_path)
                if abs_path.exists():
                    abs_path.unlink()
                    for parent in abs_path.parent.parents:
                        try:
                            parent.rmdir()
                        except OSError:
                            break  # directory not empty – stop ascent
                        if parent == self._registry_root():
                            break
            except Exception:  # pragma: no cover – defensive
                logger.exception("Failed to remove bundle for '%s'", template_id)