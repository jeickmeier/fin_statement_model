"""Centralized logging configuration for the fin_statement_model library.

This module provides consistent logging configuration across the entire package.
It sets up appropriate formatters, handlers, and logging levels for different
components of the library.
"""

import logging
import logging.handlers
import os
import sys
from typing import Optional


# Default format for log messages
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DETAILED_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s"

# Environment variable to control logging level
LOG_LEVEL_ENV = "FSM_LOG_LEVEL"
LOG_FORMAT_ENV = "FSM_LOG_FORMAT"


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name.

    This is a convenience function that ensures all loggers are properly
    namespaced under the fin_statement_model package.

    Args:
        name: The name of the logger, typically __name__

    Returns:
        A configured logger instance
    """
    if not name.startswith("fin_statement_model") and name.startswith("."):
        name = f"fin_statement_model{name}"
    return logging.getLogger(name)


def setup_logging(
    level: Optional[str] = None,
    format_string: Optional[str] = None,
    log_to_file: Optional[str] = None,
    detailed: bool = False,
) -> None:
    """Configure logging for the fin_statement_model library.

    This function should be called once at application startup to configure
    logging behavior. If not called, the library will use a NullHandler to
    avoid "no handler" warnings.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               If None, uses FSM_LOG_LEVEL env var or defaults to WARNING.
        format_string: Custom format string for log messages.
                      If None, uses FSM_LOG_FORMAT env var or default format.
        log_to_file: Optional file path to write logs to.
        detailed: If True, uses detailed format with file/line information.

    Example:
        >>> from fin_statement_model import logging_config
        >>> logging_config.setup_logging(level="INFO", detailed=True)
    """
    # Determine log level
    if level is None:
        level = os.environ.get(LOG_LEVEL_ENV, "WARNING")

    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.WARNING)

    # Determine format
    if format_string is None:
        format_string = os.environ.get(LOG_FORMAT_ENV)
        if format_string is None:
            format_string = DETAILED_FORMAT if detailed else DEFAULT_FORMAT

    # Get the root logger for fin_statement_model
    root_logger = logging.getLogger("fin_statement_model")
    root_logger.setLevel(numeric_level)

    # Remove any existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(format_string)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Optional file handler
    if log_to_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_to_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Set specific log levels for noisy sub-modules if needed
    # For example, reduce verbosity of certain components during normal operation
    logging.getLogger("fin_statement_model.io.formats").setLevel(max(numeric_level, logging.INFO))
    logging.getLogger("fin_statement_model.core.graph.traverser").setLevel(
        max(numeric_level, logging.INFO)
    )


def configure_library_logging() -> None:
    """Configure default logging for library usage.

    This is called automatically when the library is imported and sets up
    a NullHandler to prevent "no handler" warnings. Users should call
    setup_logging() to enable actual logging output.
    """
    # Attach a NullHandler to the base fin_statement_model logger so that
    # all child loggers inherit it and avoid 'No handler' warnings by default.
    base_logger = logging.getLogger("fin_statement_model")

    # Only add NullHandler if no handlers exist
    if not base_logger.handlers:
        base_logger.addHandler(logging.NullHandler())

    # Prevent propagation to root logger by default
    base_logger.propagate = False


# Configure library logging on import
configure_library_logging()


# Logging best practices for fin_statement_model:
#
# 1. Always use logger = logging.getLogger(__name__) in modules
# 2. Use appropriate log levels:
#    - DEBUG: Detailed information for diagnosing problems
#    - INFO: General informational messages
#    - WARNING: Something unexpected happened but the app is still working
#    - ERROR: A serious problem occurred, function cannot proceed
#    - CRITICAL: A very serious error occurred, program may be unable to continue
#
# 3. Include context in log messages:
#    - Good: logger.info(f"Loaded {count} metrics from {filepath}")
#    - Bad: logger.info("Metrics loaded")
#
# 4. Use logger.exception() in except blocks to capture stack traces:
#    try:
#        risky_operation()
#    except Exception:
#        logger.exception("Failed to perform risky operation")
#
# 5. For performance-sensitive code, check log level before expensive operations:
#    if logger.isEnabledFor(logging.DEBUG):
#        logger.debug(f"Expensive debug info: {expensive_function()}")
