"""Reusable mixins and decorators for IO operations.

This module provides shared functionality for readers and writers including
error handling decorators and mixins for consistent behavior.
"""

import os
import functools
import logging
import importlib.resources
import yaml
from abc import abstractmethod
from typing import Any, TypeVar, Optional, ClassVar
from collections.abc import Callable

from fin_statement_model.core.graph import Graph
from .base import DataReader
from fin_statement_model.io.exceptions import ReadError, WriteError
from fin_statement_model.io.core.utils import normalize_mapping

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


# ===== Mapping Mixins =====


class MappingAwareMixin:
    """Mixin for readers that support name mapping functionality.

    Provides common methods for:
    - Loading default mappings from YAML files
    - Getting effective mappings based on context
    - Applying mappings to source names
    """

    # Class variable to store default mappings per reader type
    _default_mappings_cache: ClassVar[dict[str, dict]] = {}

    @classmethod
    def _get_default_mapping_path(cls) -> Optional[str]:
        """Get the path to default mapping YAML file for this reader.

        Subclasses should override this to specify their default mapping file.

        Returns:
            Path relative to fin_statement_model.io.config.mappings package,
            or None if no default mappings.
        """
        return None

    @classmethod
    def _load_default_mappings(cls) -> dict[str, dict[str, str]]:
        """Load default mapping configurations from YAML file.

        Returns:
            Dictionary containing default mappings, empty if none found.
        """
        cache_key = cls.__name__

        # Return cached value if available
        if cache_key in cls._default_mappings_cache:
            return cls._default_mappings_cache[cache_key]

        mapping_path = cls._get_default_mapping_path()
        if not mapping_path:
            cls._default_mappings_cache[cache_key] = {}
            return {}

        try:
            yaml_content = (
                importlib.resources.files("fin_statement_model.io.config.mappings")
                .joinpath(mapping_path)
                .read_text(encoding="utf-8")
            )
            mappings = yaml.safe_load(yaml_content) or {}
            cls._default_mappings_cache[cache_key] = mappings
            logger.debug(f"Loaded default mappings for {cls.__name__}")
            return mappings
        except Exception:
            logger.exception(f"Failed to load default mappings for {cls.__name__}")
            cls._default_mappings_cache[cache_key] = {}
            return {}

    def _get_mapping(self, context_key: Optional[str] = None) -> dict[str, str]:
        """Get the effective mapping based on context and configuration.

        Args:
            context_key: Optional context (e.g., sheet name, statement type)
                        to select specific mapping scope.

        Returns:
            Flat dictionary mapping source names to canonical names.

        Raises:
            TypeError: If mapping configuration is invalid.
        """
        # Load defaults if not already loaded
        default_mappings = self._load_default_mappings()

        # Get user config
        user_config = self.get_config_value("mapping_config")

        # Start with defaults for the context
        mapping = normalize_mapping(default_mappings, context_key=context_key)

        # Overlay user mappings if provided
        if user_config:
            user_mapping = normalize_mapping(user_config, context_key=context_key)
            mapping.update(user_mapping)

        return mapping

    def _apply_mapping(self, source_name: str, mapping: dict[str, str]) -> str:
        """Apply mapping to convert source name to canonical name.

        Args:
            source_name: Original name from the data source
            mapping: Mapping dictionary

        Returns:
            Canonical name (mapped name or original if no mapping exists)
        """
        return mapping.get(source_name, source_name)


# ===== Validation Mixins =====


