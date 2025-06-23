r"""Graph merging logic and developer-friendly `__repr__`.

MergeReprMixin provides utilities for merging another graph's nodes and periods into the current graph,
and for generating a developer-friendly string representation of the graph's structure and contents.

Key responsibilities:
    - Merge nodes and periods from another graph, updating values as needed
    - Provide a detailed __repr__ for debugging and inspection

Examples:
    >>> from fin_statement_model.core.graph import Graph
    >>> g1 = Graph(periods=["2023"])
    >>> _ = g1.add_financial_statement_item("Revenue", {"2023": 100.0})
    >>> g2 = Graph(periods=["2024"])
    >>> _ = g2.add_financial_statement_item("Revenue", {"2024": 120.0})
    >>> g1.merge_from(g2)
    >>> repr(g1)
    '<Graph(...Periods: [\'2023\', \'2024\'])>'
"""

from __future__ import annotations

import contextlib
import logging

from fin_statement_model.core.errors import FinStatementModelError
from fin_statement_model.core.nodes import (
    FinancialStatementItemNode,
    is_calculation_node,
)

logger = logging.getLogger(__name__)

__all__: list[str] = ["MergeReprMixin"]


class MergeReprMixin:
    """Utility mix-in housing `merge_from` and an informative `__repr__`."""

    # ------------------------------------------------------------------
    # Graph merging ------------------------------------------------------
    # ------------------------------------------------------------------
    def merge_from(self, other_graph: MergeReprMixin) -> None:
        from fin_statement_model.core.graph.graph import (
            Graph,
        )  # local import to avoid cycles

        if not isinstance(other_graph, Graph):
            raise TypeError("Can only merge from another Graph instance.")

        logger.info("Starting merge from graph %r into %r", other_graph, self)

        new_periods = [p for p in other_graph.periods if p not in getattr(self, "periods", [])]
        if new_periods:
            self.add_periods(new_periods)  # type: ignore[attr-defined]
            logger.debug("Merged periods: %s", new_periods)

        nodes_added = 0
        nodes_updated = 0
        for node_name, other_node in other_graph.nodes.items():
            existing_node = self.get_node(node_name)  # type: ignore[attr-defined]
            if existing_node is not None:
                if (
                    hasattr(existing_node, "values")
                    and hasattr(other_node, "values")
                    and isinstance(existing_node.values, dict)
                    and isinstance(other_node.values, dict)
                ):
                    existing_node.values.update(other_node.values)
                    nodes_updated += 1
                    logger.debug("Merged values into existing node '%s'", node_name)
            else:
                try:
                    self.add_node(other_node)  # type: ignore[attr-defined]
                    nodes_added += 1
                except (ValueError, TypeError, FinStatementModelError):
                    logger.exception("Failed to add new node '%s' during merge", node_name)

        logger.info(
            "Merge complete. Nodes added: %s, Nodes updated (values merged): %s",
            nodes_added,
            nodes_updated,
        )

    # ------------------------------------------------------------------
    # Representation -----------------------------------------------------
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        num_nodes = len(self.nodes)  # type: ignore[attr-defined]
        _periods = getattr(self, "periods", [])
        periods_str = ", ".join(map(repr, _periods)) if _periods else "None"

        fs_item_count = 0
        calc_node_count = 0
        other_node_count = 0
        dependencies_count = 0

        for node in self.nodes.values():  # type: ignore[attr-defined]
            if isinstance(node, FinancialStatementItemNode):
                fs_item_count += 1
            elif is_calculation_node(node):
                calc_node_count += 1
                if hasattr(node, "get_dependencies"):
                    with contextlib.suppress(Exception):
                        dependencies_count += len(node.get_dependencies())
                elif hasattr(node, "inputs"):
                    try:
                        if isinstance(node.inputs, list):
                            dependencies_count += len([inp.name for inp in node.inputs if hasattr(inp, "name")])
                        elif isinstance(node.inputs, dict):
                            dependencies_count += len(node.inputs)
                    except (ValueError, AttributeError) as exc:
                        logger.debug(
                            'Failed counting dependencies for node "%s": %s',
                            getattr(node, "name", "?"),
                            exc,
                        )
            else:
                other_node_count += 1

        repr_parts = [
            f"Total Nodes: {num_nodes}",
            f"FS Items: {fs_item_count}",
            f"Calculations: {calc_node_count}",
        ]
        if other_node_count:
            repr_parts.append(f"Other: {other_node_count}")
        repr_parts.append(f"Dependencies: {dependencies_count}")
        repr_parts.append(f"Periods: [{periods_str}]")
        return f"<{type(self).__name__}({', '.join(repr_parts)})>"
