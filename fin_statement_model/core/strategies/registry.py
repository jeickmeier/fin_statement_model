"""Registry for calculation strategies in the Financial Statement Model.

This module provides a central registry for discovering and accessing different
calculation strategy classes. Strategies can be registered using their class
object and later retrieved by their class name.
"""

from __future__ import annotations

# Use lowercase built-in types
from typing import ClassVar  # Keep Type for now
import logging

from .strategy import Strategy

# Configure logging
logger = logging.getLogger(__name__)


class Registry:
    """A central registry for managing and accessing calculation strategies.

    This class uses class methods to provide a global registry. Strategies
    are stored in a dictionary mapping their class name (string) to the
    strategy class itself.

    Attributes:
        _strategies: A dictionary holding the registered strategy classes.
                     Keys are strategy class names (str), values are strategy
                     types (Type[Strategy]).
    """

    _strategies: ClassVar[dict[str, type[Strategy]]] = {}  # Use dict, type

    @classmethod
    def register(cls, strategy: type[Strategy]) -> None:
        """Register a strategy class with the registry.

        If a strategy with the same name is already registered, it will be
        overwritten.

        Args:
            strategy: The calculation strategy class (Type[Strategy]) to register.
                      The class's __name__ attribute will be used as the key.
        """
        if not issubclass(strategy, Strategy):
            raise TypeError(f"Can only register subclasses of Strategy, not {strategy}")
        cls._strategies[strategy.__name__] = strategy
        logger.debug(f"Registered strategy: {strategy.__name__}")

    @classmethod
    def get(cls, name: str) -> type[Strategy]:
        """Retrieve a strategy class from the registry by its name.

        Args:
            name: The string name of the strategy class to retrieve.

        Returns:
            The strategy class (Type[Strategy]) associated with the given name.

        Raises:
            KeyError: If no strategy with the specified name is found in the
                      registry.
        """
        # Debug print including id of the dictionary
        if name not in cls._strategies:
            logger.error(f"Attempted to access unregistered strategy: {name}")
            raise KeyError(f"Strategy '{name}' not found in registry.")
        return cls._strategies[name]

    @classmethod
    def list(cls) -> dict[str, type[Strategy]]:  # Use dict, type
        """List all registered strategy classes.

        Returns:
            A dictionary containing all registered strategy names (str) and their
            corresponding strategy classes (Type[Strategy]). Returns a copy
            to prevent modification of the internal registry.
        """
        return cls._strategies.copy()
