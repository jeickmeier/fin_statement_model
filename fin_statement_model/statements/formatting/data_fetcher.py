"""Data fetching functionality for financial statements.

This module provides the DataFetcher class that handles retrieving data from
the graph for statement formatting. It encapsulates the logic for resolving
item IDs to node IDs and fetching values with proper error handling.
"""

import logging
from dataclasses import dataclass
from typing import Optional, cast

import numpy as np
import pandas as pd

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.errors import NodeError, CalculationError
from fin_statement_model.core.adjustments.models import AdjustmentFilterInput
from fin_statement_model.statements.structure import (
    StatementStructure,
    Section,
    StatementItem,
)
from fin_statement_model.statements.population.id_resolver import IDResolver
from fin_statement_model.core.nodes import standard_node_registry
from fin_statement_model.statements.utilities.result_types import (
    Result,
    Success,
    Failure,
    ErrorDetail,
    ErrorSeverity,
    ErrorCollector,
)

logger = logging.getLogger(__name__)

__all__ = ["DataFetcher", "FetchResult", "NodeData"]


@dataclass
class NodeData:
    """Data for a single node across all periods.

    Attributes:
        node_id: The graph node ID
        values: Dict mapping period to value
        is_adjusted: Dict mapping period to bool indicating if adjusted
        errors: Any errors encountered during fetching
    """

    node_id: str
    values: dict[str, float]
    is_adjusted: dict[str, bool]
    errors: list[ErrorDetail]

    @property
    def has_data(self) -> bool:
        """Check if any non-NaN values exist."""
        return any(pd.notna(v) for v in self.values.values())


@dataclass
class FetchResult:
    """Result of fetching data for a statement.

    Attributes:
        data: Dict mapping node_id to period values
        errors: ErrorCollector with any errors/warnings
        node_count: Number of nodes successfully fetched
        missing_nodes: List of node IDs that couldn't be found
    """

    data: dict[str, dict[str, float]]
    errors: ErrorCollector
    node_count: int
    missing_nodes: list[str]

    def to_result(self) -> Result[dict[str, dict[str, float]]]:
        """Convert to Result type."""
        if self.errors.has_errors():
            return Failure(errors=self.errors.get_errors())
        return Success(value=self.data)