class ValidationMixin:
    """Mixin for readers that need comprehensive validation capabilities.

    Provides standardized validation methods for common data validation scenarios
    including data type validation, range validation, and custom validation rules.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize validation mixin."""
        super().__init__(*args, **kwargs)
        self._validation_context: dict[str, Any] = {}

    def set_validation_context(self, **context: Any) -> None:
        """Set validation context for error reporting.

        Args:
            **context: Key-value pairs to store as validation context.
        """
        self._validation_context.update(context)

    def get_validation_context(self) -> dict[str, Any]:
        """Get current validation context.

        Returns:
            Dictionary containing current validation context.
        """
        return self._validation_context.copy()

    def validate_required_columns(
        self,
        df: Any,  # pandas.DataFrame
        required_columns: list[str],
        source_identifier: str = "data source",
    ) -> None:
        """Validate that required columns exist in DataFrame.

        Args:
            df: DataFrame to validate.
            required_columns: List of required column names.
            source_identifier: Identifier for the data source (for error messages).

        Raises:
            ReadError: If required columns are missing.
        """
        if not hasattr(df, "columns"):
            raise ReadError(
                "Invalid data structure: expected DataFrame with columns attribute",
                source=source_identifier,
                reader_type=getattr(self, "__class__", {}).get("__name__", "Unknown"),
            )

        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            raise ReadError(
                f"Missing required columns in {source_identifier}: {missing_columns}",
                source=source_identifier,
                reader_type=getattr(self, "__class__", {}).get("__name__", "Unknown"),
            )

    def validate_column_bounds(
        self,
        df: Any,  # pandas.DataFrame
        column_index: int,
        source_identifier: str = "data source",
        context: str = "column",
    ) -> None:
        """Validate that column index is within DataFrame bounds.

        Args:
            df: DataFrame to validate.
            column_index: 0-based column index to validate.
            source_identifier: Identifier for the data source.
            context: Context description for error messages.

        Raises:
            ReadError: If column index is out of bounds.
        """
        if not hasattr(df, "columns"):
            raise ReadError(
                "Invalid data structure: expected DataFrame with columns attribute",
                source=source_identifier,
                reader_type=getattr(self, "__class__", {}).get("__name__", "Unknown"),
            )

        if column_index >= len(df.columns) or column_index < 0:
            raise ReadError(
                f"{context} index ({column_index + 1}) is out of bounds. "
                f"Found {len(df.columns)} columns.",
                source=source_identifier,
                reader_type=getattr(self, "__class__", {}).get("__name__", "Unknown"),
            )

    def validate_periods_exist(
        self,
        periods: list[str],
        source_identifier: str = "data source",
        min_periods: int = 1,
    ) -> None:
        """Validate that periods list is not empty and meets minimum requirements.

        Args:
            periods: List of period identifiers.
            source_identifier: Identifier for the data source.
            min_periods: Minimum number of periods required.

        Raises:
            ReadError: If periods validation fails.
        """
        if not periods:
            raise ReadError(
                f"No periods found in {source_identifier}",
                source=source_identifier,
                reader_type=getattr(self, "__class__", {}).get("__name__", "Unknown"),
            )

        if len(periods) < min_periods:
            raise ReadError(
                f"Insufficient periods in {source_identifier}. "
                f"Found {len(periods)}, minimum required: {min_periods}",
                source=source_identifier,
                reader_type=getattr(self, "__class__", {}).get("__name__", "Unknown"),
            )

    def validate_numeric_value(
        self,
        value: Any,
        item_name: str,
        period: str,
        validator: Optional["ValidationResultCollector"] = None,
        allow_conversion: bool = True,
    ) -> tuple[bool, Optional[float]]:
        """Validate and optionally convert a value to numeric.

        Args:
            value: Value to validate.
            item_name: Name of the item (for error reporting).
            period: Period identifier (for error reporting).
            validator: Optional ValidationResultCollector to record errors.
            allow_conversion: Whether to attempt string-to-float conversion.

        Returns:
            Tuple of (is_valid, converted_value).
            If is_valid is False, converted_value will be None.
        """
        import pandas as pd

        # Skip NaN/None values
        if pd.isna(value) or value is None:
            return True, None

        # Already numeric
        if isinstance(value, int | float):
            if not pd.isfinite(value):
                error_msg = f"Non-finite numeric value '{value}' for period '{period}'"
                if validator:
                    validator.add_result(item_name, False, error_msg)
                return False, None
            return True, float(value)

        # Attempt conversion if allowed
        if allow_conversion:
            try:
                converted = float(value)
                if not pd.isfinite(converted):
                    error_msg = f"Converted to non-finite value '{converted}' for period '{period}'"
                    if validator:
                        validator.add_result(item_name, False, error_msg)
                    return False, None
                return True, converted
            except (ValueError, TypeError):
                error_msg = f"Non-numeric value '{value}' for period '{period}'"
                if validator:
                    validator.add_result(item_name, False, error_msg)
                return False, None

        # Not numeric and conversion not allowed
        error_msg = f"Non-numeric value '{value}' for period '{period}'"
        if validator:
            validator.add_result(item_name, False, error_msg)
        return False, None

    def validate_node_name(
        self,
        node_name: Any,
        source_name: str = "",
        allow_empty: bool = False,
    ) -> tuple[bool, Optional[str]]:
        """Validate and normalize a node name.

        Args:
            node_name: Raw node name to validate.
            source_name: Original source name (for error context).
            allow_empty: Whether to allow empty/None node names.

        Returns:
            Tuple of (is_valid, normalized_name).
            If is_valid is False, normalized_name will be None.
        """
        import pandas as pd

        if pd.isna(node_name) or node_name is None:
            return allow_empty, None

        if not node_name or (isinstance(node_name, str) and not node_name.strip()):
            return allow_empty, None

        # Normalize to string and strip whitespace
        normalized = str(node_name).strip()
        return True, normalized

    def create_validation_summary(
        self,
        validator: "ValidationResultCollector",
        source_identifier: str,
        operation: str = "processing",
    ) -> str:
        """Create a formatted validation summary message.

        Args:
            validator: ValidationResultCollector with results.
            source_identifier: Identifier for the data source.
            operation: Description of the operation being performed.

        Returns:
            Formatted summary message.
        """
        summary = validator.get_summary()

        if not validator.has_errors():
            return f"Successfully completed {operation} {source_identifier}"

        error_summary = f"Validation errors occurred during {operation} {source_identifier}: "
        error_details = "; ".join(summary["errors"][:5])  # Limit to first 5 errors

        if len(summary["errors"]) > 5:
            error_details += f" (and {len(summary['errors']) - 5} more errors)"

        return error_summary + error_details


