"""Analytics functions for summarizing and analyzing adjustments.

This module provides utilities for generating summaries and filtered lists of adjustments
from an AdjustmentManager. It is useful for reporting, diagnostics, and exploratory analysis
of adjustment data in financial models.

Examples:
    >>> from fin_statement_model.core.adjustments.manager import AdjustmentManager
    >>> from fin_statement_model.core.adjustments.analytics import summary, list_by_tag
    >>> mgr = AdjustmentManager()
    >>> # ... add adjustments to mgr ...
    >>> df = summary(mgr)
    >>> print(df.head())
    >>> adj_list = list_by_tag(mgr, "Scenario/Upside")
    >>> print(len(adj_list))
"""

import logging
from typing import Optional, Union
from collections.abc import Callable

import pandas as pd

from fin_statement_model.core.adjustments.manager import AdjustmentManager
from fin_statement_model.core.adjustments.models import (
    Adjustment,
    AdjustmentFilter,
    AdjustmentTag,
)
from fin_statement_model.core.adjustments.helpers import tag_matches

logger = logging.getLogger(__name__)


def _filter_adjustments_static(
    all_adjustments: list[Adjustment],
    filter_input: Optional[
        Union[AdjustmentFilter, set[AdjustmentTag], Callable[[Adjustment], bool]]
    ],
) -> list[Adjustment]:
    """Filter adjustments based on static (non-period) criteria.

    Args:
        all_adjustments: List of all adjustments to filter.
        filter_input: Filter criteria (AdjustmentFilter, set of tags, callable, or None).

    Returns:
        Filtered list of adjustments matching the filter criteria.

    Examples:
        >>> from fin_statement_model.core.adjustments.models import Adjustment, AdjustmentType
        >>> adj = Adjustment(node_name='A', period='2023', value=1.0, reason='r')
        >>> _filter_adjustments_static([adj], None)
        [adj]
    """
    if filter_input is None:
        # No filter means include all adjustments
        logger.debug("No filter applied.")
        return all_adjustments

    elif isinstance(filter_input, AdjustmentFilter):
        # Apply filter, ignoring its period attribute
        temp_filter = filter_input.model_copy(update={"period": None})
        filtered = [adj for adj in all_adjustments if temp_filter.matches(adj)]
        logger.debug(
            f"Applied AdjustmentFilter (ignoring period). Filter: {temp_filter}"
        )
        return filtered

    elif isinstance(filter_input, set):
        # Shorthand for include_tags
        filtered = [
            adj for adj in all_adjustments if tag_matches(adj.tags, filter_input)
        ]
        logger.debug(f"Applied tag filter. Tags: {filter_input}")
        return filtered

    elif callable(filter_input):
        filtered = [adj for adj in all_adjustments if filter_input(adj)]
        logger.debug("Applied callable filter.")
        return filtered

    else:
        # Should not happen due to type hint, but defensive
        logger.warning(
            f"Invalid filter_input type: {type(filter_input)}. No filtering applied."
        )
        return all_adjustments


