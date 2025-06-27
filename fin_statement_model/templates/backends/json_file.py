from __future__ import annotations

"""Single JSON-file storage backend.

All template bundles are stored as a JSON mapping ``template_id → bundle`` in
*one* file on disk whose location is supplied by the caller.  This removes the
complex path/index logic of the legacy file-system backend and makes it easy
for users to manage the file manually (e.g. commit to Git, edit with a text
editor, etc.).
"""

import json
import threading
from pathlib import Path
from typing import Mapping, MutableMapping, override

from .base import StorageBackend
from fin_statement_model.templates.models import TemplateBundle

__all__: list[str] = ["JsonFileStorageBackend"]


class JsonFileStorageBackend(StorageBackend):
    """Persist bundles in a single JSON file."""

    def __init__(self, file_path: str | Path):
        self._file = Path(file_path).expanduser().resolve()
        self._lock = threading.Lock()

        # Ensure parent directory exists (but do *not* create the file – it can
        # be created lazily on first save to avoid clutter).
        self._file.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load_store(self) -> MutableMapping[str, Mapping]:
        if not self._file.exists():
            return {}
        try:
            with self._file.open(encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):  # pragma: no cover
                raise TypeError("Template store JSON must be an object mapping template_id→bundle.")
            return data  # type: ignore[return-value]
        except Exception:  # pragma: no cover
            # Defensive – corrupt file.  We surface clearly instead of silently
            # wiping data.
            raise RuntimeError(f"Corrupted template store: {self._file}")

    def _save_store(self, store: Mapping[str, Mapping]) -> None:
        payload = json.dumps(store, indent=2, sort_keys=True)
        # Atomic write via temp file in same directory
        tmp = self._file.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            fh.write(payload)
        tmp.replace(self._file)

    # ------------------------------------------------------------------
    # StorageBackend implementation
    # ------------------------------------------------------------------
    @override
    def list(self) -> list[str]:
        with self._lock:
            return sorted(self._load_store())

    @override
    def save(self, bundle: TemplateBundle) -> str:
        template_id = f"{bundle.meta.name}_{bundle.meta.version}"
        with self._lock:
            store = self._load_store()
            if template_id in store:
                raise ValueError(f"Template '{template_id}' already exists in {self._file}.")
            store[template_id] = bundle.model_dump(mode="json")
            self._save_store(store)
        return template_id

    @override
    def load(self, template_id: str) -> TemplateBundle:
        with self._lock:
            store = self._load_store()
            try:
                data = store[template_id]
            except KeyError as exc:
                raise KeyError(f"Template '{template_id}' not found in {self._file}.") from exc
            return TemplateBundle.model_validate(data)

    @override
    def delete(self, template_id: str) -> None:
        with self._lock:
            store = self._load_store()
            if store.pop(template_id, None) is not None:
                self._save_store(store)