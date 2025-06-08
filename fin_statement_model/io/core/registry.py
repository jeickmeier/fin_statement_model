"""Registry system for managing IO format handlers.

This module provides a generic registry implementation and specific registries
for readers and writers, along with registration decorators and access functions.

Internal registry dictionaries `_readers` and `_writers` are no longer exposed;
use `list_readers()` and `list_writers()` for a readonly view of registered handlers.
"""

import logging
from typing import TypeVar, Generic, Optional, Any, Union, cast
from collections.abc import Callable

from pydantic import ValidationError

from fin_statement_model.io.core.base import DataReader, DataWriter
from fin_statement_model.io.exceptions import (
    FormatNotSupportedError,
    ReadError,
    WriteError,
)
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

# Type variable for the handler type (DataReader or DataWriter)
T = TypeVar("T")


# ===== Generic Registry Implementation =====


class HandlerRegistry(Generic[T]):
    """Generic registry for managing format handlers (readers or writers).

    This class provides a reusable registry pattern for registering and
    retrieving handler classes by format type.

    Attributes:
        _registry: Internal dictionary mapping format types to handler classes.
        _handler_type: String describing the handler type ('reader' or 'writer').
    """

    def __init__(self, handler_type: str):
        """Initialize the registry.

        Args:
            handler_type: Type of handlers ('reader' or 'writer') for error messages.
        """
        self._registry: dict[str, type[T]] = {}
        self._handler_type = handler_type

    def register(self, format_type: str) -> Callable[[type[T]], type[T]]:
        """Create a decorator to register a handler class for a format type.

        Args:
            format_type: The format identifier (e.g., 'excel', 'csv').

        Returns:
            A decorator function that registers the class.

        Raises:
            ValueError: If the format is already registered to a different class.
        """

        def decorator(cls: type[T]) -> type[T]:
            if format_type in self._registry:
                # Allow re-registration of the same class (idempotent)
                if self._registry[format_type] is not cls:
                    raise ValueError(
                        f"{self._handler_type.capitalize()} format type '{format_type}' "
                        f"already registered to {self._registry[format_type]}."
                    )
                logger.debug(
                    f"Re-registering {self._handler_type} format type '{format_type}' "
                    f"to {cls.__name__}"
                )
            else:
                logger.debug(
                    f"Registering {self._handler_type} format type '{format_type}' "
                    f"to {cls.__name__}"
                )

            self._registry[format_type] = cls
            return cls

        return decorator

    def get(self, format_type: str) -> type[T]:
        """Get the registered handler class for a format type.

        Args:
            format_type: The format identifier.

        Returns:
            The registered handler class.

        Raises:
            FormatNotSupportedError: If no handler is registered for the format.
        """
        if format_type not in self._registry:
            raise FormatNotSupportedError(
                format_type=format_type, operation=f"{self._handler_type} operations"
            )

        return self._registry[format_type]

    def list_formats(self) -> dict[str, type[T]]:
        """Return a copy of all registered format handlers.

        Returns:
            Dictionary mapping format types to handler classes.
        """
        return self._registry.copy()

    def is_registered(self, format_type: str) -> bool:
        """Check if a format type is registered.

        Args:
            format_type: The format identifier to check.

        Returns:
            True if the format is registered, False otherwise.
        """
        return format_type in self._registry

    def unregister(self, format_type: str) -> Optional[type[T]]:
        """Remove a format handler from the registry.

        This method is primarily useful for testing.

        Args:
            format_type: The format identifier to remove.

        Returns:
            The removed handler class, or None if not found.
        """
        return self._registry.pop(format_type, None)

    def clear(self) -> None:
        """Clear all registered handlers.

        This method is primarily useful for testing.
        """
        self._registry.clear()

    def __contains__(self, format_type: str) -> bool:
        """Check if a format type is registered using 'in' operator.

        Args:
            format_type: The format identifier to check.

        Returns:
            True if the format is registered, False otherwise.
        """
        return format_type in self._registry

    def __len__(self) -> int:
        """Return the number of registered formats.

        Returns:
            Number of registered format handlers.
        """
        return len(self._registry)


# ===== Registry Instances =====

# Create registry instances for readers and writers
_reader_registry = HandlerRegistry[DataReader]("reader")
_writer_registry = HandlerRegistry[DataWriter]("writer")

# Schema mappings for configuration validation
_READER_SCHEMA_MAP = {
    "csv": CsvReaderConfig,
    "excel": ExcelReaderConfig,
    "fmp": FmpReaderConfig,
    "dataframe": DataFrameReaderConfig,
    "dict": DictReaderConfig,
}

