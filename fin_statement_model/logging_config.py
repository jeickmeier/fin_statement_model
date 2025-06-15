"""Deprecated shim – forwards to :pymod:`fin_statement_model.core.logging`.

This module used to host the full logging implementation.  The functionality
has been consolidated in :pymod:`fin_statement_model.core.logging` to avoid
code duplication and to respect the package's layer boundaries.  Importing
from ``fin_statement_model.logging_config`` will continue to work *for now* but
raises a :class:`DeprecationWarning`.
"""

from __future__ import annotations

import warnings

from fin_statement_model.core import logging as _core_logging

warnings.warn(
    (
        "`fin_statement_model.logging_config` is deprecated. "
        "Import `fin_statement_model.core.logging` instead."
    ),
    DeprecationWarning,
    stacklevel=2,
)

# Re-export public helpers ---------------------------------------------------

get_logger = _core_logging.get_logger
setup_logging = _core_logging.setup_logging

__all__ = ["get_logger", "setup_logging"]
