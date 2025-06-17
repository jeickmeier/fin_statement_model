"""Node-level creation, update, replacement and value-setting operations."""

from __future__ import annotations

import logging
from typing import Any, cast

from fin_statement_model.core.errors import NodeError
from fin_statement_model.core.nodes import FinancialStatementItemNode, Node

logger = logging.getLogger(__name__)

__all__: list[str] = ["NodeOpsMixin"]


class NodeOpsMixin:
    """Operations that **mutate** the graph structure or stored values."""

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
            FinancialStatementItemNode,
            self._add_node_with_validation(  # type: ignore[attr-defined]
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
        node = self.manipulator.get_node(name)  # type: ignore[attr-defined]
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
        self.add_periods(list(values.keys()))  # type: ignore[attr-defined]
        logger.info(
            "Updated FinancialStatementItemNode '%s' with periods %s; replace_existing=%s",
            name,
            list(values.keys()),
            replace_existing,
        )
        return node

    def get_financial_statement_items(self) -> Any:
        from fin_statement_model.core.nodes import FinancialStatementItemNode as _FSIN

        return [node for node in self.nodes.values() if isinstance(node, _FSIN)]  # type: ignore[attr-defined]

    # -- Generic manipulator proxies -------------------------------------------
    def add_node(self, node: Node) -> Any:
        return self.manipulator.add_node(node)  # type: ignore[attr-defined]

    def remove_node(self, node_name: str) -> Any:
        return self.manipulator.remove_node(node_name)  # type: ignore[attr-defined]

    def replace_node(self, node_name: str, new_node: Node) -> Any:
        return self.manipulator.replace_node(node_name, new_node)  # type: ignore[attr-defined]

    def has_node(self, node_id: str) -> Any:
        return self.manipulator.has_node(node_id)  # type: ignore[attr-defined]

    def set_value(self, node_id: str, period: str, value: float) -> Any:
        return self.manipulator.set_value(node_id, period, value)  # type: ignore[attr-defined]
