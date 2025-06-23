"""Centralised logging (re)configuration helper.

This module provides a single, safe entry point for applying logging settings
from a `Config` object. It acts as a hook that the `ConfigStore` can call
whenever the configuration is loaded or updated.

This decouples the `ConfigStore` from the specific implementation details of the
main `logging_config` module, allowing either to evolve independently. Other
modules should not import this directly; they should rely on the `ConfigStore`
to trigger it automatically.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fin_statement_model import logging_config

if TYPE_CHECKING:
    from .models import Config

__all__ = [
    "apply_logging_config",
]


def apply_logging_config(cfg: Config) -> None:
    """Apply logging configuration settings contained in `cfg`.

    This function reads the `logging` section of the provided configuration
    object and passes the values to the central `logging_config.setup_logging`
    function to reconfigure the application's loggers.
    """
    logging_config.setup_logging(
        level=cfg.logging.level,
        format_string=cfg.logging.format,
        detailed=cfg.logging.detailed,
        log_file_path=(str(cfg.logging.log_file_path) if cfg.logging.log_file_path else None),
    )
