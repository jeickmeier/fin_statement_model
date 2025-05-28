"""Base registry class for managing handler registrations.

This module provides a generic registry implementation that can be used
for both readers and writers, reducing code duplication.
"""

import logging
from typing import TypeVar, Generic, Optional
from collections.abc import Callable

from fin_statement_model.io.exceptions import FormatNotSupportedError

logger = logging.getLogger(__name__)

# Type variable for the handler type (DataReader or DataWriter)
T = TypeVar("T")


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
