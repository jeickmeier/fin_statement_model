"""Registry system for managing I/O format handlers.

This module provides a generic `HandlerRegistry` class and specific, pre-configured
instances for managing `DataReader` and `DataWriter` classes. It allows for a
decoupled, extensible I/O system where new formats can be added without
modifying the core logic.

The key features are:
- `register_reader` and `register_writer` decorators for associating a handler
  class with a format identifier (e.g., 'csv').
- A mandatory Pydantic schema for each handler, ensuring that all configurations
  are validated before a handler is instantiated.
- `get_reader` and `get_writer` functions that look up a handler, validate the
  provided configuration against its schema, and return an initialized instance.
"""

from collections.abc import Callable
from enum import Enum
import logging
from typing import Any, Generic, TypeVar, cast

from pydantic import BaseModel, ValidationError

from fin_statement_model.io.core.base import DataReader, DataWriter
from fin_statement_model.io.exceptions import (
    FormatNotSupportedError,
    ReadError,
    WriteError,
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
        _schema_map: Internal dictionary mapping format types to Pydantic schema classes.
    """

    def __init__(self, handler_type: str):
        """Initialize the registry.

        Args:
            handler_type: Type of handlers ('reader' or 'writer') for error messages.
        """
        self._registry: dict[str, type[T]] = {}
        self._handler_type = handler_type
        self._schema_map: dict[str, type[BaseModel]] = {}

    def register(self, format_type: str, *, schema: type[BaseModel] | None = None) -> Callable[[type[T]], type[T]]:
        """Create a decorator to register a handler class for a format type.

        Args:
            format_type: The format identifier (e.g., 'excel', 'csv').
            schema: Optional Pydantic schema for the format.

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
                logger.debug("Re-registering %s format type '%s' to %s", self._handler_type, format_type, cls.__name__)
            else:
                logger.debug("Registering %s format type '%s' to %s", self._handler_type, format_type, cls.__name__)

            self._registry[format_type] = cls
            if schema is not None:
                self._schema_map[format_type] = schema
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
            raise FormatNotSupportedError(format_type=format_type, operation=f"{self._handler_type} operations")

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

    def unregister(self, format_type: str) -> type[T] | None:
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

    def get_schema(self, format_type: str) -> type[BaseModel] | None:
        """Return the Pydantic schema for a registered format type, if any."""
        return self._schema_map.get(format_type)


# ===== Registry Instances =====

# Create registry instances for readers and writers
_reader_registry = HandlerRegistry[DataReader]("reader")
_writer_registry = HandlerRegistry[DataWriter]("writer")


# ===== Registration Decorators =====


def register_reader(
    format_type: str,
    *,
    schema: type[BaseModel] | None = None,
) -> Callable[[type[DataReader]], type[DataReader]]:
    """Decorator to register a DataReader class for a specific format type.

    Args:
        format_type: The string identifier for the format (e.g., 'excel', 'csv').
        schema: Optional Pydantic schema class for configuration validation.

    Returns:
        A decorator function that registers the class and returns it unmodified.

    Raises:
        ValueError: If the format_type is already registered for a reader.
    """
    # Require schema at registration time (legacy schema-less removed)
    if schema is None:
        raise ValueError(f"Schema required for reader '{format_type}'; legacy schema-less mode removed.")
    return _reader_registry.register(format_type, schema=schema)


def register_writer(
    format_type: str,
    *,
    schema: type[BaseModel] | None = None,
) -> Callable[[type[DataWriter]], type[DataWriter]]:
    """Decorator to register a DataWriter class for a specific format type.

    Args:
        format_type: The string identifier for the format (e.g., 'excel', 'json').
        schema: Optional Pydantic schema class for configuration validation.

    Returns:
        A decorator function that registers the class and returns it unmodified.

    Raises:
        ValueError: If the format_type is already registered for a writer.
    """
    # Require schema at registration time (legacy schema-less removed)
    if schema is None:
        raise ValueError(f"Schema required for writer '{format_type}'; legacy schema-less mode removed.")
    return _writer_registry.register(format_type, schema=schema)


# ===== Generic Handler Function =====


def _get_handler(
    format_type: str,
    registry: HandlerRegistry[Any],
    handler_type: str,
    error_class: type[ReadError | WriteError],
    **kwargs: Any,
) -> DataReader | DataWriter:
    """Generic handler instantiation logic.

    This function encapsulates the common pattern for instantiating
    readers and writers, including configuration validation and error handling.

    Args:
        format_type: The format identifier (e.g., 'excel', 'csv').
        registry: The registry instance containing handler classes.
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

    # Determine Pydantic schema from registry
    schema = registry.get_schema(format_type)
    # If no schema is registered for this format, treat it as unsupported
    if schema is None:
        raise FormatNotSupportedError(
            format_type=format_type,
            operation=f"{handler_type} operations",
        )

    # Prepare error context based on handler type
    error_context = {}
    if handler_type == "read":
        error_context["source"] = kwargs.get("source")
        error_context["reader_type"] = format_type
    else:  # write
        error_context["target"] = kwargs.get("target")
        error_context["writer_type"] = format_type

    if "format_type" not in kwargs:
        kwargs = {**kwargs, "format_type": format_type}
    try:
        cfg = schema.model_validate(kwargs)
    except ValidationError as ve:
        raise error_class(
            message=f"Invalid {handler_type}er configuration",
            original_error=ve,
            **error_context,
        ) from ve

    # Instantiate handler with validated config
    try:
        return cast("DataReader | DataWriter", handler_class(cfg))
    except Exception as e:
        logger.exception(
            "Failed to instantiate %ser for format '%s' (%s)", handler_type, format_type, handler_class.__name__
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
    return cast(
        "DataReader",
        _get_handler(
            format_type=format_type,
            registry=_reader_registry,
            handler_type="read",
            error_class=ReadError,
            **kwargs,
        ),
    )


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
    return cast(
        "DataWriter",
        _get_handler(
            format_type=format_type,
            registry=_writer_registry,
            handler_type="write",
            error_class=WriteError,
            **kwargs,
        ),
    )


def list_readers() -> dict[str, type[DataReader]]:
    """Return a copy of the registered reader classes."""
    return _reader_registry.list_formats()


def list_writers() -> dict[str, type[DataWriter]]:
    """Return a copy of the registered writer classes."""
    return _writer_registry.list_formats()


__all__ = [
    "HandlerRegistry",
    "IOFormat",
    "get_reader",
    "get_writer",
    "list_readers",
    "list_writers",
    "register_reader",
    "register_writer",
]

# -----------------------------------------------------------------------------
# Enum of registered IO format keys (for static typing / IDE completion)
# -----------------------------------------------------------------------------


def _build_io_format_enum() -> "Enum":
    """Return an Enum mapping of currently registered reader/writer keys."""
    # Union of all known reader/writer keys (grabbed at import time after
    # all format modules executed their registration side-effects).
    keys = sorted(set(_reader_registry.list_formats().keys()).union(_writer_registry.list_formats().keys()))

    # Enum member names must be valid identifiers - use upper-snake.
    def _safe(name: str) -> str:
        return name.replace("-", "_").replace(" ", "_").upper()

    members = {_safe(k): k for k in keys}
    return Enum("IOFormat", members, type=str)


# Instantiate once so downstream imports can use.
IOFormat = _build_io_format_enum()
