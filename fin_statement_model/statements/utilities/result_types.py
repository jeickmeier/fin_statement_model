"""Common result types for standardized error handling in the statements module.

This module provides consistent result types and error collection utilities
to standardize error handling across the statements package. These types
enable functional error handling without exceptions for operations that
can fail in expected ways.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Generic, Optional, TypeVar

logger = logging.getLogger(__name__)

__all__ = [
    "ErrorCollector",
    "ErrorDetail",
    "ErrorSeverity",
    "Failure",
    "OperationResult",
    "ProcessingResult",
    "Result",
    "Success",
    "ValidationResult",
]

T = TypeVar("T")


class ErrorSeverity(Enum):
    """Severity levels for errors."""

    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ErrorDetail:
    """Detailed information about an error.

    Attributes:
        code: Error code for programmatic handling
        message: Human-readable error message
        context: Optional context about where/what caused the error
        severity: Severity level of the error
        source: Optional source identifier (e.g., item ID, file path)
    """

    code: str
    message: str
    context: Optional[str] = None
    severity: ErrorSeverity = ErrorSeverity.ERROR
    source: Optional[str] = None

    def __str__(self) -> str:
        """Format error as string."""
        parts = [f"[{self.severity.value.upper()}]"]
        if self.source:
            parts.append(f"{self.source}:")
        parts.append(self.message)
        if self.context:
            parts.append(f"({self.context})")
        return " ".join(parts)


class Result(ABC, Generic[T]):
    """Abstract base class for operation results.

    Provides a functional approach to error handling, allowing
    operations to return either success or failure without exceptions.
    """

    @abstractmethod
    def is_success(self) -> bool:
        """Check if the result represents success."""

    @abstractmethod
    def is_failure(self) -> bool:
        """Check if the result represents failure."""

    @abstractmethod
    def get_value(self) -> Optional[T]:
        """Get the success value if available."""

    @abstractmethod
    def get_errors(self) -> list[ErrorDetail]:
        """Get error details if this is a failure."""

    def unwrap(self) -> T:
        """Get the value or raise an exception if failed.

        Raises:
            ValueError: If the result is a failure.
        """
        if self.is_failure():
            errors_str = "\n".join(str(e) for e in self.get_errors())
            raise ValueError(f"Cannot unwrap failed result:\n{errors_str}")
        return self.get_value()  # type: ignore

    def unwrap_or(self, default: T) -> T:
        """Get the value or return a default if failed."""
        return self.get_value() if self.is_success() else default


@dataclass(frozen=True)
class Success(Result[T]):
    """Represents a successful operation result."""

    value: T

    def is_success(self) -> bool:
        """Always returns True for Success."""
        return True

    def is_failure(self) -> bool:
        """Always returns False for Success."""
        return False

    def get_value(self) -> Optional[T]:
        """Return the success value."""
        return self.value

    def get_errors(self) -> list[ErrorDetail]:
        """Return empty list for Success."""
        return []


@dataclass(frozen=True)
class Failure(Result[T]):
    """Represents a failed operation result."""

    errors: list[ErrorDetail] = field(default_factory=list)

    def __post_init__(self):
        """Ensure at least one error is present."""
        if not self.errors:
            # Add a default error if none provided
            object.__setattr__(
                self,
                "errors",
                [
                    ErrorDetail(
                        code="unknown",
                        message="Operation failed with no specific error",
                    )
                ],
            )

    def is_success(self) -> bool:
        """Always returns False for Failure."""
        return False

    def is_failure(self) -> bool:
        """Always returns True for Failure."""
        return True

    def get_value(self) -> Optional[T]:
        """Always returns None for Failure."""
        return None

    def get_errors(self) -> list[ErrorDetail]:
        """Return the error details."""
        return self.errors

    @classmethod
    def from_exception(cls, exc: Exception, code: str = "exception") -> "Failure[T]":
        """Create a Failure from an exception."""
        return cls(
            errors=[
                ErrorDetail(
                    code=code,
                    message=str(exc),
                    context=type(exc).__name__,
                    severity=ErrorSeverity.ERROR,
                )
            ]
        )


class ErrorCollector:
    """Collects errors during multi-step operations.

    Useful for operations that should continue collecting errors
    rather than failing fast on the first error.
    """

    def __init__(self):
        """Initialize an empty error collector."""
        self._errors: list[ErrorDetail] = []
        self._warnings: list[ErrorDetail] = []

    def add_error(
        self,
        code: str,
        message: str,
        context: Optional[str] = None,
        source: Optional[str] = None,
    ) -> None:
        """Add an error to the collector."""
        self._errors.append(
            ErrorDetail(
                code=code,
                message=message,
                context=context,
                severity=ErrorSeverity.ERROR,
                source=source,
            )
        )

    def add_warning(
        self,
        code: str,
        message: str,
        context: Optional[str] = None,
        source: Optional[str] = None,
    ) -> None:
        """Add a warning to the collector."""
        self._warnings.append(
            ErrorDetail(
                code=code,
                message=message,
                context=context,
                severity=ErrorSeverity.WARNING,
                source=source,
            )
        )

    def add_from_result(self, result: Result, source: Optional[str] = None) -> None:
        """Add errors from a Result object."""
        if result.is_failure():
            for error in result.get_errors():
                # Override source if provided
                if source:
                    new_error = ErrorDetail(
                        code=error.code,
                        message=error.message,
                        context=error.context,
                        severity=error.severity,
                        source=source,
                    )
                    if new_error.severity == ErrorSeverity.WARNING:
                        self._warnings.append(new_error)
                    else:
                        self._errors.append(new_error)
                elif error.severity == ErrorSeverity.WARNING:
                    self._warnings.append(error)
                else:
                    self._errors.append(error)

    def has_errors(self) -> bool:
        """Check if any errors have been collected."""
        return len(self._errors) > 0

    def has_warnings(self) -> bool:
        """Check if any warnings have been collected."""
        return len(self._warnings) > 0

    def get_errors(self) -> list[ErrorDetail]:
        """Get all collected errors (not warnings)."""
        return list(self._errors)

    def get_warnings(self) -> list[ErrorDetail]:
        """Get all collected warnings."""
        return list(self._warnings)

    def get_all(self) -> list[ErrorDetail]:
        """Get all collected errors and warnings."""
        return self._errors + self._warnings

    def to_result(self, value: T = None) -> Result[T]:
        """Convert collector state to a Result.

        If there are errors, returns Failure.
        Otherwise returns Success with the provided value.
        """
        if self.has_errors():
            return Failure(errors=self._errors)
        return Success(value=value)

    def log_all(self, prefix: str = "") -> None:
        """Log all collected errors and warnings."""
        for warning in self._warnings:
            logger.warning(f"{prefix}{warning}")
        for error in self._errors:
            logger.error(f"{prefix}{error}")


# Type aliases for common result types
OperationResult = Result[
    bool
]  # For operations that succeed/fail without returning data
ValidationResult = Result[bool]  # For validation operations
ProcessingResult = Result[dict[str, any]]  # For processing operations that return data


def combine_results(*results: Result[T]) -> Result[list[T]]:
    """Combine multiple results into a single result.

    If all results are successful, returns Success with list of values.
    If any result is a failure, returns Failure with all errors combined.
    """
    collector = ErrorCollector()
    values = []

    for result in results:
        if result.is_success():
            values.append(result.get_value())
        else:
            for error in result.get_errors():
                if error.severity == ErrorSeverity.WARNING:
                    collector.add_warning(
                        error.code, error.message, error.context, error.source
                    )
                else:
                    collector.add_error(
                        error.code, error.message, error.context, error.source
                    )

    if collector.has_errors():
        return Failure(errors=collector.get_all())
    return Success(value=values)
