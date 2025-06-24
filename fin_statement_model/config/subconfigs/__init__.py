"""Sub-config models for fin_statement_model.config.

This subpackage splits each Pydantic model into its own module to keep
concerns isolated and files manageable.  All public classes are
re-exported here to preserve the previous flat import surface, so users
can either do::

    from fin_statement_model.config.subconfigs import LoggingConfig

or continue to import via the aggregated
`fin_statement_model.config.models` module which now forwards to these
classes.
"""

from __future__ import annotations

from .api_config import APIConfig
from .display_config import DisplayConfig, DisplayFlags
from .forecasting_config import ForecastingConfig
from .io_config import IOConfig
from .logging_config import LoggingConfig
from .metrics_config import MetricsConfig
from .preprocessing_config import PreprocessingConfig
from .statements_config import StatementsConfig
from .validation_config import ValidationConfig

# Re-export into module namespace.

globals().update({
    "APIConfig": APIConfig,
    "DisplayConfig": DisplayConfig,
    "DisplayFlags": DisplayFlags,
    "ForecastingConfig": ForecastingConfig,
    "IOConfig": IOConfig,
    "LoggingConfig": LoggingConfig,
    "MetricsConfig": MetricsConfig,
    "PreprocessingConfig": PreprocessingConfig,
    "StatementsConfig": StatementsConfig,
    "ValidationConfig": ValidationConfig,
})

__all__: list[str] = [
    "APIConfig",
    "DisplayConfig",
    "DisplayFlags",
    "ForecastingConfig",
    "IOConfig",
    "LoggingConfig",
    "MetricsConfig",
    "PreprocessingConfig",
    "StatementsConfig",
    "ValidationConfig",
]
