"""Readers for various data formats into the Financial Statement Model.

Exposes functions for reading data from different sources like configuration files,
Excel, CSV (TBD), etc.
"""

# Explicitly import each reader module to ensure registration decorators run.
from . import base
from . import cell_reader
from . import csv
from . import dataframe
from . import dict
from . import excel
from . import fmp # Ensure FMP reader module is imported
from . import statement_config_reader

# --- Public API Exports --- #

# Expose functions directly if preferred
from .statement_config_reader import (
    read_statement_config_from_path,
    list_available_builtin_configs,
    read_builtin_statement_config,
)
from .cell_reader import import_from_cells

# Expose reader base class and specific classes if needed (usually not needed by end-users)
# from .base import DataReader
# from .csv import CsvReader
# from .excel import ExcelReader
# ... etc

__all__ = [
    # Statement Config Reader Functions
    "read_statement_config_from_path",
    "list_available_builtin_configs",
    "read_builtin_statement_config",
    # Cell Reader Function
    "import_from_cells",
    # Add other directly exported functions/classes here
    # Reader classes themselves are typically accessed via the io.registry or io.read_data facade
]
