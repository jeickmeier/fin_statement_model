"""Retry handler for managing transient failures in statement operations.

This module provides a flexible retry mechanism that can be used throughout
the statements package to handle transient failures gracefully. It supports
configurable retry strategies, backoff algorithms, and error classification.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
import logging
import secrets
import time
from typing import Generic, Optional, TypeVar, cast

from fin_statement_model.config.access import cfg_or_param
from fin_statement_model.statements.utilities.result_types import (
    ErrorCollector,
    ErrorDetail,
    Failure,
    Result,
)

logger = logging.getLogger(__name__)

__all__ = [
    "BackoffStrategy",
    "ConstantBackoff",
    "ExponentialBackoff",
    "LinearBackoff",
    "RetryConfig",
    "RetryHandler",
    "RetryResult",
    "RetryStrategy",
    "is_retryable_error",
    "retry_on_specific_errors",
    "retry_with_exponential_backoff",
]

T = TypeVar("T")


class RetryStrategy(Enum):
    """Strategy for determining when to retry."""

    IMMEDIATE = "immediate"  # Retry immediately on failure
    BACKOFF = "backoff"  # Use backoff strategy between retries
    CONDITIONAL = "conditional"  # Retry only for specific error types


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_attempts: Maximum number of attempts (including initial).
                     If not provided, uses config default from api.api_retry_count
        strategy: Retry strategy to use
        backoff: Optional backoff strategy for delays
        retryable_errors: Set of error codes that are retryable
        log_retries: Whether to log retry attempts
        collect_all_errors: Whether to collect errors from all attempts
    """

    max_attempts: int | None = None
    strategy: RetryStrategy = RetryStrategy.BACKOFF
    backoff: Optional["BackoffStrategy"] = None
    retryable_errors: set[str] | None = None
    log_retries: bool = True
    collect_all_errors: bool = False

    def __post_init__(self) -> None:
        """Validate configuration and set defaults."""
        # Use config default if not provided
        if self.max_attempts is None:
            self.max_attempts = cfg_or_param("api.api_retry_count", None)

        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        if self.strategy == RetryStrategy.BACKOFF and not self.backoff:
            # Default to exponential backoff
            self.backoff = ExponentialBackoff()

        if self.retryable_errors is None:
            # Default retryable errors
            self.retryable_errors = {
                "timeout",
                "connection_error",
                "rate_limit",
                "temporary_failure",
                "calculation_error",  # For graph calculations
                "node_not_ready",  # For dependency issues
            }


class BackoffStrategy(ABC):
    """Abstract base class for backoff strategies."""

    @abstractmethod
    def get_delay(self, attempt: int) -> float:
        """Get delay in seconds for the given attempt number.

        Args:
            attempt: The attempt number (1-based)

        Returns:
            Delay in seconds before the next retry
        """


class ExponentialBackoff(BackoffStrategy):
    """Exponential backoff strategy with optional jitter."""

    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
        jitter: bool = True,
    ):
        """Initialize exponential backoff.

        Args:
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            multiplier: Multiplier for each retry
            jitter: Whether to add random jitter
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay."""
        delay = min(self.base_delay * (self.multiplier ** (attempt - 1)), self.max_delay)

        if self.jitter:
            # Add up to 20% jitter (non-crypto randomness acceptable)
            jitter_factor = secrets.randbelow(10000) / 10000  # 0.0-0.9999
            jitter_amount = delay * 0.2 * jitter_factor
            delay += jitter_amount

        return delay


class LinearBackoff(BackoffStrategy):
    """Linear backoff strategy."""

    def __init__(self, base_delay: float = 1.0, increment: float = 1.0):
        """Initialize linear backoff.

        Args:
            base_delay: Initial delay in seconds
            increment: Increment for each retry
        """
        self.base_delay = base_delay
        self.increment = increment

    def get_delay(self, attempt: int) -> float:
        """Calculate linear backoff delay."""
        return self.base_delay + (attempt - 1) * self.increment


class ConstantBackoff(BackoffStrategy):
    """Constant delay backoff strategy."""

    def __init__(self, delay: float = 1.0):
        """Initialize constant backoff.

        Args:
            delay: Constant delay in seconds
        """
        self.delay = delay

    def get_delay(self, attempt: int) -> float:
        """Return constant delay."""
        _ = attempt  # Parameter intentionally unused in constant backoff
        return self.delay


@dataclass
class RetryResult(Generic[T]):
    """Result of a retry operation.

    Attributes:
        result: The final result (success or failure)
        attempts: Number of attempts made
        total_delay: Total delay time in seconds
        all_errors: All errors collected if configured
    """

    result: Result[T]
    attempts: int
    total_delay: float
    all_errors: list[ErrorDetail] | None = None

    @property
    def success(self) -> bool:
        """Check if the operation eventually succeeded."""
        return self.result.is_success()

    def unwrap(self) -> T:
        """Get the value or raise an exception."""
        return self.result.unwrap()

    def unwrap_or(self, default: T) -> T:
        """Get the value or return default."""
        return self.result.unwrap_or(default)


def is_retryable_error(error: ErrorDetail, retryable_codes: set[str]) -> bool:
    """Check if an error is retryable based on its code.

    Args:
        error: The error to check
        retryable_codes: Set of error codes that are retryable

    Returns:
        True if the error should be retried
    """
    return error.code in retryable_codes


