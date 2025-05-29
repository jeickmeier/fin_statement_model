"""Formatting and data fetching for financial statements.

This package provides tools for:
- Fetching data from graphs for statement display
- Formatting statements as DataFrames
- Applying formatting rules and conventions
"""

from .data_fetcher import DataFetcher, FetchResult, NodeData
from .formatter import StatementFormatter

__all__ = [
    # Data Fetching
    "DataFetcher",
    "FetchResult",
    "NodeData",
    # Formatting
    "StatementFormatter",
]
