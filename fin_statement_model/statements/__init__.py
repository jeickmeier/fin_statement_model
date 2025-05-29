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
  - Centralizing ID resolution logic between statement items and graph nodes
    (`IDResolver`).

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
from .configs.validator import StatementConfig

# Building
from .structure.builder import StatementStructureBuilder

# Registry
from .registry import StatementRegistry

# ID Resolution
from .population.id_resolver import IDResolver

# Data Fetching
from .formatting.data_fetcher import DataFetcher, FetchResult, NodeData

# Item Processors
from .population.item_processors import (
    ProcessorResult,
    ItemProcessor,
    MetricItemProcessor,
    CalculatedItemProcessor,
    SubtotalItemProcessor,
    ItemProcessorManager,
)

# Result Types for Error Handling
from .utilities.result_types import (
    Result,
    Success,
    Failure,
    ErrorDetail,
    ErrorSeverity,
    ErrorCollector,
    OperationResult,
    ValidationResult,
    ProcessingResult,
    combine_results,
)

# Retry Handler
from .utilities.retry_handler import (
    RetryHandler,
    RetryConfig,
    RetryStrategy,
    RetryResult,
    BackoffStrategy,
    ExponentialBackoff,
    LinearBackoff,
    ConstantBackoff,
    retry_with_exponential_backoff,
    retry_on_specific_errors,
)

# Populator
from .population.populator import populate_graph_from_statement

# Formatting
from .formatting.formatter import StatementFormatter

# High-level Orchestration functions (previously Factory)
from .orchestration.factory import (
    create_statement_dataframe,
    export_statements_to_excel,
    export_statements_to_json,
)

# Errors specific to statements
from .errors import StatementError, ConfigurationError

# Public API definition
__all__ = [
    "BackoffStrategy",
    "CalculatedItemProcessor",
    "CalculatedLineItem",
    "ConfigurationError",
    "ConstantBackoff",
    # Data Fetching
    "DataFetcher",
    "ErrorCollector",
    "ErrorDetail",
    "ErrorSeverity",
    "ExponentialBackoff",
    "Failure",
    "FetchResult",
    "IDResolver",
    "ItemProcessor",
    "ItemProcessorManager",
    "LineItem",
    "LinearBackoff",
    "MetricItemProcessor",
    "MetricLineItem",
    "NodeData",
    "OperationResult",
    "ProcessingResult",
    # Item Processors
    "ProcessorResult",
    # Result Types
    "Result",
    "RetryConfig",
    # Retry Handler
    "RetryHandler",
    "RetryResult",
    "RetryStrategy",
    "Section",
    "StatementConfig",
    "StatementError",
    "StatementFormatter",
    "StatementItem",
    "StatementItemType",
    "StatementRegistry",
    "StatementStructure",
    "StatementStructureBuilder",
    "SubtotalItemProcessor",
    "SubtotalLineItem",
    "Success",
    "ValidationResult",
    "combine_results",
    "create_statement_dataframe",
    "export_statements_to_excel",
    "export_statements_to_json",
    "populate_graph_from_statement",
    "retry_on_specific_errors",
    "retry_with_exponential_backoff",
    # --- Removed --- #
    # "FinancialStatementGraph", (unless reintroduced)
    # "StatementFactory", (class)
    # "StatementManager",
]

# Note: FinancialStatementGraph removed as part of refactor, assuming its
# responsibilities are covered by core Graph and statement-specific components.
