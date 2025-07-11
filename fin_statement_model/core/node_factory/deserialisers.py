"""Deserialisation helpers for modular fin_statement_model.core.node_factory.

This module provides create_from_dict, which reconstructs Node instances from their serialized dictionary
representation. The logic is registry-driven and extensible.

Example:
    >>> from fin_statement_model.core.node_factory.deserialisers import create_from_dict
    >>> # Assume dct is a valid node dict and ctx is a context dict
    >>> node = create_from_dict(dct, ctx)
    >>> node.name
    dct['name']
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

from fin_statement_model.core.errors import ConfigurationError
from fin_statement_model.core.node_factory.registries import (
    ForecastTypeRegistry,
    NodeTypeRegistry,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fin_statement_model.core.nodes.base import Node

logger = logging.getLogger(__name__)

__all__: list[str] = ["create_from_dict"]


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _get_forecast_node_cls(serialised: Mapping[str, Any]) -> type[Node]:
    """Return forecast node class based on *forecast_type* in the dict."""
    f_type = serialised.get("forecast_type") or serialised.get("growth_type")
    if f_type is None:
        raise ConfigurationError("Serialised forecast node missing 'forecast_type' key.")
    try:
        return cast("type[Node]", ForecastTypeRegistry.get(f_type))
    except KeyError as exc:
        raise ConfigurationError(
            f"Unknown forecast_type '{f_type}'. Registered: {ForecastTypeRegistry.list()}"
        ) from exc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_from_dict(
    data: dict[str, Any],
    ctx: dict[str, Node] | None = None,
    *,
    context: dict[str, Node] | None = None,
) -> Node:
    """Rebuild a Node from its serialised data.

    Args:
        data: Mapping produced by Node.to_dict().
        ctx: Existing nodes (name ➜ Node) used to resolve dependencies.
        context: Alternative keyword for backward-compatibility.

    Returns:
        Node: A live Node instance reconstructed from the dictionary.

    Raises:
        TypeError: If data is not a dict.
        ConfigurationError: If the payload is invalid or type look-up fails.

    Example:
        >>> from fin_statement_model.core.node_factory.deserialisers import create_from_dict
        >>> # Assume dct is a valid node dict and ctx is a context dict
        >>> node = create_from_dict(dct, ctx)
        >>> node.name
        dct['name']
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

    # Special dispatch for forecasts - their *sub*-type is stored separately
    if node_type_key == "forecast":
        node_cls = _get_forecast_node_cls(data)
    else:
        try:
            node_cls = NodeTypeRegistry.get(node_type_key)
        except KeyError as exc:
            raise ConfigurationError(
                f"Unknown node 'type' '{node_type_key}'. Registered: {NodeTypeRegistry.list()}"
            ) from exc

    # Use unified from_dict API
    if hasattr(node_cls, "from_dict"):
        logger.debug("Deserialising %s via from_dict", node_cls)
        return node_cls.from_dict(data, ctx)

    # If we get here the node class does not support deserialisation via factory
    raise ConfigurationError(f"Node class {node_cls.__name__} does not expose from_dict method.")
