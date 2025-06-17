"""Deserialisation helper for modular :pymod:`core.node_factory`.

`create_from_dict` rebuilds a :class:`~fin_statement_model.core.nodes.base.Node`
instance from its serialised representation (typically produced by
``node.to_dict()``).  The logic is registry-driven and open for extension – no
hard-coded `if/elif` chains are required for core node types that register
themselves via the decorators in :pymod:`fin_statement_model.core.node_factory.registries`.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Mapping, cast, Type

from fin_statement_model.core.errors import ConfigurationError
from fin_statement_model.core.node_factory.registries import (
    ForecastTypeRegistry,
    NodeTypeRegistry,
)
from fin_statement_model.core.nodes.base import Node

logger = logging.getLogger(__name__)

__all__: list[str] = ["create_from_dict"]


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _get_forecast_node_cls(serialised: Mapping[str, Any]) -> type[Node]:  # noqa: D401
    """Return forecast node class based on *forecast_type* in the dict."""

    f_type = serialised.get("forecast_type") or serialised.get("growth_type")
    if f_type is None:
        raise ConfigurationError(
            "Serialised forecast node missing 'forecast_type' key."
        )
    try:
        return cast(Type[Node], ForecastTypeRegistry.get(f_type))
    except KeyError as exc:
        raise ConfigurationError(
            f"Unknown forecast_type '{f_type}'. Registered: {ForecastTypeRegistry.list()}"
        ) from exc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_from_dict(
    data: Dict[str, Any],
    ctx: Dict[str, Node] | None = None,
    *,
    context: Dict[str, Node] | None = None,
) -> Node:
    """Rebuild a Node from its serialised *data*.

    Args:
        data: Mapping produced by ``Node.to_dict()``.
        ctx: Existing nodes (name ➜ Node) used to resolve dependencies.
        context: Alternative keyword for backward-compatibility.

    Returns:
        A live :class:`~fin_statement_model.core.nodes.base.Node` instance.

    Raises:
        ConfigurationError: If the payload is invalid or type look-up fails.
    """

    # Support alternative keyword ``context`` for backward-compat
    if ctx is None and context is not None:
        ctx = context
    if ctx is None:
        ctx = {}

    if not isinstance(data, dict):
        raise TypeError("create_from_dict: 'data' must be a dict")

    node_type_key = data.get("type")
    if not node_type_key or not isinstance(node_type_key, str):
        raise ConfigurationError("Serialised node missing 'type' field.")

    # Special dispatch for forecasts – their *sub*-type is stored separately
    if node_type_key == "forecast":
        node_cls = _get_forecast_node_cls(data)
    else:
        try:
            node_cls = NodeTypeRegistry.get(node_type_key)
        except KeyError as exc:
            raise ConfigurationError(
                f"Unknown node 'type' '{node_type_key}'. Registered: {NodeTypeRegistry.list()}"
            ) from exc

    # Choose appropriate constructor helper
    if hasattr(node_cls, "from_dict_with_context"):
        logger.debug("Deserialising %s via from_dict_with_context", node_cls)
        return cast(Node, node_cls.from_dict_with_context(data, ctx))
    elif hasattr(node_cls, "from_dict"):
        logger.debug("Deserialising %s via from_dict", node_cls)
        return cast(Node, node_cls.from_dict(data))

    # If we get here the node class does not support deserialisation via factory
    raise ConfigurationError(
        f"Node class {node_cls.__name__} does not expose from_dict[_with_context] methods."
    )
