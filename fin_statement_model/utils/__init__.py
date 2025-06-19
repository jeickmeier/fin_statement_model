"""Utility sub-package for generic helper functions that can be shared across layers.

Currently exposes:
    • formatting – helpers for number & value formatting.
"""

from __future__ import annotations

# Re-export frequently accessed modules to offer shorter import paths
from .formatting import (
    apply_sign_convention,
    format_numbers,
    render_values,
)

__all__ = [
    "apply_sign_convention",
    "format_numbers",
    "render_values",
]
