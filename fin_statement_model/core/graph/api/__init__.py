"""Public API for the graph sub-package.

Users should typically import :class:`fin_statement_model.core.graph.api.facade.GraphFacade`.
The implementation lives in private modules.  This file provides a thin re-export so that
`from fin_statement_model.core.graph.api import GraphFacade` works without importing the
entire implementation graph.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any, Mapping

__all__: list[str] = ["GraphFacade", "CalcTrace"]

if TYPE_CHECKING:
    # Import at type-checking time only to avoid heavy runtime deps.
    from .facade import GraphFacade as _GraphFacade
    from .trace import CalcTrace as _CalcTrace

    GraphFacade: type[_GraphFacade]
    CalcTrace: type[_CalcTrace]
else:
    # Lazy import to keep startup time minimal.
    def __getattr__(name: str) -> Any:
        if name in __all__:
            module = import_module(
                f"{__name__}.{'facade' if name == 'GraphFacade' else 'trace'}"
            )
            return getattr(module, name)
        raise AttributeError(name)

    def __dir__() -> Mapping[str, Any]:  # type: ignore[override]
        return sorted(globals().keys() | set(__all__))
