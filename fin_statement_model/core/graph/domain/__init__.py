"""Domain objects for the graph core.

The domain layer is *pure*: it defines immutable dataclasses, enums, and small
helper functions with **no side-effects** and **no external dependencies**
other than the Python standard library.  Anything that is non-deterministic or
impure belongs elsewhere.
"""

from __future__ import annotations

__all__: list[str] = [
    "Node",
    "NodeKind",
    "Period",
    "PeriodIndex",
    "Adjustment",
    "parse_inputs",
]

# Lazy imports so that downstream code importing a single type does not pay the
# import cost of every sibling module.
from importlib import import_module
from types import ModuleType
from typing import TYPE_CHECKING, Any, Mapping

if TYPE_CHECKING:  # pragma: no cover – static-type-checking only
    from fin_statement_model.core.time.period import Period, PeriodIndex

    from .adjustment import Adjustment
    from .node import Node, NodeKind, parse_inputs
else:

    def __getattr__(name: str) -> Any:
        if name in __all__:
            module_name = (
                "node"
                if name in {"Node", "NodeKind", "parse_inputs"}
                else (
                    "fin_statement_model.core.time.period"
                    if name in {"Period", "PeriodIndex"}
                    else "adjustment"
                )
            )
            # For Period helpers we import from the canonical core.time.period module.
            if module_name.startswith("fin_statement_model"):
                module: ModuleType = import_module(module_name)
            else:
                module: ModuleType = import_module(f"{__name__}.{module_name}")
            return getattr(module, name)
        raise AttributeError(name)

    def __dir__() -> Mapping[str, Any]:  # type: ignore[override]
        return sorted(globals().keys() | set(__all__))
