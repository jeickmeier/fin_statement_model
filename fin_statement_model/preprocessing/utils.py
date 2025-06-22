"""Utility helpers for the *preprocessing* layer.

This module currently hosts :func:`ensure_dataframe` which provides a
high-performance, opinionated helper for coercing input objects to
``pandas.DataFrame`` instances while preserving the original type
information (Series vs. DataFrame).

The function is deliberately kept *very* lightweight because it sits on the
hot-path for many transformer implementations.  In particular it contains a
fast-path that simply returns the original object **unmodified** when it is
already a ``pandas.DataFrame`` – avoiding an unnecessary and potentially
expensive copy.
"""

# PEP 563/PEP 649: Keep future imports directly below the module docstring.
from __future__ import annotations

from typing import Tuple, Union

import pandas as pd

__all__: list[str] = [
    "ensure_dataframe",
]


def ensure_dataframe(data: Union[pd.DataFrame, pd.Series]) -> Tuple[pd.DataFrame, bool]:
    """Return ``(df, was_series)`` ensuring *data* is a DataFrame.

    Args:
        data: The input object which must be either a ``pandas.DataFrame`` or
            ``pandas.Series`` instance.

    Returns:
        Tuple[DataFrame, bool]:
            1. A ``pandas.DataFrame`` representation of *data*.
            2. ``True`` if the original *data* was a ``pandas.Series``; ``False``
               if it was already a ``DataFrame``.

    Raises:
        TypeError: If *data* is neither a ``DataFrame`` nor a ``Series``.
    """

    # Fast-path: already a DataFrame – *do not* create a copy
    if isinstance(data, pd.DataFrame):
        return data, False

    # Series → single-column DataFrame conversion
    if isinstance(data, pd.Series):
        return data.to_frame(), True

    raise TypeError("data must be a pandas DataFrame or Series")