# ===== Error Handling Decorators =====


def handle_read_errors(source_attr: str = "source") -> Callable[[F], F]:
    """Decorator to standardize error handling for readers.

    This decorator catches common exceptions during read operations and
    converts them to appropriate ReadError instances with consistent
    error messages and context.

    Args:
        source_attr: Name of the attribute containing the source identifier.
                    Defaults to "source".

    Returns:
        Decorated function that handles errors consistently.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(self: Any, source: Any, **kwargs: Any) -> Any:
            try:
                return func(self, source, **kwargs)
            except ReadError:
                raise  # Re-raise our own errors without modification
            except FileNotFoundError as e:
                raise ReadError(
                    f"File not found: {source}",
                    source=str(source),
                    reader_type=self.__class__.__name__,
                    original_error=e,
                )
            except ValueError as e:
                raise ReadError(
                    f"Invalid value encountered: {e}",
                    source=str(source),
                    reader_type=self.__class__.__name__,
                    original_error=e,
                )
            except Exception as e:
                logger.error(f"Failed to read from {source}: {e}", exc_info=True)
                raise ReadError(
                    f"Failed to process source: {e}",
                    source=str(source),
                    reader_type=self.__class__.__name__,
                    original_error=e,
                ) from e

        return wrapper  # type: ignore

    return decorator


def handle_write_errors(target_attr: str = "target") -> Callable[[F], F]:
    """Decorator to standardize error handling for writers.

    Similar to handle_read_errors but for write operations.

    Args:
        target_attr: Name of the attribute containing the target identifier.
                    Defaults to "target".

    Returns:
        Decorated function that handles errors consistently.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(self: Any, graph: Any, target: Any = None, **kwargs: Any) -> Any:
            try:
                return func(self, graph, target, **kwargs)
            except WriteError:
                raise  # Re-raise our own errors without modification
            except Exception as e:
                logger.error(f"Failed to write to {target}: {e}", exc_info=True)
                raise WriteError(
                    f"Failed to write data: {e}",
                    target=str(target) if target else "unknown",
                    writer_type=self.__class__.__name__,
                    original_error=e,
                ) from e

        return wrapper  # type: ignore

    return decorator


