"""Service container for the *fin_statement_model* graph layer.

This lightweight dataclass aggregates **service classes** used by the
``Graph`` implementation so that dependency-injection can be performed with a
single argument instead of passing every individual service class.  It does
*not* instantiate the services because most services require collaborator
callables from a concrete ``Graph`` instance.  Therefore the container stores
**class objects** (or callables returning class objects) that the graph will
instantiate *after* it has constructed the required collaborators.

Examples
--------
Basic usage with all defaults::

    >>> from fin_statement_model.core.graph.services.container import ServiceContainer
    >>> container = ServiceContainer()  # every attribute is set to its default class

Customising one service while keeping the rest::

    >>> from fin_statement_model.core.graph.services import CalculationEngine
    >>> class TracingCalcEngine(CalculationEngine):
    ...     ...  # custom behaviour here
    >>> custom = ServiceContainer(calc_engine=TracingCalcEngine)

The container is **frozen** and **slot-based** for fast attribute access and to
avoid accidental mutation after creation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

from fin_statement_model.core.graph.services.adjustment_service import (
    AdjustmentService,
)

# Import service classes.  These are lightweight at import-time and avoid heavy
# runtime work, so pulling them into the module top-level is acceptable.
from fin_statement_model.core.graph.services.calculation_engine import (
    CalculationEngine,
)
from fin_statement_model.core.graph.services.data_item_service import (
    DataItemService,
)
from fin_statement_model.core.graph.services.introspector import GraphIntrospector
from fin_statement_model.core.graph.services.merge_service import MergeService
from fin_statement_model.core.graph.services.node_registry import (
    NodeRegistryService,
)
from fin_statement_model.core.graph.services.period_service import PeriodService

__all__: list[str] = ["ServiceContainer"]


@dataclass(slots=True, frozen=True)
class ServiceContainer:  # pylint: disable=too-many-instance-attributes
    """Aggregate **service class references** for the graph layer.

    Each attribute refers to the **class** (not an instance) that implements
    the corresponding service.  The graph implementation will instantiate the
    classes with the collaborators it constructs internally.
    """

    calc_engine: type[CalculationEngine] = field(
        default_factory=lambda: CalculationEngine
    )
    period_service: type[PeriodService] = field(default_factory=lambda: PeriodService)
    adjustment_service: type[AdjustmentService] = field(
        default_factory=lambda: AdjustmentService
    )
    data_item_service: type[DataItemService] = field(
        default_factory=lambda: DataItemService
    )
    merge_service: type[MergeService] = field(default_factory=lambda: MergeService)
    introspector: type[GraphIntrospector] = field(
        default_factory=lambda: GraphIntrospector
    )
    registry_service: type[NodeRegistryService] = field(
        default_factory=lambda: NodeRegistryService
    )

    # ------------------------------------------------------------------
    # Helper dunder methods
    # ------------------------------------------------------------------
    def replace(self, **kwargs: object) -> "ServiceContainer":
        """Return a *new* container with the provided attributes replaced.

        This mirrors :pyfunc:`dataclasses.replace` but keeps the method local to
        avoid an extra import.
        """

        data: dict[str, object] = {
            fld.name: getattr(self, fld.name)
            for fld in self.__dataclass_fields__.values()
        }
        data.update(kwargs)
        return ServiceContainer(**data)  # type: ignore[arg-type]

    # Keep container iterable for convenience (rarely used) ----------------
    def __iter__(self) -> "Iterator[type[object]]":
        """Iterate over the *class* objects in a deterministic order."""

        yield self.calc_engine
        yield self.period_service
        yield self.adjustment_service
        yield self.data_item_service
        yield self.merge_service
        yield self.introspector
        yield self.registry_service
