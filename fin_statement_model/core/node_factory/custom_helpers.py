"""Custom helper utilities for the modular NodeFactory.

This module provides helpers for wrapping Python callables as custom calculation nodes.

Example:
    >>> from fin_statement_model.core.node_factory.custom_helpers import _create_custom_node_from_callable
    >>> def my_formula(a, b):
    ...     return a + b
    >>> # Assume n1, n2 are Node instances
    >>> node = _create_custom_node_from_callable(name="CustomSum", inputs=[n1, n2], formula=my_formula)
    >>> node.name
    'CustomSum'
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fin_statement_model.core.errors import CalculationError
from fin_statement_model.core.nodes.base import Node
from fin_statement_model.core.nodes.calculation_nodes import CustomCalculationNode

if TYPE_CHECKING:
    from collections.abc import Callable

__all__: list[str] = ["_create_custom_node_from_callable"]


def _create_custom_node_from_callable(
    *,
    name: str,
    inputs: list[Node],
    formula: Callable[..., float],
    description: str | None = None,
) -> CustomCalculationNode:
    """Wrap a formula callable in a CustomCalculationNode.

    Args:
        name: Name of the custom calculation node.
        inputs: List of input Node instances.
        formula: Callable that implements the calculation logic.
        description: Optional description for the node.

    Returns:
        CustomCalculationNode: The resulting node wrapping the formula.

    Raises:
        TypeError: If formula is not callable or inputs are not Node instances.
        CalculationError: If node creation fails.

    Example:
        >>> from fin_statement_model.core.node_factory.custom_helpers import _create_custom_node_from_callable
        >>> def my_formula(a, b):
        ...     return a + b
        >>> # Assume n1, n2 are Node instances
        >>> node = _create_custom_node_from_callable(name="CustomSum", inputs=[n1, n2], formula=my_formula)
        >>> node.name
        'CustomSum'
    """
    # Basic validation ----------------------------------------------------
    if not callable(formula):
        raise TypeError("formula must be a callable object returning float")

    for n in inputs:
        if not isinstance(n, Node):
            raise TypeError(f"All items in 'inputs' must be Node instances; got {type(n)!r}")

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
