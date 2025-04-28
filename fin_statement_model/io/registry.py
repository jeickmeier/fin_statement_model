"""Registry for readers and writers."""

import logging
from typing import Any, TypeVar
from collections.abc import Callable

from .base import DataReader, DataWriter
from .exceptions import FormatNotSupportedError, ReadError, WriteError
from pydantic import ValidationError
from fin_statement_model.io.config.models import (
    CsvReaderConfig,
    ExcelReaderConfig,
    FmpReaderConfig,
    DataFrameReaderConfig,
    DictReaderConfig,
    ExcelWriterConfig,
    DataFrameWriterConfig,
    DictWriterConfig,
    MarkdownWriterConfig,
)

logger = logging.getLogger(__name__)

# --- Registry Dicts and Decorators ---

# Type variables for generic registration decorators
R = TypeVar("R", bound=DataReader)
W = TypeVar("W", bound=DataWriter)

# Internal registries
_readers: dict[str, type[DataReader]] = {}
_writers: dict[str, type[DataWriter]] = {}


def register_reader(format_type: str) -> Callable[[type[R]], type[R]]:
    """Decorator to register a DataReader class for a specific format type.

    Args:
        format_type: The string identifier for the format (e.g., 'excel', 'csv').

    Returns:
        A decorator function that registers the class and returns it unmodified.

    Raises:
        ValueError: If the format_type is already registered for a reader.
    """

    def decorator(cls: type[R]) -> type[R]:
        if format_type in _readers:
            # Allow re-registration if it's the exact same class (e.g., during reload)
            if _readers[format_type] is not cls:
                raise ValueError(
                    f"Reader format type '{format_type}' already registered to {_readers[format_type]}."
                )
            # If same class, just log and allow (idempotent registration)
            logger.debug(f"Re-registering reader format type '{format_type}' to {cls.__name__}")
        else:
            logger.debug(f"Registering reader format type '{format_type}' to {cls.__name__}")
        _readers[format_type] = cls
        return cls

    return decorator


def register_writer(format_type: str) -> Callable[[type[W]], type[W]]:
    """Decorator to register a DataWriter class for a specific format type.

    Args:
        format_type: The string identifier for the format (e.g., 'excel', 'json').

    Returns:
        A decorator function that registers the class and returns it unmodified.

    Raises:
        ValueError: If the format_type is already registered for a writer.
    """

    def decorator(cls: type[W]) -> type[W]:
        if format_type in _writers:
            # Allow re-registration if it's the exact same class
            if _writers[format_type] is not cls:
                raise ValueError(
                    f"Writer format type '{format_type}' already registered to {_writers[format_type]}."
                )
            logger.debug(f"Re-registering writer format type '{format_type}' to {cls.__name__}")
        else:
            logger.debug(f"Registering writer format type '{format_type}' to {cls.__name__}")
        _writers[format_type] = cls
        return cls

    return decorator


# --- Registry Access Functions ---


def get_reader(format_type: str, **kwargs: Any) -> DataReader:
    """Get an instance of the registered DataReader for the given format type.

    Args:
        format_type: The string identifier for the format.
        **kwargs: Keyword arguments to pass to the reader's constructor.

    Returns:
        An initialized DataReader instance.

    Raises:
        FormatNotSupportedError: If no reader is registered for the format type.
        ReadError: If validation fails for known reader types.
    """
    if format_type not in _readers:
        raise FormatNotSupportedError(format_type=format_type, operation="read")

    reader_class = _readers[format_type]
    # Validate config for known reader types
    schema_map = {
        "csv": CsvReaderConfig,
        "excel": ExcelReaderConfig,
        "fmp": FmpReaderConfig,
        "dataframe": DataFrameReaderConfig,
        "dict": DictReaderConfig,
    }
    schema = schema_map.get(format_type)
    if schema:
        try:
            cfg = schema.model_validate({**kwargs, "format_type": format_type})
        except ValidationError as ve:
            # Map other pydantic errors to ReadError
            raise ReadError(
                message="Invalid reader configuration",
                source=kwargs.get("source"),
                reader_type=format_type,
                original_error=ve,
            ) from ve
        # Instantiate reader with config object
        try:
            return reader_class(cfg)
        except Exception as e:
            logger.error(
                f"Failed to instantiate reader for format '{format_type}' ({reader_class.__name__}): {e}",
                exc_info=True,
            )
            raise ReadError(
                message="Failed to initialize reader",
                source=kwargs.get("source"),
                reader_type=format_type,
                original_error=e,
            ) from e
    # Fallback for legacy readers without config schema
    try:
        return reader_class(**kwargs)
    except Exception as e:
        logger.error(
            f"Failed to instantiate reader for format '{format_type}' ({reader_class.__name__}): {e}",
            exc_info=True,
        )
        raise ReadError(
            message="Failed to initialize reader",
            source=kwargs.get("source"),
            reader_type=format_type,
            original_error=e,
        ) from e


def get_writer(format_type: str, **kwargs: Any) -> DataWriter:
    """Get an instance of the registered DataWriter for the given format type.

    Args:
        format_type: The string identifier for the format.
        **kwargs: Keyword arguments to pass to the writer's constructor.

    Returns:
        An initialized DataWriter instance.

    Raises:
        FormatNotSupportedError: If no writer is registered for the format type.
        WriteError: If validation fails for known writer types.
    """
    if format_type not in _writers:
        raise FormatNotSupportedError(format_type=format_type, operation="write")

    writer_class = _writers[format_type]
    # Map writer types to their config models
    writer_schema_map = {
        "excel": ExcelWriterConfig,
        "dataframe": DataFrameWriterConfig,
        "dict": DictWriterConfig,
        "markdown": MarkdownWriterConfig,
    }

    schema_cls = writer_schema_map.get(format_type)

    if schema_cls:
        try:
            cfg = schema_cls.model_validate({**kwargs, "format_type": format_type})
        except ValidationError as ve:
            raise WriteError(
                message="Invalid writer configuration",
                target=kwargs.get("target"),
                writer_type=format_type,
                original_error=ve,
            ) from ve
        try:
            return writer_class(cfg)
        except Exception as e:
            logger.error(
                f"Failed to instantiate writer for format '{format_type}': {e}",
                exc_info=True,
            )
            raise WriteError(
                message="Failed to initialize writer",
                target=kwargs.get("target"),
                writer_type=format_type,
                original_error=e,
            ) from e
    # Fallback if no schema defined
    try:
        return writer_class(**kwargs)
    except Exception as e:
        logger.error(
            f"Failed to instantiate writer for format '{format_type}': {e}",
            exc_info=True,
        )
        raise WriteError(
            message="Failed to initialize writer",
            target=kwargs.get("target"),
            writer_type=format_type,
            original_error=e,
        ) from e


def list_readers() -> dict[str, type[DataReader]]:
    """Return a copy of the registered reader classes."""
    return _readers.copy()


def list_writers() -> dict[str, type[DataWriter]]:
    """Return a copy of the registered writer classes."""
    return _writers.copy()


__all__ = [
    "get_reader",
    "get_writer",
    "list_readers",
    "list_writers",
    "register_reader",
    "register_writer",
]