_WRITER_SCHEMA_MAP = {
    "excel": ExcelWriterConfig,
    "dataframe": DataFrameWriterConfig,
    "dict": DictWriterConfig,
    "markdown": MarkdownWriterConfig,
}


# ===== Registration Decorators =====


def register_reader(format_type: str) -> Callable[[type[DataReader]], type[DataReader]]:
    """Decorator to register a DataReader class for a specific format type.

    Args:
        format_type: The string identifier for the format (e.g., 'excel', 'csv').

    Returns:
        A decorator function that registers the class and returns it unmodified.

    Raises:
        ValueError: If the format_type is already registered for a reader.
    """
    return _reader_registry.register(format_type)


def register_writer(format_type: str) -> Callable[[type[DataWriter]], type[DataWriter]]:
    """Decorator to register a DataWriter class for a specific format type.

    Args:
        format_type: The string identifier for the format (e.g., 'excel', 'json').

    Returns:
        A decorator function that registers the class and returns it unmodified.

    Raises:
        ValueError: If the format_type is already registered for a writer.
    """
    return _writer_registry.register(format_type)


# ===== Generic Handler Function =====


def _get_handler(
    format_type: str,
    registry: HandlerRegistry[Any],
    schema_map: dict[str, Any],
    handler_type: str,
    error_class: type[Union[ReadError, WriteError]],
    **kwargs: Any,
) -> Union[DataReader, DataWriter]:
    """Generic handler instantiation logic.

    This function encapsulates the common pattern for instantiating
    readers and writers, including configuration validation and error handling.

    Args:
        format_type: The format identifier (e.g., 'excel', 'csv').
        registry: The registry instance containing handler classes.
        schema_map: Mapping of format types to Pydantic config schemas.
        handler_type: Either 'read' or 'write' for error messages.
        error_class: Either ReadError or WriteError class.
        **kwargs: Configuration parameters for the handler.

    Returns:
        An initialized handler instance.

    Raises:
        FormatNotSupportedError: If format_type is not in registry.
        ReadError/WriteError: If configuration validation or instantiation fails.
    """
    # Get handler class from registry (may raise FormatNotSupportedError)
    handler_class = registry.get(format_type)

    schema = schema_map.get(format_type)

    # Prepare error context based on handler type
    error_context = {}
    if handler_type == "read":
        error_context["source"] = kwargs.get("source")
        error_context["reader_type"] = format_type
    else:  # write
        error_context["target"] = kwargs.get("target")
        error_context["writer_type"] = format_type

    if schema:
        # Validate configuration using Pydantic schema
        try:
            cfg = schema.model_validate({**kwargs, "format_type": format_type})
        except ValidationError as ve:
            raise error_class(
                message=f"Invalid {handler_type}er configuration",
                original_error=ve,
                **error_context,
            ) from ve

        # Instantiate handler with validated config
        try:
            return cast(Union[DataReader, DataWriter], handler_class(cfg))
        except Exception as e:
            logger.error(
                f"Failed to instantiate {handler_type}er for format '{format_type}' "
                f"({handler_class.__name__}): {e}",
                exc_info=True,
            )
            raise error_class(
                message=f"Failed to initialize {handler_type}er",
                original_error=e,
                **error_context,
            ) from e

    # Fallback for handlers without config schema (legacy support)
    try:
        return cast(Union[DataReader, DataWriter], handler_class(**kwargs))
    except Exception as e:
        logger.error(
            f"Failed to instantiate {handler_type}er for format '{format_type}' "
            f"({handler_class.__name__}): {e}",
            exc_info=True,
        )
        raise error_class(
            message=f"Failed to initialize {handler_type}er",
            original_error=e,
            **error_context,
        ) from e


# ===== Registry Access Functions =====


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
    return cast(DataReader, _get_handler(
        format_type=format_type,
        registry=_reader_registry,
        schema_map=_READER_SCHEMA_MAP,
        handler_type="read",
        error_class=ReadError,
        **kwargs,
    ))


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
    return cast(DataWriter, _get_handler(
        format_type=format_type,
        registry=_writer_registry,
        schema_map=_WRITER_SCHEMA_MAP,
        handler_type="write",
        error_class=WriteError,
        **kwargs,
    ))


def list_readers() -> dict[str, type[DataReader]]:
    """Return a copy of the registered reader classes."""
    return _reader_registry.list_formats()


def list_writers() -> dict[str, type[DataWriter]]:
    """Return a copy of the registered writer classes."""
    return _writer_registry.list_formats()


__all__ = [
    "HandlerRegistry",
    "get_reader",
    "get_writer",
    "list_readers",
    "list_writers",
    "register_reader",
    "register_writer",
]
