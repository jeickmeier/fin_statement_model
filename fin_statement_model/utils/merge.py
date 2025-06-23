"""Utility functions for merging nested Python dictionaries.

This module provides :func:`deep_merge` which recursively merges two nested
mapping objects.  It is intended to be the single, canonical implementation of
*deep merge* behaviour across the *fin_statement_model* code-base to avoid the
proliferation of ad-hoc variants that may diverge over time.

The implementation is based on the original logic in
``fin_statement_model.config.manager.ConfigManager._deep_merge`` (commit
9c83d5d) and has been extracted so that all packages can depend on the same
semantics.

Key characteristics
-------------------
1.  The merge is **non-destructive** - the *base* mapping is **copied** before
    updates are applied.  Neither *base* nor *update* is modified in-place.
2.  Values from *update* take precedence over those in *base*.
3.  If the value under a given key is a mapping in **both** *base* and
    *update*, the function recurses so that nested dictionaries are merged
    deeply.
4.  If the value under a given key is a **list** in both inputs, the lists are
    concatenated **preserving the original order** and **deduplicating** items
    that already exist in *base*.
5.  In all other cases the value from *update* replaces the one in *base*.

This behaviour covers the most common requirements we have encountered so far
(e.g. merging configuration trees, adjustment definitions, etc.).  For more
advanced policies consider pulling-in a dedicated library such as
`deepmerge <https://pypi.org/project/deepmerge/>`_.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

__all__ = ["deep_merge"]


def deep_merge(base: Mapping[str, Any], update: Mapping[str, Any]) -> dict[str, Any]:
    """Recursively merge two dictionaries.

    The *update* mapping wins over *base* for scalar values.  Nested mappings
    are merged recursively, and list values are concatenated while ensuring
    that duplicates from *update* are **not** re-added.

    Args:
        base: The *base* mapping.
        update: The mapping providing override values.

    Returns:
        A **new** dictionary containing the merged result.
    """
    # Make a shallow copy so we never mutate the caller's object.
    result: dict[str, Any] = dict(base)

    for key, value in update.items():
        # Case 1 - both values are dict-like → recurse
        if key in result and isinstance(result[key], Mapping) and isinstance(value, Mapping):
            result[key] = deep_merge(result[key], value)

        # Case 2 - both values are lists → append unique items preserving order
        elif key in result and isinstance(result[key], list) and isinstance(value, list):
            existing_list: list[Any] = result[key]
            combined = existing_list + [item for item in value if item not in existing_list]
            result[key] = combined

        # Fallback - scalar or mismatching types → overwrite
        # We copy *value* if it is a mutable mapping or list to guard against
        # accidental shared-state when the caller later mutates it in-place.
        elif isinstance(value, Mapping | list):
            result[key] = value.copy() if hasattr(value, "copy") else list(value)
        else:
            result[key] = value

    return result
