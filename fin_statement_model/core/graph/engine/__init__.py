"""Pure calculation engine and helpers for the graph core.

This package contains *stateless* and *immutable* building blocks that operate
on the domain layer.  No side-effects, no service container.
"""

from __future__ import annotations

__all__: list[str] = [
    "GraphState",
    "GraphBuilder",
    "CalculationEngine",
]

from importlib import import_module
from types import ModuleType
from typing import TYPE_CHECKING, Any, Mapping

if TYPE_CHECKING:  # pragma: no cover
    from .builder import GraphBuilder
    from .calculator import CalculationEngine
    from .state import GraphState
else:

    def __getattr__(name: str) -> Any:
        if name in __all__:
            mapping = {
                "CalculationEngine": "calculator",
                "GraphBuilder": "builder",
                "GraphState": "state",
            }
            module_name = mapping.get(name, name.lower())
            module: ModuleType = import_module(f"{__name__}.{module_name}")
            return getattr(module, name)
        raise AttributeError(name)

    def __dir__() -> Mapping[str, Any]:  # type: ignore[override]
        return sorted(globals().keys() | set(__all__))
