"""Reusable mixins and decorators for IO operations.

This module provides shared functionality for readers and writers including
error handling decorators and mixins for consistent behavior.
"""

import os
import functools
import logging
from abc import abstractmethod
from typing import Any, TypeVar, Optional
from collections.abc import Callable

from fin_statement_model.core.graph import Graph
from .base import DataReader
from fin_statement_model.io.exceptions import ReadError, WriteError

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


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
                f"File not found: {path}", source=path, reader_type=self.__class__.__name__
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


class ConfigurableReaderMixin:
    """Mixin for readers that use configuration objects.

    Provides common methods for accessing configuration values
    with proper error handling.
    """

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Safely get a configuration value.

        Args:
            key: Configuration key to retrieve.
            default: Default value if key is not found.

        Returns:
            Configuration value or default.
        """
        if hasattr(self, "cfg") and self.cfg:
            return getattr(self.cfg, key, default)
        return default

    def require_config_value(self, key: str) -> Any:
        """Get a required configuration value.

        Args:
            key: Configuration key to retrieve.

        Returns:
            Configuration value.

        Raises:
            ReadError: If the configuration value is missing.
        """
        if not hasattr(self, "cfg") or not self.cfg:
            raise ReadError(
                "Reader not properly configured: missing configuration object",
                reader_type=self.__class__.__name__,
            )

        value = getattr(self.cfg, key, None)
        if value is None:
            raise ReadError(
                f"Required configuration value '{key}' is missing",
                reader_type=self.__class__.__name__,
            )

        return value


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
        self, graph: Graph, include_nodes: Optional[list[str]] = None, calculate: bool = True
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
        self, items: list[Any], process_func: callable, progress_callback: Optional[callable] = None
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
    """Utility class for collecting and summarizing validation results.

    Useful for batch operations where you want to collect all validation
    results and report them together.
    """

    def __init__(self):
        self.results: list[tuple[str, bool, str]] = []
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def add_result(self, item_name: str, is_valid: bool, message: str) -> None:
        """Add a validation result."""
        self.results.append((item_name, is_valid, message))

        if not is_valid:
            self.errors.append(f"{item_name}: {message}")
        elif "warning" in message.lower():
            self.warnings.append(f"{item_name}: {message}")

    def has_errors(self) -> bool:
        """Check if any errors were collected."""
        return len(self.errors) > 0

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all validation results."""
        total = len(self.results)
        valid = sum(1 for _, is_valid, _ in self.results if is_valid)

        return {
            "total": total,
            "valid": valid,
            "invalid": total - valid,
            "errors": self.errors.copy(),
            "warnings": self.warnings.copy(),
            "error_rate": (total - valid) / total if total > 0 else 0.0,
        }