# ===== Reader Mixins =====


class FileBasedReader(DataReader):
    """Base class for file-based readers with common validation.

    This class provides common file validation methods and ensures
    consistent error handling for all file-based readers.

    Note: Subclasses should apply the @handle_read_errors() decorator
    to their read() method implementation for consistent error handling.
    """

    def validate_file_exists(self, path: str) -> None:
        """Validate that file exists.

        Args:
            path: Path to the file to validate.

        Raises:
            ReadError: If the file does not exist.
        """
        if not os.path.exists(path):
            raise ReadError(
                f"File not found: {path}",
                source=path,
                reader_type=self.__class__.__name__,
            )

    def validate_file_extension(self, path: str, valid_extensions: tuple[str, ...]) -> None:
        """Validate file has correct extension.

        Args:
            path: Path to the file to validate.
            valid_extensions: Tuple of valid file extensions (e.g., ('.csv', '.txt')).

        Raises:
            ReadError: If the file extension is not valid.
        """
        if not path.lower().endswith(valid_extensions):
            raise ReadError(
                f"Invalid file extension. Expected one of {valid_extensions}, "
                f"got '{os.path.splitext(path)[1]}'",
                source=path,
                reader_type=self.__class__.__name__,
            )

    @abstractmethod
    def read(self, source: str, **kwargs: Any) -> Graph:
        """Read from file source.

        Subclasses must implement this method with their specific
        file reading logic. It's recommended to apply the @handle_read_errors()
        decorator to the implementation.

        Args:
            source: Path to the file to read.
            **kwargs: Additional reader-specific options.

        Returns:
            Graph populated with data from the file.
        """


