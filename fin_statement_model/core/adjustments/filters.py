"""Common filtering utilities for Adjustment objects.

This module centralises the logic for filtering adjustment collections so that
it can be reused across the core adjustment manager and analytics helpers.
"""

from __future__ import annotations

import inspect
import logging
from typing import Callable

from .helpers import tag_matches
from .models import (
    Adjustment,
    AdjustmentFilter,
    AdjustmentFilterInput,
)

logger = logging.getLogger(__name__)


def _callable_param_count(fn: Callable[..., bool]) -> int:
    """Return the number of positional parameters a callable expects.

    For built-ins and callables without a retrievable signature the function
    falls back to *1* as a safe default.
    """

    try:
        return len(inspect.signature(fn).parameters)
    except (TypeError, ValueError):  # pragma: no cover – defensive
        return 1


def filter_adjustments(
    adjs: list[Adjustment],
    spec: AdjustmentFilterInput = None,
) -> list[Adjustment]:
    """Filter a sequence of adjustments according to *spec*.

    The helper supports the same flexible *spec* type accepted throughout the
    adjustments package:

    * ``None`` – return *adjs* unchanged.
    * :class:`~fin_statement_model.core.adjustments.models.AdjustmentFilter` –
      use its :py:meth:`matches` method.
    * ``set[str]`` – shorthand for filtering by *include_tags* prefixes.
    * ``Callable`` – arbitrary predicate receiving the :class:`Adjustment` as
      its first positional argument.  Additional positional parameters are
      ignored by this helper – callers that need to supply contextual
      arguments (e.g. *period*) should wrap the predicate in a *lambda*.

    The original ordering of *adjs* is preserved.

    Args:
        adjs: The adjustments to filter.
        spec: Filtering specification or *None*.

    Returns:
        A list containing only those adjustments that match *spec*.
    """
    # Early-out when no filter has been supplied.
    if spec is None:
        logger.debug(
            "filter_adjustments: no spec → returning original list (%d items)",
            len(adjs),
        )
        return adjs

    # ------------------------------------------------------------------
    # AdjustmentFilter – leverage its built-in *matches* method
    # ------------------------------------------------------------------
    if isinstance(spec, AdjustmentFilter):
        filtered = [adj for adj in adjs if spec.matches(adj)]
        logger.debug(
            "filter_adjustments: AdjustmentFilter retained %d/%d items",
            len(filtered),
            len(adjs),
        )
        return filtered

    # ------------------------------------------------------------------
    # Tag set shorthand – treat *spec* as *include_tags* prefixes
    # ------------------------------------------------------------------
    if isinstance(spec, set):
        filtered = [adj for adj in adjs if tag_matches(adj.tags, spec)]
        logger.debug(
            "filter_adjustments: tag set filtered to %d/%d items (tags=%s)",
            len(filtered),
            len(adjs),
            spec,
        )
        return filtered

    # ------------------------------------------------------------------
    # Callable predicate – allow arbitrary user logic
    # ------------------------------------------------------------------
    if callable(spec):
        param_count = _callable_param_count(spec)
        if param_count == 1:
            filtered = [adj for adj in adjs if spec(adj)]
        else:
            # We have no contextual parameters – call with the first one only.
            filtered = [adj for adj in adjs if spec(adj)]
        logger.debug(
            "filter_adjustments: callable predicate retained %d/%d items",
            len(filtered),
            len(adjs),
        )
        return filtered

    # ------------------------------------------------------------------
    # Fallback – spec type not recognised, return list unchanged with warning
    # ------------------------------------------------------------------
    logger.warning(
        "filter_adjustments: unsupported spec type %s – returning unfiltered list",
        type(spec),
    )
    return adjs
