"""Core type aliases shared across the IO package.

This module serves as the single source of truth for type aliases used
throughout the `fin_statement_model.io` subpackage. Centralizing these
definitions avoids circular dependencies and duplication.
"""

from __future__ import annotations

from typing import Optional, Union

# MappingConfig defines the structure for name-mapping configurations.
# It can be a simple flat dictionary (e.g., {"sourceName": "canonicalName"})
# or a nested dictionary scoped by context (e.g., "income_statement").
MappingConfig = Union[dict[str, str], dict[Optional[str], dict[str, str]]]

__all__ = ["MappingConfig"]
