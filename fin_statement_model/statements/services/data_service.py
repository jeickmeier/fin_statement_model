"""Data service for financial statements.

Encapsulates building of the data dictionary from the graph and statement structure.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fin_statement_model.statements.structure import StatementStructure, LineItem
from fin_statement_model.core.graph.graph import Graph
from fin_statement_model.statements.errors import StatementError

logger = logging.getLogger(__name__)

__all__ = ["DataService"]

if TYPE_CHECKING:
    from fin_statement_model.statements.manager import StatementManager


class DataService:
    """Service to build data dictionaries for statements."""

    def __init__(self, manager: StatementManager) -> None:
        """Initialize the DataService.

        Args:
            manager: The StatementManager instance providing graph and statements.
        """
        self.manager = manager
        self.graph: Graph = manager.graph
        self.statements: dict[str, StatementStructure] = manager.statements

    def build_data_dictionary(self, statement_id: str) -> dict[str, dict[str, float]]:
        """Build a data dictionary for a statement from the graph.

        Args:
            statement_id: The ID of the statement to build data for.

        Returns:
            Dictionary mapping node IDs to their period-value maps.

        Raises:
            StatementError: If the statement ID is not registered.
        """
        statement = self.statements.get(statement_id)
        if statement is None:
            raise StatementError(message="Statement not found", statement_id=statement_id)

        data: dict[str, dict[str, float]] = {}

        # Get all items that need data
        all_items = statement.get_all_items()

        # Build data dictionary
        for item in all_items:
            # Only line items
            if isinstance(item, LineItem):
                node_id = item.node_id
                node = self.graph.get_node(node_id)
                if node is None:
                    continue
                values = {}
                for period in self.graph.periods:
                    try:
                        value = self.graph.calculate(node_id, period)
                        values[period] = value
                    except Exception as e:
                        logger.warning(
                            f"Could not calculate value for node '{node_id}' in period '{period}'. Skipping. Error: {e}"
                        )
                        continue
                if values:
                    data[node_id] = values
        return data
