"""Builder helpers for the modular :pymod:`core.node_factory`.

These functions are thin wrappers that look up the concrete classes via the
registries defined in :pymod:`fin_statement_model.core.node_factory.registries`
and instantiate them.  They intentionally avoid eager imports so that importing
``fin_statement_model.core`` remains lightweight – heavy modules are only
loaded when the builders are *actually called*.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, TYPE_CHECKING, Type, cast

from fin_statement_model.core.node_factory.registries import (
    CalculationAliasRegistry,
    ForecastTypeRegistry,
    NodeTypeRegistry,
)
from fin_statement_model.core.errors import ConfigurationError

logger = logging.getLogger(__name__)

__all__: list[str] = [
    "create_financial_statement_item",
    "create_calculation_node",
    "create_forecast_node",
]

if TYPE_CHECKING:  # pragma: no cover
    from fin_statement_model.core.nodes.base import Node

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _import_calculation_node() -> Type[Any]:  # noqa: D401
    """Lazy import ``CalculationNode`` to avoid circulars at import time."""

    from fin_statement_model.core.nodes.calculation_nodes import (
        CalculationNode,
    )  # pylint: disable=import-outside-toplevel

    return CalculationNode


def _ensure_node_instance(node_obj: Any) -> None:  # noqa: D401
    """Raise if *node_obj* is not a subclass of :class:`core.nodes.Node`."""

    from fin_statement_model.core.nodes.base import (
        Node,
    )  # pylint: disable=import-outside-toplevel

    if not isinstance(node_obj, Node):
        raise TypeError("inputs must be Node instances – got %r" % type(node_obj))


# ---------------------------------------------------------------------------
# Public builders
# ---------------------------------------------------------------------------


def create_financial_statement_item(name: str, values: Dict[str, float]) -> "Node":
    """Instantiate a :class:`FinancialStatementItemNode` via the registry.

    Provided for symmetry; callers *could* import the class directly but using
    this helper makes future customisation (e.g., subclassing) transparent.
    """

    try:
        node_cls = NodeTypeRegistry.get("financial_statement_item")
    except KeyError:
        # Fallback to direct import if not registered yet (pre-decorator phase)
        from fin_statement_model.core.nodes.item_node import (
            FinancialStatementItemNode,
        )  # pylint: disable=import-outside-toplevel

        node_cls = FinancialStatementItemNode

    return cast("Node", node_cls(name, values))


def create_calculation_node(
    *,
    name: str,
    inputs: List["Node"],  # forward ref
    calculation_type: str,
    formula_variable_names: List[str] | None = None,
    **calculation_kwargs: Any,
) -> "Node":
    """Create a generic calculation node using alias lookup.

    ``calculation_type`` corresponds to the *alias* used in Graph APIs
    ("addition", "subtraction", "formula", …).
    """

    # Lazy import to avoid heavy dependency when this builder is unused
    CalculationNode = _import_calculation_node()

    # Validate inputs are Node instances
    for n in inputs:
        _ensure_node_instance(n)

    try:
        calc_cls = CalculationAliasRegistry.get(calculation_type)
    except KeyError as exc:
        raise ConfigurationError(
            f"Unknown calculation_type alias '{calculation_type}'. Registered: "
            f"{CalculationAliasRegistry.list()}"
        ) from exc

    # Special case: formula calculation needs variable names – tack them on via
    # kwargs so constructor signature remains flexible.
    if formula_variable_names is not None:
        calculation_kwargs.setdefault("input_variable_names", formula_variable_names)

    # Split kwargs between calculation-init and node extra attributes
    node_extra_kwargs = {}
    for key in ("metric_name", "metric_description"):
        if key in calculation_kwargs:
            node_extra_kwargs[key] = calculation_kwargs.pop(key)

    calculation_instance = calc_cls(**calculation_kwargs)

    return cast(
        "Node",
        CalculationNode(name, inputs, calculation_instance, **node_extra_kwargs),
    )


def create_forecast_node(
    *,
    # New modular signature ------------------------------------------------
    forecast_type: str | None = None,
    input_node: "Node" | None = None,
    base_period: str | None = None,
    forecast_periods: List[str] | None = None,
    growth_params: Any = None,
    # Legacy/alternative keywords -----------------------------------------
    name: str | None = None,  # ignored but accepted for API stability
    base_node: "Node" | None = None,  # alias for input_node
    forecast_config: Any | None = None,  # not yet supported, will raise
    **_extra: Any,
) -> "Node":
    """Instantiate a forecast node using *forecast_type* registry lookup.

    Accepts both the new modular signature and the legacy signature used by
    ``forecasting.Forecaster`` for backward compatibility.
    """

    # Map legacy parameters -------------------------------------------------
    if input_node is None and base_node is not None:
        input_node = base_node

    if forecast_config is not None:
        # TODO: parse ForecastConfig in a later iteration
        raise ConfigurationError(
            "create_forecast_node currently does not support 'forecast_config' parameter."
        )

    if forecast_type is None:
        raise ConfigurationError("'forecast_type' must be provided.")
    if input_node is None:
        raise ConfigurationError("'input_node' (or 'base_node') must be provided.")
    if base_period is None or forecast_periods is None:
        raise ConfigurationError("'base_period' and 'forecast_periods' are required.")

    _ensure_node_instance(input_node)

    try:
        forecast_cls = ForecastTypeRegistry.get(forecast_type)
    except KeyError as exc:
        raise ConfigurationError(
            f"Unknown forecast_type '{forecast_type}'. Registered: {ForecastTypeRegistry.list()}"
        ) from exc

    # Simple branching depending on constructor signature. For now we treat the
    # most common classes; if constructor signature mismatch occurs it will
    # raise TypeError which is propagated as ConfigurationError.
    try:
        if forecast_type == "simple":
            return cast(
                "Node",
                forecast_cls(input_node, base_period, forecast_periods, growth_params),
            )
        elif forecast_type == "curve":
            return cast(
                "Node",
                forecast_cls(input_node, base_period, forecast_periods, growth_params),
            )
        else:
            # For other types assume (input_node, base_period, forecast_periods, *extra)
            return cast(
                "Node",
                forecast_cls(input_node, base_period, forecast_periods, growth_params),
            )
    except TypeError as exc:
        raise ConfigurationError(
            f"Failed to instantiate forecast node for type '{forecast_type}': {exc}"
        ) from exc
