"""Custom helper utilities for the modular NodeFactory.

Currently houses ``_create_custom_node_from_callable`` which wraps a Python
callable in a :class:`~fin_statement_model.core.nodes.CustomCalculationNode`.
"""

from __future__ import annotations

from typing import Callable, List

from fin_statement_model.core.errors import CalculationError
from fin_statement_model.core.nodes.calculation_nodes import CustomCalculationNode
from fin_statement_model.core.nodes.base import Node

__all__: list[str] = ["_create_custom_node_from_callable"]


def _create_custom_node_from_callable(
    *,
    name: str,
    inputs: List[Node],
    formula: Callable[..., float],
    description: str | None = None,
) -> CustomCalculationNode:
    """Wrap a *formula* callable in a :class:`CustomCalculationNode`.

    This helper merely validates inputs and delegates to the node constructor –
    it exists so that higher-level code (e.g., :class:`CalculationEngine`) can
    stay agnostic of the concrete node class.
    """

    # Basic validation ----------------------------------------------------
    if not callable(formula):
        raise TypeError("formula must be a callable object returning float")

    for n in inputs:
        if not isinstance(n, Node):
            raise TypeError(
                "All items in 'inputs' must be Node instances; got %r" % type(n)
            )

    try:
        return CustomCalculationNode(
            name,
            inputs=inputs,
            formula_func=formula,
            description=description or "",
        )
    except (ValueError, TypeError) as exc:
        raise CalculationError(
            message="Failed to create CustomCalculationNode via factory",
            node_id=name,
            details={"error": str(exc)},
        ) from exc
