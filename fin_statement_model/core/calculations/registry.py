"""Registry for calculation classes in the Financial Statement Model.

This module provides a central registry for discovering and accessing different
calculation classes. Calculations can be registered using their class
object and later retrieved by their class name.

Examples:
    >>> from fin_statement_model.core.calculations.registry import Registry
    >>> from fin_statement_model.core.calculations import AdditionCalculation
    >>> Registry.register(AdditionCalculation)
    >>> Registry.get("AdditionCalculation") is AdditionCalculation
    >>> list(Registry.list().keys())
    ['AdditionCalculation', 'SubtractionCalculation', 'MultiplicationCalculation', ...]
"""

# Use lowercase built-in types
from typing import ClassVar  # Keep Type for now
import logging

from .calculation import Calculation

# Configure logging
logger = logging.getLogger(__name__)


class Registry:
    """A central registry for managing and accessing calculation classes.

    This class uses class methods to provide a global registry. Calculations
    are stored in a dictionary mapping their class name (string) to the
    calculation class itself.

    Attributes:
        _strategies: A dictionary holding the registered calculation classes.
                     Keys are calculation class names (str), values are calculation
                     types (Type[Calculation]).
    """

    _strategies: ClassVar[dict[str, type[Calculation]]] = {}  # Use dict, type

    @classmethod
    def register(cls, calculation: type[Calculation]) -> None:
        """Register a calculation class with the registry.

        If a calculation with the same name is already registered, it will be
        overwritten.

        Args:
            calculation: The calculation class (Type[Calculation]) to register.
                         The class's __name__ attribute will be used as the key.
        """
        if not issubclass(calculation, Calculation):
            raise TypeError(
                f"Can only register subclasses of Calculation, not {calculation}"
            )
        cls._strategies[calculation.__name__] = calculation
        logger.debug(f"Registered calculation: {calculation.__name__}")

    @classmethod
    def get(cls, name: str) -> type[Calculation]:
        """Retrieve a calculation class from the registry by its name.

        Args:
            name: The string name of the calculation class to retrieve.

        Returns:
            The calculation class (Type[Calculation]) associated with the given name.

        Raises:
            KeyError: If no calculation with the specified name is found in the
                      registry.
        """
        # Debug print including id of the dictionary
        if name not in cls._strategies:
            logger.error(f"Attempted to access unregistered calculation: {name}")
            raise KeyError(f"Calculation '{name}' not found in registry.")
        return cls._strategies[name]

    @classmethod
    def list(cls) -> dict[str, type[Calculation]]:  # Use dict, type
        """List all registered calculation classes.

        Returns:
            A dictionary containing all registered calculation names (str) and their
            corresponding calculation classes (Type[Calculation]). Returns a copy
            to prevent modification of the internal registry.
        """
        return cls._strategies.copy()