class DataFetcher:
    """Fetches data from graph for statement formatting.

    This class encapsulates the logic for:
    - Resolving statement item IDs to graph node IDs
    - Fetching values from the graph with error handling
    - Applying adjustment filters if specified
    - Collecting errors and warnings during the process
    """

    def __init__(self, statement: StatementStructure, graph: Graph):
        """Initialize the data fetcher.

        Args:
            statement: The statement structure to fetch data for
            graph: The graph containing the data
        """
        self.statement = statement
        self.graph = graph
        self.id_resolver = IDResolver(statement, standard_node_registry)

    def _resolve_adjustment_filter(
        self,
        item: StatementItem,
        global_filter: Optional[AdjustmentFilterInput] = None,
    ) -> Optional[AdjustmentFilterInput]:
        """Resolve which adjustment filter to use for an item.

        Precedence order:
        1. Global filter passed to fetch method (highest priority)
        2. Item's default adjustment filter
        3. Parent section's default adjustment filter
        4. None (no filter)

        Args:
            item: The statement item to get the filter for.
            global_filter: Optional global filter that overrides everything.

        Returns:
            The resolved adjustment filter to use, or None.
        """
        # Global filter has highest priority
        if global_filter is not None:
            return global_filter

        # Check item's own default filter
        if (
            hasattr(item, "default_adjustment_filter")
            and item.default_adjustment_filter is not None
        ):
            return cast(AdjustmentFilterInput, item.default_adjustment_filter)

        # Check parent section's default filter
        # We need to find which section contains this item
        parent_section = self._find_parent_section(item)
        if (
            parent_section
            and hasattr(parent_section, "default_adjustment_filter")
            and parent_section.default_adjustment_filter is not None
        ):
            return cast(AdjustmentFilterInput, parent_section.default_adjustment_filter)

        # No filter
        return None

    def _find_parent_section(self, target_item: StatementItem) -> Optional[Section]:
        """Find the parent section that contains the given item.

        Args:
            target_item: The item to find the parent section for.

        Returns:
            The parent Section object, or None if not found.
        """

        def search_in_section(section: Section) -> Optional[Section]:
            # Check direct items
            for item in section.items:
                if item is target_item or (
                    hasattr(item, "id")
                    and hasattr(target_item, "id")
                    and item.id == target_item.id
                ):
                    return section
                # Check nested sections
                if isinstance(item, Section):
                    result = search_in_section(item)
                    if result:
                        return result

            # Check subtotal
            if hasattr(section, "subtotal") and section.subtotal is target_item:
                return section

            return None

        # Search through all top-level sections
        for section in self.statement.sections:
            result = search_in_section(section)
            if result:
                return result

        return None

    def fetch_all_data(
        self,
        adjustment_filter: Optional[AdjustmentFilterInput] = None,
        include_missing: bool = False,
    ) -> FetchResult:
        """Fetch data for all items in the statement.

        Args:
            adjustment_filter: Optional global filter for adjustments (overrides item defaults)
            include_missing: If True, include nodes that don't exist in graph
                           with NaN values

        Returns:
            FetchResult containing the fetched data and any errors
        """
        error_collector = ErrorCollector()
        data: dict[str, dict[str, float]] = {}
        missing_nodes: list[str] = []

        # Check if graph has periods
        periods = self.graph.periods
        if not periods:
            error_collector.add_error(
                code="no_periods",
                message=f"Graph has no periods defined for statement '{self.statement.id}'",
                source=self.statement.id,
            )
            return FetchResult(
                data={}, errors=error_collector, node_count=0, missing_nodes=[]
            )

        logger.debug(
            f"Fetching data for statement '{self.statement.id}' across {len(periods)} periods"
        )

        # Get all items and resolve their node IDs
        all_items = self.statement.get_all_items()
        processed_node_ids = set()

        for item in all_items:
            # Resolve item ID to node ID
            node_id = self.id_resolver.resolve(item.id, self.graph)

            if not node_id:
                error_collector.add_warning(
                    code="unresolvable_item",
                    message=f"Cannot resolve item '{item.id}' to a node ID",
                    source=item.id,
                    context="IDResolver.resolve",
                )
                continue

            if node_id in processed_node_ids:
                continue  # Skip already processed nodes

            processed_node_ids.add(node_id)

            # Resolve adjustment filter for this specific item
            item_filter = self._resolve_adjustment_filter(item, adjustment_filter)

            # Fetch data for this node
            node_result = self._fetch_node_data(
                node_id, periods, item_filter, item_id=item.id
            )

            if node_result.is_success():
                node_data = cast(NodeData, node_result.get_value())
                if node_data.has_data or include_missing:
                    data[node_id] = node_data.values

                # Add any warnings from node fetching
                for error in node_data.errors:
                    if error.severity == ErrorSeverity.WARNING:
                        error_collector.add_warning(
                            error.code,
                            error.message,
                            error.context,
                            error.source or item.id,
                        )
            else:
                # Node doesn't exist in graph
                missing_nodes.append(node_id)
                if include_missing:
                    # Fill with NaN values
                    data[node_id] = {period: np.nan for period in periods}

                error_collector.add_from_result(node_result, source=item.id)

        logger.info(
            f"Fetched data for {len(data)} nodes from statement '{self.statement.id}'. "
            f"Missing: {len(missing_nodes)}, Warnings: {len(error_collector.get_warnings())}"
        )

        return FetchResult(
            data=data,
            errors=error_collector,
            node_count=len(data),
            missing_nodes=missing_nodes,
        )

    def _fetch_node_data(
        self,
        node_id: str,
        periods: list[str],
        adjustment_filter: Optional[AdjustmentFilterInput],
        item_id: Optional[str] = None,
    ) -> Result[NodeData]:
        """Fetch data for a single node across all periods.

        Args:
            node_id: The graph node ID to fetch
            periods: List of periods to fetch
            adjustment_filter: Optional adjustment filter
            item_id: Optional statement item ID for error context

        Returns:
            Result containing NodeData or error details
        """
        # Check if node exists
        if not self.graph.has_node(node_id):
            return Failure(
                [
                    ErrorDetail(
                        code="node_not_found",
                        message=f"Node '{node_id}' not found in graph",
                        source=item_id or node_id,
                        severity=ErrorSeverity.WARNING,
                    )
                ]
            )

        values = {}
        is_adjusted = {}
        errors = []

        for period in periods:
            try:
                # Fetch value with optional adjustments
                raw_value = cast(
                    float,
                    self.graph.get_adjusted_value(
                        node_id,
                        period,
                        filter_input=adjustment_filter,
                        return_flag=False,  # Only need the value
                    ),
                )
                # Ensure value is float or NaN
                values[period] = float(raw_value) if pd.notna(raw_value) else np.nan
                is_adjusted[period] = bool(raw_value)

            except (NodeError, CalculationError) as e:
                # Expected errors - log as warning
                logger.warning(
                    f"Error calculating node '{node_id}' for period '{period}': {e}"
                )
                values[period] = np.nan
                is_adjusted[period] = False
                errors.append(
                    ErrorDetail(
                        code="calculation_error",
                        message=f"Failed to calculate value: {e}",
                        context=f"period={period}",
                        severity=ErrorSeverity.WARNING,
                        source=item_id or node_id,
                    )
                )

            except TypeError as e:
                # Filter/adjustment errors
                logger.warning(
                    f"Type error for node '{node_id}', period '{period}': {e}"
                )
                values[period] = np.nan
                is_adjusted[period] = False
                errors.append(
                    ErrorDetail(
                        code="filter_error",
                        message=f"Invalid adjustment filter: {e}",
                        context=f"period={period}",
                        severity=ErrorSeverity.WARNING,
                        source=item_id or node_id,
                    )
                )

            except Exception as e:
                # Unexpected errors - log as error
                logger.error(
                    f"Unexpected error for node '{node_id}', period '{period}': {e}",
                    exc_info=True,
                )
                values[period] = np.nan
                is_adjusted[period] = False
                errors.append(
                    ErrorDetail(
                        code="unexpected_error",
                        message=f"Unexpected error: {e}",
                        context=f"period={period}, error_type={type(e).__name__}",
                        severity=ErrorSeverity.ERROR,
                        source=item_id or node_id,
                    )
                )

        return Success(
            NodeData(
                node_id=node_id, values=values, is_adjusted=is_adjusted, errors=errors
            )
        )

    def check_adjustments(
        self,
        node_ids: list[str],
        periods: list[str],
        adjustment_filter: Optional[AdjustmentFilterInput] = None,
    ) -> dict[str, dict[str, bool]]:
        """Check which node/period combinations have adjustments.

        Args:
            node_ids: List of node IDs to check
            periods: List of periods to check
            adjustment_filter: Filter to check adjustments against

        Returns:
            Dict mapping node_id -> period -> was_adjusted boolean
        """
        results = {}

        for node_id in node_ids:
            if not self.graph.has_node(node_id):
                results[node_id] = {period: False for period in periods}
                continue

            period_results = {}
            for period in periods:
                try:
                    was_adjusted = self.graph.was_adjusted(
                        node_id, period, adjustment_filter
                    )
                    period_results[period] = bool(was_adjusted)
                except Exception as e:
                    logger.warning(
                        f"Error checking adjustments for {node_id}/{period}: {e}"
                    )
                    period_results[period] = False

            results[node_id] = period_results

        return results
