from __future__ import annotations

"""Abstract base-class for template storage backends.

Backends encapsulate the persistence layer of the
:class:`fin_statement_model.templates.registry.TemplateRegistry`.  They are
responsible *only* for storing and retrieving
:class:`fin_statement_model.templates.models.TemplateBundle` instances – all
higher-level validation and graph reconstruction remains part of the
registry itself.

Implementations **must** honour the following contract:

* Be *process-safe*.  A simple `threading.Lock` is usually sufficient for
  single-process consumers, however backends that may be accessed from
  multiple Python processes (e.g. network file-systems) need to provide
  stronger guarantees (e.g. file locks or database transactions).
* Verify the integrity of the provided bundle.  The default
  :class:`~fin_statement_model.templates.models.TemplateBundle` validator
  already checks that the SHA-256 checksum matches – backends can rely on
  this.
* Raise the same core exceptions as the historical file-system logic so that
  downstream callers remain unaffected (``ValueError``, ``KeyError``, etc.).

Only four operations are required – this keeps the surface minimal while
still covering the full lifecycle.  Additional optional helper methods can
be added in the future (e.g. `update`, `search`, etc.).
"""

import abc
import threading
from typing import Protocol, runtime_checkable

from fin_statement_model.templates.models import TemplateBundle

__all__: list[str] = ["StorageBackend"]


# ---------------------------------------------------------------------------
# The public StorageBackend protocol – runtime_checkable so it can be used
# safely with ``isinstance`` / ``issubclass`` in client code.
# ---------------------------------------------------------------------------

@runtime_checkable
class StorageBackend(Protocol):
    """Pluggable persistence strategy for the template registry."""

    # ------------------------------------------------------------------
    # Mandatory interface
    # ------------------------------------------------------------------
    @abc.abstractmethod
    def list(self) -> list[str]:
        """Return **sorted** list of registered template identifiers."""

    @abc.abstractmethod
    def save(self, bundle: TemplateBundle) -> str:  # noqa: D401 – keep name short
        """Persist *bundle* and return its canonical ``template_id``.

        Backends **must** raise ``ValueError`` if the given identifier already
        exists – this ensures the registry can detect duplicates reliably.
        """

    @abc.abstractmethod
    def load(self, template_id: str) -> TemplateBundle:
        """Return the stored :class:`TemplateBundle` for *template_id*.

        Must raise ``KeyError`` if the identifier is unknown.
        """

    @abc.abstractmethod
    def delete(self, template_id: str) -> None:
        """Permanently remove *template_id* and its data.

        Must *not* raise when the identifier does **not** exist – this matches
        the pre-refactor semantics which allowed callers to attempt best-effort
        clean-up.
        """

    # ------------------------------------------------------------------
    # Optional helpers – provided for convenience but not part of the
    # mandatory contract.  Concrete backends may choose to expose additional
    # operations which callers can utilise via :pyfunc:`isinstance` checks.
    # ------------------------------------------------------------------

    # A shared lock that naïve implementations can reuse to serialise access
    # in a single Python process.  Multi-process backends should override this
    # with a stronger mechanism.
    _lock: threading.Lock = threading.Lock()