def summary(
    manager: AdjustmentManager,
    filter_input: Optional[
        Union[AdjustmentFilter, set[AdjustmentTag], Callable[[Adjustment], bool]]
    ] = None,
    group_by: list[str] = ["period", "node_name"],
) -> pd.DataFrame:
    """Generate a summary DataFrame of adjustments, optionally filtered and grouped.

    Calculates count, sum of values, and mean of absolute values for adjustments.

    Args:
        manager: The AdjustmentManager instance containing the adjustments.
        filter_input: Optional filter criteria (AdjustmentFilter, set of tags, callable, or None)
            to apply before summarizing.
        group_by: List of Adjustment attributes to group the summary by.
            Defaults to ["period", "node_name"]. Valid fields include
            'period', 'node_name', 'scenario', 'type', 'user'.

    Returns:
        A pandas DataFrame with the summary statistics (count, sum, mean_abs_value)
        indexed by the specified group_by columns.

    Examples:
        >>> from fin_statement_model.core.adjustments.manager import AdjustmentManager
        >>> from fin_statement_model.core.adjustments.models import Adjustment
        >>> mgr = AdjustmentManager()
        >>> adj = Adjustment(node_name='A', period='2023', value=2.0, reason='r')
        >>> mgr.add_adjustment(adj)
        >>> df = summary(mgr)
        >>> df.loc[('2023', 'A'), 'sum_value'] == 2.0
        True
    """
    logger.debug(f"Generating adjustment summary, grouping by: {group_by}")

    # Get all adjustments first
    # TODO: Optimization - If filtering is very restrictive, could filter first.
    # However, filtering requires period context which isn't directly available here.
    # Get all adjustments and filter based on the filter_input's static properties.
    # The period-based filtering (effective window) cannot be applied generically here.
    all_adjustments = manager.get_all_adjustments()

    # Apply filtering using the helper function
    filtered_adjustments = _filter_adjustments_static(all_adjustments, filter_input)

    if not filtered_adjustments:
        logger.info("No adjustments found matching the filter criteria for summary.")
        # Return empty DataFrame with expected columns
        cols = [*group_by, "count", "sum_value", "mean_abs_value"]
        return pd.DataFrame(columns=cols).set_index(group_by)

    # Convert to DataFrame for easier aggregation
    adj_data = [
        adj.model_dump(
            include=set([*group_by, "value"])
        )  # Include value for aggregation
        for adj in filtered_adjustments
    ]
    df = pd.DataFrame(adj_data)

    # Ensure correct types for grouping columns if needed (e.g., type as string)
    if "type" in group_by:
        df["type"] = df["type"].astype(str)

    # Add absolute value for mean calculation
    df["abs_value"] = df["value"].abs()

    # Perform aggregation
    summary_df = df.groupby(group_by).agg(
        count=("value", "size"),
        sum_value=("value", "sum"),
        mean_abs_value=("abs_value", "mean"),
    )

    logger.info(f"Generated adjustment summary with {len(summary_df)} groups.")
    return summary_df


def list_by_tag(
    manager: AdjustmentManager,
    tag_prefix: str,
    filter_input: Optional[
        Union[AdjustmentFilter, set[AdjustmentTag], Callable[[Adjustment], bool]]
    ] = None,
) -> list[Adjustment]:
    """List all adjustments matching a tag prefix, optionally applying further filters.

    Args:
        manager: The AdjustmentManager instance containing the adjustments.
        tag_prefix: The tag prefix string to match (e.g., "NonRecurring").
        filter_input: Optional additional filter criteria (AdjustmentFilter, set of tags,
            callable, or None).

    Returns:
        A list of Adjustment objects that have at least one tag starting with
        the tag_prefix and also match the optional filter_input.

    Examples:
        >>> from fin_statement_model.core.adjustments.manager import AdjustmentManager
        >>> from fin_statement_model.core.adjustments.models import Adjustment
        >>> mgr = AdjustmentManager()
        >>> adj = Adjustment(node_name='A', period='2023', value=1.0, reason='r', tags={'X'})
        >>> mgr.add_adjustment(adj)
        >>> result = list_by_tag(mgr, 'X')
        >>> result[0].node_name == 'A'
        True
    """
    logger.debug(f"Listing adjustments by tag prefix: '{tag_prefix}'")

    # Get all adjustments and apply filters using the helper function
    all_adjustments = manager.get_all_adjustments()
    filtered_adjustments = _filter_adjustments_static(all_adjustments, filter_input)

    # Apply the primary tag prefix filter
    prefix_set = {tag_prefix}
    final_list = [
        adj for adj in filtered_adjustments if tag_matches(adj.tags, prefix_set)
    ]

    logger.info(
        f"Found {len(final_list)} adjustments matching prefix '{tag_prefix}' and other filters."
    )
    # Sort by priority/timestamp for consistent output
    return sorted(final_list, key=lambda x: (x.priority, x.timestamp))
