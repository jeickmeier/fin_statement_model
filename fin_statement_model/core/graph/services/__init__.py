"""Graph service layer (dependency injection).

Services provide side-effecting capabilities (e.g., caching, period
normalisation) that are orchestrated by the imperative shell.  They **MUST NOT**
be imported by pure layers (`domain`, `engine`).
"""

from __future__ import annotations

__all__: list[str] = [
    "AdjustmentService",
    "PeriodService",
    "MetricService",
]

from importlib import import_module
from types import ModuleType
from typing import TYPE_CHECKING, Any, Mapping

if TYPE_CHECKING:  # pragma: no cover
    from .adjustments import AdjustmentService
    from .periods import PeriodService
else:

    def __getattr__(name: str) -> Any:
        if name in __all__:
            module_name = (
                "adjustments"
                if name == "AdjustmentService"
                else "periods" if name == "PeriodService" else "metrics"
            )
            module: ModuleType = import_module(f"{__name__}.{module_name}")
            return getattr(module, name)
        raise AttributeError(name)

    def __dir__() -> Mapping[str, Any]:  # type: ignore[override]
        return sorted(globals().keys() | set(__all__))
