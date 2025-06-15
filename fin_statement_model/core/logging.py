"""Centralised logging utilities for ``fin_statement_model``.

This module exposes two main helpers:

1. ``get_logger(name: str)`` – a thin wrapper around :pyfunc:`logging.getLogger` that
   ensures the logger is namespaced under the ``fin_statement_model`` top-level
   package.  Use this instead of calling the stdlib directly so that end users
   can configure all library loggers in a single place.
2. ``setup_logging(**cfg)`` – configures the log level, format, and optional file
   handler based on *either* explicit keyword arguments *or* environment
   variables.

Environment variable overrides
------------------------------
The behaviour of ``setup_logging`` can be influenced via the following
variables (all optional):

* ``FSM_LOG_LEVEL``  – overrides the log level (e.g. ``DEBUG``).  Ignored if the
  caller explicitly supplies the ``level`` argument.
* ``FSM_LOG_FORMAT`` – overrides the log message format string.  Ignored if the
  caller explicitly supplies the ``format_string`` argument.

If neither explicit arguments nor environment variables are supplied, sensible
library defaults are used (see ``DEFAULT_FORMAT``).

The function is *idempotent*: calling it multiple times merely replaces the
handlers on the ``fin_statement_model`` root logger, so it is safe to call more
than once, although the recommended pattern is to invoke it exactly once during
package import (see ``fin_statement_model.__init__``).
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_FORMAT = "%(" "asctime)s - %(name)s - %(levelname)s - %(message)s"
DETAILED_FORMAT = (
    "%("
    "asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s"
)

_LOG_LEVEL_ENV = "FSM_LOG_LEVEL"
_LOG_FORMAT_ENV = "FSM_LOG_FORMAT"

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_logger(name: str) -> logging.Logger:
    """Return a library-namespaced :class:`logging.Logger` instance.

    Args:
        name: Typically ``__name__`` from the calling module.

    Returns:
        A logger whose *effective* name is guaranteed to start with
        ``fin_statement_model``.
    """
    if not name.startswith("fin_statement_model") and name.startswith("."):
        name = f"fin_statement_model{name}"
    return logging.getLogger(name)


def setup_logging(
    *,
    level: Optional[str] = None,
    format_string: Optional[str] = None,
    log_file_path: Optional[str] = None,
    detailed: bool = False,
) -> None:
    """Configure logging for *all* ``fin_statement_model`` loggers.

    The function clears any existing handlers on the ``fin_statement_model``
    root logger before attaching fresh ones.  This guarantees that repeated
    calls do not accumulate duplicate handlers.

    Args:
        level: Log level as a string (``DEBUG``, ``INFO`` …).  If *None*, the
            value of ``FSM_LOG_LEVEL`` is consulted; if that is unset the level
            defaults to ``WARNING``.
        format_string: Custom log format.  If *None*, the value of
            ``FSM_LOG_FORMAT`` is consulted; if that too is unset a default is
            chosen (detailed vs. simple depending on *detailed*).
        log_file_path: Optional path to an additional *rotating* file handler.
        detailed: Toggle between the simple and the *DETAILED_FORMAT*.
    """

    # ------------------------------------------------------------------
    # Resolve configuration
    # ------------------------------------------------------------------

    # Ensure ``resolved_level`` is always a concrete string for static typing
    if level is not None:
        resolved_level: str = level
    else:
        resolved_level = os.environ.get(_LOG_LEVEL_ENV, "WARNING")

    numeric_level = getattr(logging, resolved_level.upper(), logging.WARNING)

    resolved_fmt = format_string or os.environ.get(_LOG_FORMAT_ENV)
    if resolved_fmt is None:
        resolved_fmt = DETAILED_FORMAT if detailed else DEFAULT_FORMAT

    # ------------------------------------------------------------------
    # Configure root logger for this library
    # ------------------------------------------------------------------

    root_logger = logging.getLogger("fin_statement_model")
    root_logger.setLevel(numeric_level)

    # Clear out *all* existing handlers to avoid duplication when the function
    # is called more than once (it is idempotent by design).
    root_logger.handlers.clear()

    formatter = logging.Formatter(resolved_fmt)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Optional rotating file handler
    if log_file_path:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Reduce noise from ultra-verbose internal sub-modules unless the user
    # explicitly requested an even lower level.
    logging.getLogger("fin_statement_model.io.formats").setLevel(
        max(numeric_level, logging.INFO)
    )
    logging.getLogger("fin_statement_model.core.graph.traverser").setLevel(
        max(numeric_level, logging.INFO)
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _attach_null_handler() -> None:
    """Attach :class:`logging.NullHandler` so import-time logging is quiet."""
    base_logger = logging.getLogger("fin_statement_model")
    if not base_logger.handlers:
        base_logger.addHandler(logging.NullHandler())
    base_logger.propagate = False


# Execute immediately so that importing any sub-module will **never** emit the
# dreaded "No handlers could be found for logger X" warning.  Users can later
# replace the handler set via :pyfunc:`setup_logging`.
_attach_null_handler()

__all__ = ["get_logger", "setup_logging"]