class RetryHandler:
    """Handles retry logic for operations that may fail transiently."""

    def __init__(self, config: RetryConfig | None = None):
        """Initialize retry handler.

        Args:
            config: Retry configuration, uses defaults if not provided
        """
        self.config = config or RetryConfig()

    def retry(
        self,
        operation: Callable[[], Result[T]],
        operation_name: str | None = None,
    ) -> RetryResult[T]:
        """Execute an operation with retry logic.

        Args:
            operation: Callable that returns a Result
            operation_name: Optional name for logging

        Returns:
            RetryResult containing the final result and metadata
        """
        error_collector = ErrorCollector() if self.config.collect_all_errors else None
        total_delay = 0.0
        # Ensure max_attempts is int
        max_attempts = cast("int", self.config.max_attempts)
        op_name = operation_name or operation.__name__

        for attempt in range(1, max_attempts + 1):
            if attempt > 1 and self.config.log_retries:
                logger.info("Retrying %s (attempt %s/%s)", op_name, attempt, max_attempts)

            # Execute the operation
            try:
                result = operation()
            except Exception as e:  # noqa: BLE001 - convert any exception into Failure for retry logic
                # Convert exception to Result
                result = Failure.from_exception(e)

            # Check if successful
            if result.is_success():
                return RetryResult(
                    result=result,
                    attempts=attempt,
                    total_delay=total_delay,
                    all_errors=error_collector.get_all() if error_collector else None,
                )

            # Handle failure
            errors = result.get_errors()

            # Collect errors if configured
            if error_collector:
                for error in errors:
                    error_collector.add_error(
                        code=error.code,
                        message=f"Attempt {attempt}: {error.message}",
                        context=error.context,
                        source=error.source,
                    )

            # Check if we should retry
            if attempt >= max_attempts:
                # No more retries
                if self.config.log_retries:
                    logger.warning(
                        "%s failed after %s attempts. Final error: %s",
                        op_name,
                        attempt,
                        errors[0].message if errors else "Unknown",
                    )
                break

            # Check if errors are retryable
            if self.config.strategy == RetryStrategy.CONDITIONAL:
                # Safe cast retryable_errors to non-nullable set
                retryable_errors = cast("set[str]", self.config.retryable_errors)
                retryable = any(is_retryable_error(error, retryable_errors) for error in errors)
                if not retryable:
                    if self.config.log_retries:
                        logger.debug(
                            "%s failed with non-retryable error: %s",
                            op_name,
                            errors[0].code if errors else "Unknown",
                        )
                    break

            # Calculate delay
            if self.config.strategy == RetryStrategy.BACKOFF and self.config.backoff:
                delay = self.config.backoff.get_delay(attempt)
                if self.config.log_retries:
                    logger.debug("Waiting %.2fs before retry", delay)
                time.sleep(delay)
                total_delay += delay

        # Return final result
        return RetryResult(
            result=result,
            attempts=attempt,
            total_delay=total_delay,
            all_errors=error_collector.get_all() if error_collector else None,
        )

    def retry_async(
        self,
        operation: Callable[[], Result[T]],
        operation_name: str | None = None,
    ) -> RetryResult[T]:
        """Execute an async operation with retry logic.

        Note: This is a placeholder for future async support.
        Currently just delegates to sync retry.

        Args:
            operation: Callable that returns a Result
            operation_name: Optional name for logging

        Returns:
            RetryResult containing the final result and metadata
        """
        # TODO: Implement proper async support when needed
        return self.retry(operation, operation_name)


# Convenience functions for common retry patterns


def retry_with_exponential_backoff(
    operation: Callable[[], Result[T]],
    max_attempts: int | None = None,
    base_delay: float = 1.0,
    operation_name: str | None = None,
) -> RetryResult[T]:
    """Retry an operation with exponential backoff.

    Args:
        operation: The operation to retry
        max_attempts: Maximum number of attempts. If not provided, uses config default from api.api_retry_count
        base_delay: Initial delay in seconds
        operation_name: Optional name for logging

    Returns:
        RetryResult with the final outcome
    """
    # Use config default if not provided
    max_attempts = cfg_or_param("api.api_retry_count", max_attempts)

    config = RetryConfig(
        max_attempts=max_attempts,
        strategy=RetryStrategy.BACKOFF,
        backoff=ExponentialBackoff(base_delay=base_delay),
    )
    handler = RetryHandler(config)
    return handler.retry(operation, operation_name)


def retry_on_specific_errors(
    operation: Callable[[], Result[T]],
    retryable_errors: set[str],
    max_attempts: int | None = None,
    operation_name: str | None = None,
) -> RetryResult[T]:
    """Retry an operation only for specific error codes.

    Args:
        operation: The operation to retry
        retryable_errors: Set of error codes that trigger retry
        max_attempts: Maximum number of attempts. If not provided, uses config default from api.api_retry_count
        operation_name: Optional name for logging

    Returns:
        RetryResult with the final outcome
    """
    # Use config default if not provided
    max_attempts = cfg_or_param("api.api_retry_count", max_attempts)

    config = RetryConfig(
        max_attempts=max_attempts,
        strategy=RetryStrategy.CONDITIONAL,
        retryable_errors=retryable_errors,
        backoff=ExponentialBackoff(),
    )
    handler = RetryHandler(config)
    return handler.retry(operation, operation_name)
