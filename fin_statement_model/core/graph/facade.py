"""User-facing *GraphFacade* wrapper.

The original :class:`fin_statement_model.core.graph.graph.Graph` class has grown
into a powerful – yet fairly large – object that mixes domain logic with
service orchestration.  To support a cleaner architecture and upcoming public
API stabilisation we introduce a **façade** that exposes only the *high-level*
verbs needed by end-users while delegating every detail to the underlying
implementation.

At the moment the façade simply **inherits** from :class:`~fin_statement_model.core.graph.graph.Graph`
to keep the migration friction minimal.  Over the next iterations we may
replace inheritance with pure delegation once the internal vs. external API
surface has been audited.

Important
~~~~~~~~~
*GraphFacade* is now the preferred import target::

    >>> from fin_statement_model.core.graph import GraphFacade

Legacy ``Graph`` imports continue to work but raise a
``DeprecationWarning`` that will turn into an error in a future major
version.
"""

from __future__ import annotations

import warnings
from typing import Optional, List, TYPE_CHECKING

# Local import – deliberately inside the function body to avoid circular deps
from fin_statement_model.core.graph.graph import Graph

# Only imported for static typing purposes to avoid runtime dependency loops
if TYPE_CHECKING:  # pragma: no cover
    from fin_statement_model.core.graph.services.container import ServiceContainer

__all__: list[str] = ["GraphFacade"]


class GraphFacade(Graph):  # pylint: disable=too-many-public-methods
    """Thin façade delegating to :class:`Graph`."""

    def __init__(
        self,
        periods: Optional[List[str]] = None,
        *,
        services: "ServiceContainer | None" = None,
    ) -> None:  # noqa: D401
        # Emit deprecation warning if legacy positional parameters of Graph are
        # used.  The façade only exposes *periods* and *services*.
        super().__init__(periods=periods, services=services)

    # ------------------------------------------------------------------
    # Future: restrict / wrap low-level methods
    # ------------------------------------------------------------------

    def __getattr__(self, item: str) -> object:  # noqa: D401
        """Delegate unknown attributes to *self* (i.e. the Graph base class)."""

        return super().__getattribute__(item)


# ----------------------------------------------------------------------
# Deprecation shim – keep *Graph* import working with a warning
# ----------------------------------------------------------------------

warnings.filterwarnings("default", category=DeprecationWarning)


def _deprecated_graph_alias(
    *args: object, **kwargs: object
) -> "GraphFacade":  # noqa: D401
    warnings.warn(
        "'Graph' has been deprecated – import 'GraphFacade' from"
        " 'fin_statement_model.core.graph' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return GraphFacade(*args, **kwargs)  # type: ignore[arg-type]


GraphAlias = _deprecated_graph_alias  # kept for explicit re-export
