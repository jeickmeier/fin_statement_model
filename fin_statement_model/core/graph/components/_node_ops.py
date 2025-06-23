"""Node-level creation, update, replacement and value-setting operations.

NodeOpsMixin provides all operations that mutate the graph structure or stored values at the node level.
This includes adding, updating, replacing, and removing nodes, as well as setting values for specific periods.

Key responsibilities:
    - Add new financial statement item nodes
    - Update values for existing nodes
    - Proxy generic manipulator operations (add, remove, replace, set value)
    - Retrieve all financial statement item nodes

Examples:
    >>> from fin_statement_model.core.graph import Graph
    >>> g = Graph(periods=["2023"])
    >>> _ = g.add_financial_statement_item("Revenue", {"2023": 100.0})
    >>> g.update_financial_statement_item("Revenue", {"2023": 120.0})
    FinancialStatementItemNode(name='Revenue', ...)
    >>> [n.name for n in g.get_financial_statement_items()]
    ['Revenue']
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

from fin_statement_model.core.errors import NodeError
from fin_statement_model.core.nodes import FinancialStatementItemNode, Node

logger = logging.getLogger(__name__)

__all__: list[str] = ["NodeOpsMixin"]


if TYPE_CHECKING:
    from fin_statement_model.core.nodes import Node  # pragma: no cover


class NodeOpsMixin:
    """Operations that **mutate** the graph structure or stored values."""

    # Attributes injected by "GraphBaseMixin" at runtime. They are declared here solely
    # for the benefit of static type checkers (mypy) and have **no** runtime effect.
    manipulator: Any  # provided by GraphBaseMixin
    _add_node_with_validation: Any  # provided by GraphBaseMixin
    add_periods: Any

    # -- Simple FS item helpers -------------------------------------------------
    def add_financial_statement_item(
        self,
        name: str,
        values: dict[str, float],
    ) -> FinancialStatementItemNode:
        from fin_statement_model.core.node_factory import NodeFactory

        if not isinstance(values, dict):
            raise TypeError("Values must be provided as a dict[str, float]")

        new_node = NodeFactory().create_financial_statement_item(
            name=name,
            values=values.copy(),
        )
        added_node = cast(
            "FinancialStatementItemNode",
            self._add_node_with_validation(
                new_node,
                check_cycles=False,
                validate_inputs=False,
            ),
        )
        logger.info(
            "Added FinancialStatementItemNode '%s' with periods %s",
            name,
            list(values.keys()),
        )
        return added_node

    def update_financial_statement_item(
        self,
        name: str,
        values: dict[str, float],
        *,
        replace_existing: bool = False,
    ) -> FinancialStatementItemNode:
        node = self.manipulator.get_node(name)
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
        self.add_periods(list(values.keys()))
        logger.info(
            "Updated FinancialStatementItemNode '%s' with periods %s; replace_existing=%s",
            name,
            list(values.keys()),
            replace_existing,
        )
        return node

    def get_financial_statement_items(self) -> Any:
        """Return all FinancialStatementItemNode instances in the graph."""
        return [
            node
            for node in self.nodes.values()  # type: ignore[attr-defined]
            if isinstance(node, FinancialStatementItemNode)
        ]

    # -- Generic manipulator proxies -------------------------------------------
    def add_node(self, node: Node) -> Any:
        return self.manipulator.add_node(node)

    def remove_node(self, node_name: str) -> Any:
        return self.manipulator.remove_node(node_name)

    def replace_node(self, node_name: str, new_node: Node) -> Any:
        return self.manipulator.replace_node(node_name, new_node)

    def has_node(self, node_id: str) -> Any:
        return self.manipulator.has_node(node_id)

    def set_value(self, node_id: str, period: str, value: float) -> Any:
        return self.manipulator.set_value(node_id, period, value)
