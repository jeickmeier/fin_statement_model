"""StatementMerger: encapsulates merge logic for two FinancialStatementGraphs."""

import logging
from typing import Any

logger = logging.getLogger(__name__)

class StatementMerger:
    """Merge-related helpers for a FinancialStatementGraph."""

    def __init__(self, fsg: Any) -> None:
        """Store reference to the host graph."""
        self.fsg = fsg

    def merge_from(self, other_graph: Any) -> None:
        """Merge another FinancialStatementGraph into this one."""
        # 1. Update periods
        for period in other_graph.periods:
            if period not in self.fsg.periods:
                self.fsg.periods.append(period)
        self.fsg.periods.sort()

        # 2. Merge nodes
        for node_name, node in other_graph.nodes.items():
            existing = self.fsg.get_node(node_name)
            if existing is not None:
                # Update existing node's values
                if hasattr(node, "values"):
                    for p, v in node.values.items():
                        existing.values[p] = v  # type: ignore
                self.fsg.manipulator.add_node(existing)
            else:
                # Add entirely new node
                self.fsg.manipulator.add_node(node)