class ConfigurationMixin:
    """Enhanced mixin for readers that use configuration objects.

    Provides comprehensive configuration management including:
    - Safe configuration value access with defaults
    - Configuration validation and type checking
    - Configuration inheritance and merging
    - Environment variable integration
    - Configuration context tracking
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize configuration mixin."""
        super().__init__(*args, **kwargs)
        self._config_context: dict[str, Any] = {}
        self._config_overrides: dict[str, Any] = {}

    def set_config_context(self, **context: Any) -> None:
        """Set configuration context for enhanced error reporting.

        Args:
            **context: Key-value pairs to store as configuration context.
        """
        self._config_context.update(context)

    def get_config_context(self) -> dict[str, Any]:
        """Get current configuration context.

        Returns:
            Dictionary containing current configuration context.
        """
        return self._config_context.copy()

    def set_config_override(self, key: str, value: Any) -> None:
        """Set a configuration override for runtime customization.

        Args:
            key: Configuration key to override.
            value: Override value.
        """
        self._config_overrides[key] = value

    def clear_config_overrides(self) -> None:
        """Clear all configuration overrides."""
        self._config_overrides.clear()

    def get_config_value(
        self,
        key: str,
        default: Any = None,
        required: bool = False,
        value_type: Optional[type] = None,
        validator: Optional[callable] = None,
    ) -> Any:
        """Get a configuration value with comprehensive validation and fallback.

        Args:
            key: Configuration key to retrieve.
            default: Default value if key is not found.
            required: Whether the configuration value is required.
            value_type: Expected type for the configuration value.
            validator: Optional validation function that takes the value and returns bool.

        Returns:
            Configuration value, override, or default.

        Raises:
            ReadError: If required value is missing or validation fails.
        """
        # Check for runtime overrides first
        if key in self._config_overrides:
            value = self._config_overrides[key]
        # Then check configuration object
        elif hasattr(self, "cfg") and self.cfg:
            value = getattr(self.cfg, key, default)
        else:
            value = default

        # Handle required values
        if required and value is None:
            raise ReadError(
                f"Required configuration value '{key}' is missing",
                reader_type=self.__class__.__name__,
            )

        # Type validation
        if value is not None and value_type is not None and not isinstance(value, value_type):
            try:
                # Attempt type conversion
                value = value_type(value)
            except (ValueError, TypeError) as e:
                raise ReadError(
                    f"Configuration value '{key}' has invalid type. "
                    f"Expected {value_type.__name__}, got {type(value).__name__}",
                    reader_type=self.__class__.__name__,
                    original_error=e,
                )

        # Custom validation
        if value is not None and validator is not None:
            try:
                if not validator(value):
                    raise ReadError(
                        f"Configuration value '{key}' failed validation",
                        reader_type=self.__class__.__name__,
                    )
            except Exception as e:
                raise ReadError(
                    f"Configuration validation error for '{key}': {e}",
                    reader_type=self.__class__.__name__,
                    original_error=e,
                )

        return value

    def require_config_value(
        self,
        key: str,
        value_type: Optional[type] = None,
        validator: Optional[callable] = None,
    ) -> Any:
        """Get a required configuration value with validation.

        Args:
            key: Configuration key to retrieve.
            value_type: Expected type for the configuration value.
            validator: Optional validation function.

        Returns:
            Configuration value.

        Raises:
            ReadError: If the configuration value is missing or invalid.
        """
        return self.get_config_value(key, required=True, value_type=value_type, validator=validator)

    def get_config_with_env_fallback(
        self,
        key: str,
        env_var: str,
        default: Any = None,
        value_type: Optional[type] = None,
    ) -> Any:
        """Get configuration value with environment variable fallback.

        Args:
            key: Configuration key to retrieve.
            env_var: Environment variable name to check as fallback.
            default: Default value if neither config nor env var is found.
            value_type: Expected type for the value.

        Returns:
            Configuration value, environment variable value, or default.
        """
        import os

        # First try configuration
        value = self.get_config_value(key)

        # If not found, try environment variable
        if value is None:
            env_value = os.getenv(env_var)
            if env_value is not None:
                value = env_value

        # Use default if still None
        if value is None:
            value = default

        # Type conversion if needed
        if value is not None and value_type is not None and not isinstance(value, value_type):
            try:
                value = value_type(value)
            except (ValueError, TypeError):
                logger.warning(
                    f"Failed to convert {key} value '{value}' to {value_type.__name__}, using as-is"
                )

        return value

    def validate_configuration(self) -> "ValidationResultCollector":
        """Validate the entire configuration object.

        Returns:
            ValidationResultCollector with validation results.
        """
        validator = ValidationResultCollector(context=self._config_context)

        if not hasattr(self, "cfg") or not self.cfg:
            validator.add_result(
                "configuration", False, "Missing configuration object", "structure"
            )
            return validator

        # Validate configuration object using Pydantic if available
        try:
            if hasattr(self.cfg, "model_validate"):
                # It's a Pydantic model, validation already happened during creation
                validator.add_result(
                    "configuration", True, "Configuration object is valid", "structure"
                )
            else:
                validator.add_result(
                    "configuration",
                    True,
                    "Configuration object exists (non-Pydantic)",
                    "structure",
                )
        except Exception as e:
            validator.add_result(
                "configuration",
                False,
                f"Configuration validation failed: {e}",
                "validation",
            )

        return validator

    def get_effective_configuration(self) -> dict[str, Any]:
        """Get the effective configuration including overrides.

        Returns:
            Dictionary containing all configuration values with overrides applied.
        """
        config_dict = {}

        # Start with base configuration
        if hasattr(self, "cfg") and self.cfg:
            if hasattr(self.cfg, "model_dump"):
                # Pydantic model
                config_dict = self.cfg.model_dump()
            elif hasattr(self.cfg, "__dict__"):
                # Regular object
                config_dict = vars(self.cfg).copy()

        # Apply overrides
        config_dict.update(self._config_overrides)

        return config_dict

    def merge_configurations(self, *configs: Any) -> dict[str, Any]:
        """Merge multiple configuration objects with precedence.

        Args:
            *configs: Configuration objects to merge (later ones take precedence).

        Returns:
            Merged configuration dictionary.
        """
        merged = {}

        for config in configs:
            if config is None:
                continue

            if hasattr(config, "model_dump"):
                # Pydantic model
                config_dict = config.model_dump()
            elif hasattr(config, "__dict__"):
                # Regular object
                config_dict = vars(config).copy()
            elif isinstance(config, dict):
                # Dictionary
                config_dict = config.copy()
            else:
                logger.warning(f"Unsupported configuration type: {type(config)}")
                continue

            merged.update(config_dict)

        return merged


