from __future__ import annotations

"""Ephemeral in-memory storage backend.

Intended for tests and short-lived scripting sessions where template data does
not need to persist on disk.  **Not thread-safe** beyond the single-process
`threading.Lock` provided by :pyclass:`~fin_statement_model.templates.backends.base.StorageBackend`.
"""

import copy
import threading
from typing import Dict, override

from fin_statement_model.templates.models import TemplateBundle
from .base import StorageBackend

__all__: list[str] = ["InMemoryStorageBackend"]


class InMemoryStorageBackend(StorageBackend):
    """Volatile backend that keeps all data in RAM."""

    def __init__(self) -> None:
        self._store: Dict[str, TemplateBundle] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # StorageBackend implementation
    # ------------------------------------------------------------------
    @override
    def list(self) -> list[str]:  # noqa: D401 – concise name preferred
        with self._lock:
            return sorted(self._store)

    @override
    def save(self, bundle: TemplateBundle) -> str:  # noqa: D401 – concise name preferred
        template_id = f"{bundle.meta.name}_{bundle.meta.version}"
        with self._lock:
            if template_id in self._store:
                raise ValueError(f"Template '{template_id}' already exists in backend.")
            # Deep-copy to defend against accidental mutation by callers
            self._store[template_id] = copy.deepcopy(bundle)
        return template_id

    @override
    def load(self, template_id: str) -> TemplateBundle:
        with self._lock:
            try:
                bundle = self._store[template_id]
            except KeyError as exc:
                raise KeyError(f"Template '{template_id}' not found in backend.") from exc
            # Return a defensive copy so callers cannot mutate internal state
            return copy.deepcopy(bundle)

    @override
    def delete(self, template_id: str) -> None:  # noqa: D401 – keep name short
        with self._lock:
            self._store.pop(template_id, None)