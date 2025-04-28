"""Financial Statements Layer (`fin_statement_model.statements`).

This package provides domain-specific abstractions for defining, building,
managing, and presenting financial statements (like Income Statement,
Balance Sheet, Cash Flow Statement) based on underlying configurations.

It sits above the `core` layer and orchestrates the use of core components
(like `Graph`, `Node`) within the context of financial statement structures.
It utilizes configurations (often YAML files) to define the layout, items,
and calculations of a statement.

Key functionalities include:
  - Defining statement structure (`StatementStructure`, `Section`, `LineItem` etc.)
  - Loading and validating statement configurations (`StatementConfig`).
  - Building `StatementStructure` objects from configurations
    (`StatementStructureBuilder`).
  - Managing multiple loaded statements (`StatementRegistry`).
  - Populating a `core.graph.Graph` with calculation nodes based on statement
    definitions (`populate_graph_from_statement`).
  - Formatting statement data retrieved from a graph into user-friendly formats,
    primarily pandas DataFrames (`StatementFormatter`).
  - High-level functions to streamline common workflows like generating a
    statement DataFrame or exporting statements to files (`create_statement_dataframe`,
    `export_statements_to_excel`).

This package imports from `core` and `io` (indirectly via `factory`), but should
not be imported by `core`.
"""

# Core statement structure components
from .structure import (
    StatementStructure,
    Section,
    LineItem,
    CalculatedLineItem,
    SubtotalLineItem,
    StatementItemType,
    StatementItem,  # Added base item type if needed
)

# Configuration related classes
from .config.config import StatementConfig

# Building
from .builder import StatementStructureBuilder

# Registry
from .registry import StatementRegistry

# Populator
from .populator import populate_graph_from_statement

# Formatting
# Ensure formatter is imported correctly if it's in a sub-package
try:
    from .formatter import StatementFormatter  # If __init__.py exists in formatter
except ImportError:
    from .formatter.formatter import StatementFormatter  # Direct import
# High-level Orchestration functions (previously Factory)
from .factory import (
    create_statement_dataframe,
    export_statements_to_excel,
    export_statements_to_json,
)

# Errors specific to statements
from .errors import StatementError, ConfigurationError

# Public API definition
__all__ = [
    "CalculatedLineItem",
    "ConfigurationError",
    "LineItem",
    "Section",
    "StatementConfig",
    "StatementError",
    "StatementFormatter",
    "StatementItem",
    "StatementItemType",
    "StatementRegistry",
    "StatementStructure",
    "StatementStructureBuilder",
    "SubtotalLineItem",
    "create_statement_dataframe",
    "export_statements_to_excel",
    "export_statements_to_json",
    "populate_graph_from_statement",
    # --- Removed --- #
    # "FinancialStatementGraph", (unless reintroduced)
    # "StatementFactory", (class)
    # "StatementManager",
]

# Note: FinancialStatementGraph removed as part of refactor, assuming its
# responsibilities are covered by core Graph and statement-specific components.
