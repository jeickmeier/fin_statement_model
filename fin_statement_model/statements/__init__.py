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
# -----------------------------------------------------------------------------
# Convenience helpers - discovery of built-in statement configs
# -----------------------------------------------------------------------------
from pathlib import Path
from typing import Any

from fin_statement_model.core.nodes import standard_node_registry

# Import UnifiedNodeValidator for convenience
from fin_statement_model.statements.validation import UnifiedNodeValidator

from .configs.models import AdjustmentFilterSpec

# Configuration related classes
from .configs.validator import StatementConfig

# Errors specific to statements
from .errors import ConfigurationError, StatementError

# Data Fetching
from .formatting.data_fetcher import DataFetcher, FetchResult, NodeData

# Formatting
from .formatting.formatter import StatementFormatter
from .orchestration.exporter import (
    export_statements_to_excel,
    export_statements_to_json,
)

# High-level orchestration functions
from .orchestration.orchestrator import create_statement_dataframe

# ID Resolution
from .population.id_resolver import IDResolver

# Item Processors
from .population.item_processors import (
    CalculatedItemProcessor,
    ItemProcessor,
    ItemProcessorManager,
    MetricItemProcessor,
    ProcessorResult,
    SubtotalItemProcessor,
)

# Populator
from .population.populator import populate_graph_from_statement

# Registry
from .registry import StatementRegistry
from .structure import (
    CalculatedLineItem,
    LineItem,
    Section,
    StatementItem,  # Added base item type if needed
    StatementItemType,
    StatementStructure,
    SubtotalLineItem,
)

# Legacy builder was removed in version 0.1.0; use `load_structure()` instead.
from .utilities.cli_formatters import pretty_print_errors

# Result Types for Error Handling
from .utilities.result_types import (
    ErrorCollector,
    ErrorDetail,
    ErrorSeverity,
    Failure,
    OperationResult,
    ProcessingResult,
    Result,
    Success,
    ValidationResult,
    combine_results,
)

# Retry Handler
from .utilities.retry_handler import (
    BackoffStrategy,
    ConstantBackoff,
    ExponentialBackoff,
    LinearBackoff,
    RetryConfig,
    RetryHandler,
    RetryResult,
    RetryStrategy,
    retry_on_specific_errors,
    retry_with_exponential_backoff,
)


def list_available_builtin_configs() -> list[str]:
    """Return the IDs of YAML configs bundled with ``fin_statement_model``.

    The library ships a small set of reference statement configurations in
    ``fin_statement_model/statements/configs``.  Each config is stored as a
    YAML file whose *stem* (filename without extension) serves as the public
    *statement_id* when loading the config.

    Returns:
        A list of available built-in statement IDs sorted alphabetically.
    """
    cfg_dir = Path(__file__).parent / "configs"
    if not cfg_dir.exists():
        return []

    return sorted(p.stem for p in cfg_dir.glob("*.yaml"))


# -----------------------------------------------------------------------------
# Expand public API
# -----------------------------------------------------------------------------


# Node validation convenience functions
def create_validated_statement_config(
    config_data: dict[str, Any],
    enable_node_validation: bool = True,
    strict_mode: bool = False,
    node_validator: UnifiedNodeValidator | None = None,
) -> StatementConfig:
    """Create a StatementConfig with optional node validation enabled.

    Args:
        config_data: Dictionary containing the raw configuration data.
        enable_node_validation: If True, validates node IDs using UnifiedNodeValidator.
        strict_mode: If True, treats node validation failures as errors.
        node_validator: Optional pre-configured UnifiedNodeValidator instance.

    Returns:
        StatementConfig instance with validation configured.

    Example:
        >>> config_data = {...}  # Your YAML/JSON config as dict
        >>> config = create_validated_statement_config(config_data, enable_node_validation=True, strict_mode=True)
        >>> errors = config.validate_config()
        >>> if errors:
        ...     print("Validation failed:", errors)
    """
    return StatementConfig(
        config_data=config_data,
        enable_node_validation=enable_node_validation,
        node_validation_strict=strict_mode,
        node_validator=node_validator,
    )


def validate_statement_config_with_nodes(
    config_path_or_data: str | dict[str, Any],
    strict_mode: bool = False,
    auto_standardize: bool = True,
) -> tuple[StatementConfig, list[ErrorDetail]]:
    """Validate a statement configuration with comprehensive node validation.

    This is a high-level convenience function that handles the entire validation
    process including node ID validation.

    Args:
        config_path_or_data: Path to config file or config data dict.
        strict_mode: If True, treats node validation failures as errors.
        auto_standardize: If True, auto-standardize alternate node names.

    Returns:
        Tuple of (StatementConfig, validation_errors), where validation_errors is a list of ErrorDetail.
        If the list is empty, validation was successful.

    Example:
        >>> config, errors = validate_statement_config_with_nodes("path/to/income_statement.yaml", strict_mode=True)
        >>> if errors:
        ...     print("Validation failed:", errors)
        >>> else:
        ...     print("Validation passed!")
    """
    # File-based loading is no longer supported; only in-memory dicts
    if not isinstance(config_path_or_data, dict):
        raise ConfigurationError(
            message="File-based loading of statement configs is no longer supported; please pass a configuration dictionary."
        )
    config_data = config_path_or_data

    # Create validator
    node_validator = UnifiedNodeValidator(
        standard_node_registry,
        strict_mode=strict_mode,
        auto_standardize=auto_standardize,
        warn_on_non_standard=True,
        enable_patterns=True,
    )

    # Create and validate config
    config = StatementConfig(
        config_data=config_data,
        enable_node_validation=True,
        node_validation_strict=strict_mode,
        node_validator=node_validator,
    )

    errors = config.validate_config()
    return config, errors


# Public API definition
__all__ = [
    "AdjustmentFilterSpec",
    "BackoffStrategy",
    "CalculatedItemProcessor",
    "CalculatedLineItem",
    "ConfigurationError",
    "ConstantBackoff",
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
    "ProcessorResult",
    "Result",
    "RetryConfig",
    "RetryHandler",
    "RetryResult",
    "RetryStrategy",
    "Section",
    "StatementError",
    "StatementFormatter",
    "StatementItem",
    "StatementItemType",
    "StatementRegistry",
    "StatementStructure",
    "SubtotalItemProcessor",
    "SubtotalLineItem",
    "Success",
    "UnifiedNodeValidator",
    "ValidationResult",
    "combine_results",
    "create_statement_dataframe",
    "export_statements_to_excel",
    "export_statements_to_json",
    "list_available_builtin_configs",
    "populate_graph_from_statement",
    "pretty_print_errors",
    "retry_on_specific_errors",
    "retry_with_exponential_backoff",
]

# Note: FinancialStatementGraph removed as part of refactor, assuming its
# responsibilities are covered by core Graph and statement-specific components.
