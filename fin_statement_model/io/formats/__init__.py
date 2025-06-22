"""Format-specific IO implementations.

This module contains readers and writers for various data formats.
Each format is organized in its own submodule.
"""

# Import all concrete format handlers (flat files) to ensure registry side-effects.

from .csv_reader import CsvReader  # noqa: F401
from .dataframe_reader import DataFrameReader  # noqa: F401
from .dataframe_writer import DataFrameWriter  # noqa: F401
from .dict_reader import DictReader  # noqa: F401
from .dict_writer import DictWriter  # noqa: F401
from .excel_reader import ExcelReader  # noqa: F401
from .excel_writer import ExcelWriter  # noqa: F401
from .fmp_reader import FmpReader  # noqa: F401
from .markdown_writer import MarkdownWriter  # noqa: F401

__all__ = [
    # CSV
    "CsvReader",
    # DataFrame
    "DataFrameReader",
    "DataFrameWriter",
    # Dict
    "DictReader",
    "DictWriter",
    # Excel
    "ExcelReader",
    "ExcelWriter",
    # API
    "FmpReader",
    # Markdown
    "MarkdownWriter",
]
