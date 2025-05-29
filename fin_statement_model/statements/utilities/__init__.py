"""Cross-cutting utilities for the statements package.

This package provides reusable components:
- Result types for functional error handling
- Retry mechanisms for transient failures
- Common error codes and handling patterns
"""

from .result_types import (
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
from .retry_handler import (
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

__all__ = [
    "BackoffStrategy",
    "ConstantBackoff",
    "ErrorCollector",
    "ErrorDetail",
    "ErrorSeverity",
    "ExponentialBackoff",
    "Failure",
    "LinearBackoff",
    "OperationResult",
    "ProcessingResult",
    # Result Types
    "Result",
    "RetryConfig",
    # Retry Handler
    "RetryHandler",
    "RetryResult",
    "RetryStrategy",
    "Success",
    "ValidationResult",
    "combine_results",
    "retry_on_specific_errors",
    "retry_with_exponential_backoff",
]