# Maintain backward compatibility
ConfigurableReaderMixin = ConfigurationMixin


# ===== Writer Mixins =====


class ValueExtractionMixin:
    """Mixin for consistent value extraction from nodes.

    This mixin provides a standardized way to extract values from nodes,
    handling both calculated values and stored values with proper error
    handling.
    """

    def extract_node_value(
        self,
        node: Any,  # Avoid circular import with Node type
        period: str,
        calculate: bool = True,
    ) -> Optional[float]:
        """Extract value from node with consistent error handling.

        Args:
            node: The node to extract value from.
            period: The period to get the value for.
            calculate: If True, attempt to calculate the value using node.calculate().
                      If False, only look for stored values.

        Returns:
            The extracted value as a float, or None if no value could be extracted.
        """
        try:
            # First try calculation if enabled and method exists
            if calculate and hasattr(node, "calculate") and callable(node.calculate):
                value = node.calculate(period)
                if isinstance(value, int | float):
                    return float(value)

            # Fall back to stored values
            if hasattr(node, "values") and isinstance(node.values, dict):
                value = node.values.get(period)
                if isinstance(value, int | float):
                    return float(value)

            return None

        except Exception as e:
            logger.debug(
                f"Failed to extract value from node '{getattr(node, 'name', 'unknown')}' "
                f"for period '{period}': {e}"
            )
            return None


