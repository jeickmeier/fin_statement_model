"""General IO utility placeholders.

Heavy helpers have been relocated to their thematic modules.  The file now only
re-exports common type aliases to avoid breaking legacy imports.
"""

from __future__ import annotations

from .types import MappingConfig  # re-export for backward compatibility

__all__ = ["MappingConfig"]
