"""ID resolution for statement items to graph nodes.

This module provides centralized logic for resolving statement item IDs to their
corresponding graph node IDs, handling the complexity of different item types
having different ID mapping rules.
"""

import logging
from typing import Optional

from fin_statement_model.core.graph import Graph
from fin_statement_model.statements.structure import (
    StatementStructure,
    LineItem,
)

logger = logging.getLogger(__name__)

__all__ = ["IDResolver"]


class IDResolver:
    """Centralizes ID resolution from statement items to graph nodes.

    This class handles the complexity of mapping statement item IDs to graph
    node IDs, accounting for the fact that:
    - LineItems have a separate node_id property that differs from their ID
    - Other items (CalculatedLineItem, SubtotalLineItem, MetricLineItem) use
      their ID directly as the node ID
    - Some nodes may exist directly in the graph without being statement items

    The resolver caches mappings for performance and provides both single and
    batch resolution methods.
    """

    def __init__(self, statement: StatementStructure):
        """Initialize the resolver with a statement structure.

        Args:
            statement: The statement structure containing items to resolve.
        """
        self.statement = statement
        self._item_to_node_cache: dict[str, str] = {}
        self._node_to_items_cache: dict[str, list[str]] = {}
        self._build_cache()

    def _build_cache(self) -> None:
        """Pre-build ID mappings for all items in the statement."""
        logger.debug(f"Building ID cache for statement '{self.statement.id}'")

        for item in self.statement.get_all_items():
            if isinstance(item, LineItem):
                # LineItems map their ID to their node_id property
                self._item_to_node_cache[item.id] = item.node_id
                self._node_to_items_cache.setdefault(item.node_id, []).append(item.id)
            else:
                # Other items use their ID directly as the node ID
                self._item_to_node_cache[item.id] = item.id
                self._node_to_items_cache.setdefault(item.id, []).append(item.id)

        logger.debug(
            f"ID cache built: {len(self._item_to_node_cache)} item->node mappings, "
            f"{len(self._node_to_items_cache)} unique nodes"
        )

    def resolve(self, item_id: str, graph: Optional[Graph] = None) -> Optional[str]:
        """Resolve a statement item ID to its graph node ID.

        Resolution process:
        1. Check the pre-built cache for the item ID
        2. If not found and a graph is provided, check if the ID exists
           directly as a node in the graph
        3. Return None if not found anywhere

        Args:
            item_id: The statement item ID to resolve.
            graph: Optional graph to check for direct node existence.

        Returns:
            The resolved graph node ID if found, None otherwise.
        """
        # Rebuild cache if it's empty (e.g., after invalidation)
        if not self._item_to_node_cache:
            self._build_cache()

        # Check cache first
        if item_id in self._item_to_node_cache:
            return self._item_to_node_cache[item_id]

        # Check if it exists directly in graph
        if graph and graph.has_node(item_id):
            # Cache this discovery for future lookups
            self._item_to_node_cache[item_id] = item_id
            self._node_to_items_cache.setdefault(item_id, []).append(item_id)
            return item_id

        return None

    def resolve_multiple(
        self, item_ids: list[str], graph: Optional[Graph] = None
    ) -> dict[str, Optional[str]]:
        """Resolve multiple item IDs at once.

        Args:
            item_ids: List of statement item IDs to resolve.
            graph: Optional graph to check for direct node existence.

        Returns:
            Dictionary mapping each item ID to its resolved node ID (or None).
        """
        return {item_id: self.resolve(item_id, graph) for item_id in item_ids}

    def get_items_for_node(self, node_id: str) -> list[str]:
        """Get all statement item IDs that map to a given node ID.

        This reverse lookup can be useful for debugging and understanding
        which statement items contribute to a particular graph node.

        Args:
            node_id: The graph node ID to look up.

        Returns:
            List of statement item IDs that map to this node (may be empty).
        """
        # Rebuild cache if it's empty
        if not self._node_to_items_cache:
            self._build_cache()
        return self._node_to_items_cache.get(node_id, [])

    def get_all_mappings(self) -> dict[str, str]:
        """Get all item ID to node ID mappings.

        Returns:
            Dictionary of all cached mappings.
        """
        # Rebuild cache if it's empty
        if not self._item_to_node_cache:
            self._build_cache()
        return self._item_to_node_cache.copy()

    def invalidate_cache(self) -> None:
        """Clear the cache, forcing a rebuild on next resolution.

        This should be called if the statement structure changes after
        the resolver was created.
        """
        self._item_to_node_cache.clear()
        self._node_to_items_cache.clear()
        logger.debug(f"ID cache invalidated for statement '{self.statement.id}'")

    def refresh_cache(self) -> None:
        """Rebuild the cache from the current statement structure."""
        self.invalidate_cache()
        self._build_cache()