class DataFrameBasedWriter(ValueExtractionMixin):
    """Base class for writers that convert to DataFrame format.

    This base class provides common functionality for writers that
    need to extract data from a graph into a tabular format.

    Note: Subclasses should apply the @handle_write_errors() decorator
    to their write() method implementation for consistent error handling.
    """

    def extract_graph_data(
        self,
        graph: Graph,
        include_nodes: Optional[list[str]] = None,
        calculate: bool = True,
    ) -> dict[str, dict[str, float]]:
        """Extract data from graph nodes into a dictionary format.

        Args:
            graph: The graph to extract data from.
            include_nodes: Optional list of node names to include.
                          If None, includes all nodes.
            calculate: Whether to calculate values or just use stored values.

        Returns:
            Dictionary mapping node names to period-value dictionaries.
        """
        import numpy as np

        periods = sorted(graph.periods) if graph.periods else []
        data: dict[str, dict[str, float]] = {}

        # Determine which nodes to process
        nodes_to_process = include_nodes if include_nodes else list(graph.nodes.keys())

        # Validate requested nodes exist
        if include_nodes:
            missing_nodes = [n for n in include_nodes if n not in graph.nodes]
            if missing_nodes:
                logger.warning(f"Requested nodes not found in graph: {missing_nodes}")
                nodes_to_process = [n for n in include_nodes if n in graph.nodes]

        # Extract data for each node
        for node_id in nodes_to_process:
            node = graph.nodes[node_id]
            row: dict[str, float] = {}

            for period in periods:
                # Use the mixin's extract method for consistent value extraction
                value = self.extract_node_value(node, period, calculate=calculate)

                # Convert None to NaN for DataFrame compatibility
                if (
                    value is None
                    or not isinstance(value, int | float | np.number)
                    or not np.isfinite(value)
                ):
                    value = np.nan

                row[period] = float(value)

            data[node_id] = row

        return data

    @abstractmethod
    def write(self, graph: Graph, target: Any = None, **kwargs: Any) -> Any:
        """Write graph data to target.

        Subclasses must implement this method with their specific
        writing logic. It's recommended to apply the @handle_write_errors()
        decorator to the implementation.

        Args:
            graph: Graph containing data to write.
            target: Target for the output (file path, etc.).
            **kwargs: Additional writer-specific options.

        Returns:
            Writer-specific return value.
        """


# ===== Utility Classes =====


class BatchProcessingMixin:
    """Mixin for readers/writers that process data in batches.

    Provides utilities for chunking data and progress reporting.
    """

    def __init__(self, batch_size: int = 1000):
        """Initialize with batch size.

        Args:
            batch_size: Number of items to process in each batch.
        """
        self.batch_size = batch_size
        self._processed_count = 0
        self._total_count = 0

    def process_in_batches(
        self,
        items: list[Any],
        process_func: callable,
        progress_callback: Optional[callable] = None,
    ) -> list[Any]:
        """Process items in batches.

        Args:
            items: List of items to process.
            process_func: Function to apply to each batch.
            progress_callback: Optional callback for progress updates.

        Returns:
            List of results from processing all batches.
        """
        results = []
        self._total_count = len(items)
        self._processed_count = 0

        for i in range(0, len(items), self.batch_size):
            batch = items[i : i + self.batch_size]
            batch_results = process_func(batch)
            results.extend(batch_results)

            self._processed_count += len(batch)

            if progress_callback:
                progress_callback(self._processed_count, self._total_count)

            # Log progress
            if self._processed_count % (self.batch_size * 10) == 0:
                logger.info(
                    f"Processed {self._processed_count}/{self._total_count} items "
                    f"({self._processed_count / self._total_count * 100:.1f}%)"
                )

        return results

    def get_progress(self) -> tuple[int, int]:
        """Get current progress.

        Returns:
            Tuple of (processed_count, total_count).
        """
        return self._processed_count, self._total_count


