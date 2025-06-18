"""
Builder helpers for the modular fin_statement_model.core.node_factory.

These functions provide registry-driven instantiation of node types, calculation nodes, and forecast nodes.
They avoid eager imports to keep the core module lightweight. All builders validate input and raise
ConfigurationError on failure.

Examples:
    >>> from fin_statement_model.core.node_factory.builders import create_financial_statement_item
    >>> node = create_financial_statement_item('Revenue', {'2022': 100.0, '2023': 120.0})
    >>> node.name
    'Revenue'
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, TYPE_CHECKING, Type, cast
import inspect  # Local import to avoid cost when builder unused

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
    """Instantiate a FinancialStatementItemNode via the registry.

    Args:
        name: The name of the financial statement item (e.g., 'Revenue').
        values: A dictionary mapping period strings to float values.

    Returns:
        Node: An instance of FinancialStatementItemNode.

    Example:
        >>> from fin_statement_model.core.node_factory.builders import create_financial_statement_item
        >>> node = create_financial_statement_item('Revenue', {'2022': 100.0})
        >>> node.name
        'Revenue'
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
    inputs: List["Node"],
    calculation_type: str,
    formula_variable_names: List[str] | None = None,
    **calculation_kwargs: Any,
) -> "Node":
    """Create a generic calculation node using alias lookup.

    Args:
        name: The name of the calculation node.
        inputs: List of input Node instances.
        calculation_type: Alias for the calculation type (e.g., 'addition', 'formula').
        formula_variable_names: Optional list of variable names for formula calculations.
        **calculation_kwargs: Additional keyword arguments for calculation or node attributes.

    Returns:
        Node: An instance of CalculationNode with the specified calculation logic.

    Raises:
        ConfigurationError: If the calculation_type is unknown or inputs are invalid.

    Example:
        >>> from fin_statement_model.core.node_factory.builders import create_calculation_node
        >>> # Assume n1, n2 are Node instances
        >>> node = create_calculation_node(name='GrossProfit', inputs=[n1, n2], calculation_type='addition')
        >>> node.name
        'GrossProfit'
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
    forecast_type: str | None = None,
    input_node: "Node" | None = None,
    base_period: str | None = None,
    forecast_periods: List[str] | None = None,
    growth_params: Any = None,
    name: str | None = None,
    base_node: "Node" | None = None,
    forecast_config: Any | None = None,
    **_extra: Any,
) -> "Node":
    """Instantiate a forecast node using forecast_type registry lookup.

    Args:
        forecast_type: The type of forecast node to create (e.g., 'simple', 'curve').
        input_node: The input Node to forecast (or use base_node for legacy).
        base_period: The base period string (e.g., '2022').
        forecast_periods: List of periods to forecast.
        growth_params: Parameters for the forecast method.
        name: (Legacy) Name of the node (ignored).
        base_node: (Legacy) Alias for input_node.
        forecast_config: (Not supported yet).
        **_extra: Additional keyword arguments (ignored).

    Returns:
        Node: An instance of the appropriate ForecastNode subclass.

    Raises:
        ConfigurationError: If required parameters are missing or instantiation fails.

    Example:
        >>> from fin_statement_model.core.node_factory.builders import create_forecast_node
        >>> # Assume n1 is a Node instance
        >>> node = create_forecast_node(forecast_type='simple', input_node=n1, base_period='2022', forecast_periods=['2023', '2024'])
        >>> node.name
        n1.name  # Typically inherits from input_node
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

    # ---------------------------------------------------------------------
    # Dynamic constructor handling via reflection
    # ---------------------------------------------------------------------
    # We inspect the __init__ signature of the forecast class to determine
    # whether it expects a fourth positional/keyword parameter (commonly
    # `growth_params`). This avoids hard-coding special cases for each
    # forecast_type and automatically works for any new classes added later.

    try:
        sig = inspect.signature(forecast_cls.__init__)
        # Drop the implicit 'self'
        ctor_params = [p for p in sig.parameters.values() if p.name != "self"]

        # Base signature is (input_node, base_period, forecast_periods)
        args: list[Any] = [input_node, base_period, forecast_periods]

        # If the constructor defines a 4th parameter OR has a parameter named
        # 'growth_params', we append growth_params as the 4th argument.
        needs_growth = False
        if len(ctor_params) > 3:
            needs_growth = True
        else:
            needs_growth = any(p.name == "growth_params" for p in ctor_params)

        if needs_growth:
            args.append(growth_params)

        return cast("Node", forecast_cls(*args))

    except TypeError as exc:
        # Provide helpful context with expected signature
        expected = [p.name for p in ctor_params]
        raise ConfigurationError(
            f"Failed to instantiate forecast node for type '{forecast_type}': {exc}\n"
            f"Constructor parameters: {expected}"
        ) from exc
