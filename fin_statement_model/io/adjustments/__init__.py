"""Specialized I/O for financial adjustments.

This package provides helpers for importing and exporting `Adjustment` objects,
primarily using Excel files. It contains the high-level functions for these
operations as well as the Pydantic model (`AdjustmentRowModel`) used for
validating the data during import.
"""

from .excel_io import (
    export_adjustments_to_excel,
    load_adjustments_from_excel,
    read_excel,
    write_excel,
)
from .row_models import AdjustmentRowModel

__all__ = [
    "AdjustmentRowModel",
    "export_adjustments_to_excel",
    "load_adjustments_from_excel",
    "read_excel",
    "write_excel",
]
