"""Configure centralized logging for the fin_statement_model library.

This module provides consistent logging configuration across the entire package.
It defines formatters, handlers, and logging levels for different components of
the library.

Features:
    - Centralized logger configuration for all submodules.
    - Support for console and rotating file handlers.
    - Customizable log format and log level via function arguments or environment variables.
    - NullHandler by default to avoid 'No handler' warnings if not configured.
    - Best practices for logging in the library.
    - Environment variables:
        * FSM_LOG_LEVEL: Set the default log level (e.g., 'DEBUG', 'INFO').
        * FSM_LOG_FORMAT: Set a custom log format string.

Example:
    >>> from fin_statement_model import logging_config
    >>> logging_config.setup_logging(level="INFO", detailed=True)
    >>> logger = logging_config.get_logger(__name__)
    >>> logger.info("Logging is configured!")
"""

import logging
import logging.handlers
import os
import sys

# Default format for log messages
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DETAILED_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s"

# Environment variable to control logging level
LOG_LEVEL_ENV = "FSM_LOG_LEVEL"
LOG_FORMAT_ENV = "FSM_LOG_FORMAT"


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name.

    Ensure the logger is namespaced under the fin_statement_model package.
    If `name` starts with '.', it will be prefixed with 'fin_statement_model'.

    Args:
        name: The name of the logger, typically __name__

    Returns:
        A configured logger instance.

    Example:
        >>> from fin_statement_model.logging_config import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.debug("Debug message")
    """
    if not name.startswith("fin_statement_model") and name.startswith("."):
        name = f"fin_statement_model{name}"
    return logging.getLogger(name)


def setup_logging(
    level: str | None = None,
    format_string: str | None = None,
    log_file_path: str | None = None,
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
        log_file_path: Optional file path to write logs to.
        detailed: If True, uses detailed format with file/line information.

    Returns:
        None

    Example:
        >>> from fin_statement_model import logging_config
        >>> logging_config.setup_logging(level="INFO", detailed=True)
        >>> logger = logging_config.get_logger(__name__)
        >>> logger.info("Logging is configured!")

    Advanced Example:
        >>> logging_config.setup_logging(
        ...     level="DEBUG",
        ...     format_string="%(asctime)s %(levelname)s %(message)s",
        ...     log_file_path="fin_model.log",
        ...     detailed=True,
        ... )
        >>> logger = logging_config.get_logger("fin_statement_model.core")
        >>> logger.debug("Advanced logging enabled!")
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
    if log_file_path:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Set specific log levels for noisy sub-modules if needed
    # For example, reduce verbosity of certain components during normal operation
    logging.getLogger("fin_statement_model.io.formats").setLevel(max(numeric_level, logging.INFO))
    logging.getLogger("fin_statement_model.core.graph.traverser").setLevel(max(numeric_level, logging.INFO))


def configure_library_logging() -> None:
    """Configure default logging for library usage.

    This is called automatically when the library is imported and sets up
    a NullHandler to prevent "no handler" warnings. Users should call
    setup_logging() to enable actual logging output.

    Returns:
        None

    Example:
        >>> from fin_statement_model import logging_config
        >>> logging_config.configure_library_logging()
        >>> # No output will be shown unless setup_logging() is called
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
# 4. Prefer ``logger.exception`` in except blocks to capture stack traces.
# 5. Guard expensive debug-only computations using ``logger.isEnabledFor`` checks.
