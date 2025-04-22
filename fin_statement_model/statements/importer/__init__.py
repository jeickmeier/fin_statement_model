"""Importer package for financial statement data.

Provides functions to import raw data (e.g., cell dicts) into the graph.
"""

from .cell_importer import import_from_cells

__all__ = ["import_from_cells"]