class ValidationResultCollector:
    """Enhanced utility class for collecting and summarizing validation results.

    Useful for batch operations where you want to collect all validation
    results and report them together. Supports categorization, context tracking,
    and detailed metrics.
    """

    def __init__(self, context: Optional[dict[str, Any]] = None):
        """Initialize the validation result collector.

        Args:
            context: Optional context information for validation.
        """
        self.results: list[tuple[str, bool, str, str]] = []  # item, valid, message, category
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.context = context or {}
        self._categories: dict[str, int] = {}

    def add_result(
        self,
        item_name: str,
        is_valid: bool,
        message: str,
        category: str = "general",
    ) -> None:
        """Add a validation result with optional categorization.

        Args:
            item_name: Name/identifier of the item being validated.
            is_valid: Whether the validation passed.
            message: Validation message or error description.
            category: Category of validation (e.g., 'data_type', 'range', 'format').
        """
        self.results.append((item_name, is_valid, message, category))

        # Track categories
        if category not in self._categories:
            self._categories[category] = 0
        if not is_valid:
            self._categories[category] += 1

        if not is_valid:
            self.errors.append(f"{item_name}: {message}")
        elif "warning" in message.lower():
            self.warnings.append(f"{item_name}: {message}")

    def add_warning(self, item_name: str, message: str, category: str = "warning") -> None:
        """Add a warning (non-blocking validation issue).

        Args:
            item_name: Name/identifier of the item.
            message: Warning message.
            category: Category of the warning.
        """
        self.warnings.append(f"{item_name}: {message}")
        self.results.append((item_name, True, f"WARNING: {message}", category))

    def has_errors(self) -> bool:
        """Check if any errors were collected."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if any warnings were collected."""
        return len(self.warnings) > 0

    def get_error_count_by_category(self) -> dict[str, int]:
        """Get error counts grouped by category.

        Returns:
            Dictionary mapping category names to error counts.
        """
        return self._categories.copy()

    def get_items_with_errors(self) -> list[str]:
        """Get list of item names that had validation errors.

        Returns:
            List of item names with errors.
        """
        return [item for item, valid, _, _ in self.results if not valid]

    def get_summary(self) -> dict[str, Any]:
        """Get a comprehensive summary of all validation results.

        Returns:
            Dictionary containing validation metrics and summaries.
        """
        total = len(self.results)
        valid = sum(1 for _, is_valid, _, _ in self.results if is_valid)

        # Calculate category-specific metrics
        category_summary = {}
        for category, error_count in self._categories.items():
            category_total = sum(1 for _, _, _, cat in self.results if cat == category)
            category_summary[category] = {
                "total": category_total,
                "errors": error_count,
                "success_rate": (
                    (category_total - error_count) / category_total if category_total > 0 else 1.0
                ),
            }

        return {
            "total": total,
            "valid": valid,
            "invalid": total - valid,
            "errors": self.errors.copy(),
            "warnings": self.warnings.copy(),
            "error_rate": (total - valid) / total if total > 0 else 0.0,
            "warning_count": len(self.warnings),
            "categories": category_summary,
            "context": self.context.copy(),
            "items_with_errors": self.get_items_with_errors(),
        }

    def clear(self) -> None:
        """Clear all collected results."""
        self.results.clear()
        self.errors.clear()
        self.warnings.clear()
        self._categories.clear()

    def merge(self, other: "ValidationResultCollector") -> None:
        """Merge results from another collector.

        Args:
            other: Another ValidationResultCollector to merge from.
        """
        for item, valid, message, category in other.results:
            self.add_result(item, valid, message, category)

    def get_detailed_report(self) -> str:
        """Generate a detailed text report of validation results.

        Returns:
            Formatted string report.
        """
        summary = self.get_summary()

        report_lines = [
            "=== Validation Report ===",
            f"Total items processed: {summary['total']}",
            f"Valid items: {summary['valid']}",
            f"Invalid items: {summary['invalid']}",
            f"Warnings: {summary['warning_count']}",
            f"Overall success rate: {(1 - summary['error_rate']) * 100:.1f}%",
        ]

        if summary["categories"]:
            report_lines.append("\n--- Category Breakdown ---")
            for category, stats in summary["categories"].items():
                report_lines.append(
                    f"{category}: {stats['total']} items, {stats['errors']} errors "
                    f"({stats['success_rate'] * 100:.1f}% success)"
                )

        if self.has_errors():
            report_lines.append("\n--- First 10 Errors ---")
            report_lines.extend(f"  • {error}" for error in self.errors[:10])
            if len(self.errors) > 10:
                report_lines.append(f"  ... and {len(self.errors) - 10} more errors")

        if self.has_warnings():
            report_lines.append("\n--- First 5 Warnings ---")
            report_lines.extend(f"  • {warning}" for warning in self.warnings[:5])
            if len(self.warnings) > 5:
                report_lines.append(f"  ... and {len(self.warnings) - 5} more warnings")

        return "\n".join(report_lines)
