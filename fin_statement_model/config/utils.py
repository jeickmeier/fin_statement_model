"""Configuration utility helpers.

This module centralises helpers that are shared across the configuration
sub-package.  In particular it provides :func:`parse_env_var` which parses
an environment variable **key** (e.g. ``FSM_LOGGING__LEVEL``) into a list of
lower-case path segments understood by the configuration system.  The actual
value parsing logic lives in :pymeth:`fin_statement_model.config.helpers.parse_env_value`.
"""

from __future__ import annotations

from typing import List

# Re-export commonly used helpers from .helpers to avoid deep import chains
# Must be at module top for Ruff E402 compliance.
from fin_statement_model.config.helpers import (
    parse_env_value as parse_env_value,
)

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def parse_env_var(key: str, *, prefix: str = "FSM_") -> List[str]:
    """Parse an environment-variable *key* into config path segments.

    The Financial Statement Model library follows a *double underscore* naming
    convention for hierarchical configuration via environment variables.  A
    single underscore is allowed as a fallback separator for backward
    compatibility but ``__`` is preferred to avoid ambiguity with keys that
    legitimately contain underscores.

    Example mappings::

        FSM_LOGGING__LEVEL      -> ["logging", "level"]
        FSM_API__FMP_API_KEY    -> ["api", "fmp_api_key"]
        FSM_FOO_BAR            -> ["foo", "bar"]

    Args:
        key:  The raw environment variable key.
        prefix:  The expected *prefix* (default ``"FSM_"``).  If the key does
            not start with this prefix the original *key* is returned split
            into path segments (this allows parsing non-FSM env-vars if
            desired).

    Returns:
        A list of lower-case path segments representing the configuration
        hierarchy encoded in *key*.
    """

    # Remove prefix if present
    if key.startswith(prefix):
        key_body = key[len(prefix) :]
    else:
        key_body = key

    # Prefer double underscore as separator, fallback to single underscore
    if "__" in key_body:
        parts = key_body.split("__")
    else:
        parts = key_body.split("_")

    return [segment.lower() for segment in parts if segment]


__all__ = [
    "parse_env_var",
    "parse_env_value",
]
