"""Utility helpers for fin_statement_model.

Currently exposes dictionary helpers such as `deep_merge`.
"""

from __future__ import annotations

# Public exports -----------------------------------------------------
from .dicts import deep_merge  # noqa: F401,E402  (re-export)

__all__: list[str] = [
    "deep_merge",
]
