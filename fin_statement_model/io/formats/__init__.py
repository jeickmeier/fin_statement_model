"""Format-specific IO implementations.

This module contains readers and writers for various data formats.
Each format is organized in its own submodule.
"""

# Import all concrete format handlers (flat files) to ensure registry side-effects.

from .csv_reader import CsvReader
from .dataframe_reader import DataFrameReader
from .dataframe_writer import DataFrameWriter
from .dict_reader import DictReader
from .dict_writer import DictWriter
from .excel_reader import ExcelReader
from .excel_writer import ExcelWriter
from .fmp_reader import FmpReader
from .markdown_writer import MarkdownWriter

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
