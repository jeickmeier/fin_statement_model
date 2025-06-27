from __future__ import annotations

"""Template storage backends.

This sub-package contains the pluggable storage backend system used by
`fin_statement_model.templates.registry.TemplateRegistry` to persist and
retrieve template bundles.  The public surface is deliberately minimal –
third-party libraries only need to implement the :class:`StorageBackend`
ABC and then configure the registry via :pyfunc:`TemplateRegistry.configure_backend`.

Available built-in backends
---------------------------
* :class:`FileSystemStorageBackend` – the default backend that replicates the
  historical behaviour of storing bundles on the local file-system under
  ``~/.fin_statement_model/templates``.
* :class:`InMemoryStorageBackend` – a lightweight, non-persistent backend
  useful for tests and ephemeral scenarios.
"""

from .base import StorageBackend  # noqa: F401 – re-export public ABC
from .filesystem import FileSystemStorageBackend  # noqa: F401
from .memory import InMemoryStorageBackend  # noqa: F401
from .s3 import S3StorageBackend  # noqa: F401 – optional dependency

__all__: list[str] = [
    "StorageBackend",
    "FileSystemStorageBackend",
    "InMemoryStorageBackend",
    "S3StorageBackend",
]