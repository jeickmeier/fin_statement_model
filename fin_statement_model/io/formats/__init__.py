"""Format-specific IO implementations.

This module contains readers and writers for various data formats.
Each format is organized in its own submodule.
"""

# Import all format handlers to ensure they're registered
from .api import FmpReader
from .csv import CsvReader
from .dataframe import DataFrameReader, DataFrameWriter
from .dict import DictReader, DictWriter
from .excel import ExcelReader, ExcelWriter
from .markdown import MarkdownWriter

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
