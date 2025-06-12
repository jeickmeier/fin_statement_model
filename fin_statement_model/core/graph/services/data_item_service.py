"""Data-item helper service for ``fin_statement_model.core.graph``.

This module extracts the logic previously embedded in ``Graph`` that is
responsible for managing *data nodes* (``FinancialStatementItemNode``).
It deliberately avoids importing ``Graph`` directly – all required
collaborators are injected via the constructor so the service remains
framework-agnostic and re-usable.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional, List, TYPE_CHECKING

from fin_statement_model.core.nodes import FinancialStatementItemNode, Node
from fin_statement_model.core.errors import NodeError

__all__: list[str] = ["DataItemService"]

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from fin_statement_model.core.node_factory import NodeFactory


class DataItemService:  # pylint: disable=too-few-public-methods
    """Encapsulate *financial-statement item* CRUD helpers.

    Args:
        node_factory: Factory used to create ``FinancialStatementItemNode``
            instances.
        add_node_with_validation: Callable delegating to the owning graph's
            node-registration helper (handles cycles / input validation).
        add_periods: Callable to register newly encountered periods on the graph.
        node_getter: Callable returning a node for a given name.
        node_names_provider: Callable to return a list of all node names.
    """

    def __init__(
        self,
        *,
        node_factory: "NodeFactory",
        add_node_with_validation: Callable[..., Node],
        add_periods: Callable[[List[str]], None],
        node_getter: Callable[[str], Optional[Node]],
        node_names_provider: Callable[[], List[str]],
    ) -> None:
        from fin_statement_model.core.node_factory import NodeFactory  # local import

        # Keep a weak type reference for mypy clarity
        if not isinstance(node_factory, NodeFactory):  # pragma: no cover – defensive
            raise TypeError("node_factory must be a NodeFactory instance")

        self._node_factory = node_factory
        self._add_node_with_validation = add_node_with_validation
        self._add_periods = add_periods
        self._get_node = node_getter
        self._node_names_provider = node_names_provider

    # ------------------------------------------------------------------
    # Public API – mirrors Graph façade exactly
    # ------------------------------------------------------------------
    def add_financial_statement_item(
        self, name: str, values: dict[str, float]
    ) -> FinancialStatementItemNode:
        """Create and register a new *data node* on the graph.

        This is largely a direct copy of the former ``Graph`` implementation
        but stripped of any direct attribute access.
        """
        # Validate inputs --------------------------------------------------
        if not isinstance(values, dict):  # pragma: no cover – defensive
            raise TypeError("Values must be provided as a dict[str, float]")

        # Use factory to instantiate node
        new_node = self._node_factory.create_financial_statement_item(
            name=name, values=values.copy()
        )

        # Delegate to owning graph for registration / cycle checks ---------
        added_node = self._add_node_with_validation(
            new_node,
            check_cycles=False,  # Data nodes have no inputs, cycles impossible
            validate_inputs=False,
        )

        # Update periods on graph -----------------------------------------
        self._add_periods(list(values.keys()))

        logger.info(
            "Added FinancialStatementItemNode '%s' with periods %s",
            name,
            list(values.keys()),
        )
        return added_node  # type: ignore[return-value]

    def update_financial_statement_item(
        self, name: str, values: dict[str, float], *, replace_existing: bool = False
    ) -> FinancialStatementItemNode:
        """Update an existing data node's values.

        Behaviour mirrors the old ``Graph`` method exactly.
        """
        node = self._get_node(name)
        if node is None:
            raise NodeError("Node not found", node_id=name)
        if not isinstance(node, FinancialStatementItemNode):
            raise TypeError(f"Node '{name}' is not a FinancialStatementItemNode")
        if not isinstance(values, dict):
            raise TypeError("Values must be provided as a dict[str, float]")

        if replace_existing:
            node.values = values.copy()
        else:
            node.values.update(values)

        # Register new periods, if any
        self._add_periods(list(values.keys()))

        logger.info(
            "Updated FinancialStatementItemNode '%s' with periods %s; replace_existing=%s",
            name,
            list(values.keys()),
            replace_existing,
        )
        return node

    def get_financial_statement_items(self) -> list[FinancialStatementItemNode]:
        """Return *all* data nodes currently registered on the graph."""
        from fin_statement_model.core.nodes import (
            FinancialStatementItemNode,
        )  # local import

        return [
            node
            for node in filter(None, map(self._get_node, self._all_node_names()))
            if isinstance(node, FinancialStatementItemNode)
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _all_node_names(self) -> list[str]:
        """Return list of all node names by probing the factory's nodes dict.

        The service itself doesn't know the owner graph's registry; we rely on
        the injected ``node_getter`` to deduce membership.
        """
        return list(self._node_names_provider())
