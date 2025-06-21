"""Core type aliases shared across the IO package."""

from __future__ import annotations

from typing import Optional, Union

# MappingConfig was previously duplicated; this is now the single source of truth.
MappingConfig = Union[dict[str, str], dict[Optional[str], dict[str, str]]]

__all__ = ["MappingConfig"]
