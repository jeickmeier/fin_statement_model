"""Analytics functions for summarizing and analyzing adjustments."""

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
    """Thin proxy delegating to :pyfunc:`filters.filter_adjustments`.

    Historically this helper ignored the *period* attribute on
    :class:`AdjustmentFilter` instances because analytics operates across all
    periods.  To preserve that behaviour we strip the *period* field before
    delegating.
    """

    from .filters import filter_adjustments  # local import to avoid cycles

    if isinstance(filter_input, AdjustmentFilter):
        filter_input = filter_input.model_copy(update={"period": None})

    return filter_adjustments(all_adjustments, filter_input)


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
        >>> manager = AdjustmentManager()
        >>> df = summary(manager)
        >>> df.index.names == ["period", "node_name"]
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
        >>> manager = AdjustmentManager()
        >>> adjustments = list_by_tag(manager, "NonRecurring")
        >>> all("NonRecurring" in tag for adj in adjustments for tag in adj.tags)
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
