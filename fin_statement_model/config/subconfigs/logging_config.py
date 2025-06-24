"""LoggingConfig sub-model.

Separated from the original monolithic `fin_statement_model.config.models`
module for better maintainability.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["LoggingConfig"]


class LoggingConfig(BaseModel):
    """Settings for library logging.

    Attributes:
        level (Literal): Default logging level ('DEBUG', 'INFO', 'WARNING',
            'ERROR', or 'CRITICAL').
        format (str): Log message format string.
        detailed (bool): Enable detailed logging with file and line numbers.
        log_file_path (Optional[Path]): Path for rotating log files; ``None``
            disables file logging.

    Example:
        >>> LoggingConfig(level="DEBUG").level
        'DEBUG'
    """

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        "WARNING",
        description="Default logging level for the library",
    )
    format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format string",
    )
    detailed: bool = Field(False, description="Enable detailed logging with file and line numbers")
    log_file_path: Path | None = Field(
        None,
        description=(
            "If provided, logs are written to this path (rotating handler). If None, file logging is disabled."
        ),
    )

    model_config = ConfigDict(extra="forbid")
