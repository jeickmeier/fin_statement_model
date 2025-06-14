"""Dictionary-related utility helpers.

Currently provides:
• ``deep_merge`` – recursively merge two mappings where *update* overrides *base*.

The helper is intentionally conservative: it only recurses when *both* values are
``Mapping`` instances. In all other cases, the value from *update* replaces the
value from *base*.

The implementation is copied from the previous ``ConfigManager._deep_merge`` to
provide a single authoritative version.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Dict, cast

__all__: list[str] = ["deep_merge"]


def deep_merge(
    base: Mapping[str, Any],
    update: Mapping[str, Any],
    *,
    copy: bool = True,
) -> Dict[str, Any]:
    """Recursively merge two mappings.

    Args:
        base: The original mapping whose values have lower precedence.
        update: The mapping whose keys/values override those in *base*.
        copy: If *True* (default) return a new *dict*; if *False*, merge into
            *base* **in-place** and return the same object. When *False* and
            *base* is not a ``dict`` instance, a *TypeError* is raised.

    Returns:
        A merged *dict* containing keys from both *base* and *update* with
        precedence rules applied.
    """
    # Ensure we are working with a mutable dict instance if copying is disabled
    if copy:
        result: Dict[str, Any] = dict(base)  # shallow copy of base
    else:
        if not isinstance(base, dict):
            raise TypeError("In-place deep_merge requires 'base' to be a dict")
        result = cast(Dict[str, Any], base)

    for key, value in update.items():
        if (
            key in result
            and isinstance(result[key], Mapping)
            and isinstance(value, Mapping)
        ):
            # Recurse only when both are mapping types.
            result[key] = deep_merge(
                cast(Mapping[str, Any], result[key]), value, copy=copy
            )
        else:
            # Value from *update* wins.
            result[key] = value

    return result
