"""Financial statements module for the Financial Statement Model.

This module defines configurable financial statement structures,
including various types of financial statements (Income Statement,
Balance Sheet, Cash Flow) with hierarchical sections and line items
defined through configuration.
"""

# Core statement structure components
from .structure import (
    StatementStructure,
    Section,
    LineItem,
    CalculatedLineItem,
    SubtotalLineItem,
    StatementItemType,
)
# Configuration related classes (loading is now in IO layer)
from .config.config import StatementConfig
# Formatting
from .formatter import StatementFormatter
# Management and Factory
from .manager import StatementManager
from .factory import StatementFactory
# Statement-specific graph facade (if needed as part of public API)
from .graph import FinancialStatementGraph # Updated import path

__all__ = [
    # Structure
    "StatementStructure",
    "Section",
    "LineItem",
    "CalculatedLineItem",
    "SubtotalLineItem",
    "StatementItemType",
    # Config (Building/Validation only)
    "StatementConfig",
    # Formatting
    "StatementFormatter",
    # Management & Factory
    "StatementManager",
    "StatementFactory",
    # Graph Facade
    "FinancialStatementGraph",
]

# Removed CalculationService, ExportService, cell_importer, forecaster etc.
# as they are moved or integrated.
