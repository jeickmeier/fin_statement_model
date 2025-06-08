"""Registry for managing loaded and validated financial statement structures.

This module provides the `StatementRegistry` class, which acts as a central
store for `StatementStructure` objects after they have been loaded from
configurations and built. It ensures uniqueness of statement IDs and provides
methods for retrieving registered statements.
"""

import logging
from typing import Optional

# Assuming StatementStructure is defined here or imported appropriately
# We might need to adjust this import based on the actual location
try:
    from .structure import StatementStructure
except ImportError:
    # Handle cases where structure might be in a different sub-package later if needed
    # For now, assume it's available via relative import
    from fin_statement_model.statements.structure import StatementStructure

from .errors import StatementError  # Assuming StatementError is in statements/errors.py

logger = logging.getLogger(__name__)

__all__ = ["StatementRegistry"]


class StatementRegistry:
    """Manages a collection of loaded financial statement structures.

    This registry holds instances of `StatementStructure`, keyed by their unique
    IDs. It prevents duplicate registrations and provides methods to access
    registered statements individually or collectively.

    Attributes:
        _statements: A dictionary mapping statement IDs (str) to their
                     corresponding `StatementStructure` objects.
    """

    def __init__(self) -> None:
        """Initialize an empty statement registry."""
        self._statements: dict[str, StatementStructure] = {}
        logger.debug("StatementRegistry initialized.")

    def register(self, statement: StatementStructure) -> None:
        """Register a statement structure with the registry.

        Ensures the provided object is a `StatementStructure` with a valid ID
        and that the ID is not already present in the registry.

        Args:
            statement: The `StatementStructure` instance to register.

        Raises:
            TypeError: If the `statement` argument is not an instance of
                `StatementStructure`.
            ValueError: If the `statement` has an invalid or empty ID.
            StatementError: If a statement with the same ID (`statement.id`) is
                already registered.
        """
        if not isinstance(statement, StatementStructure):
            raise TypeError("Only StatementStructure objects can be registered.")

        statement_id = statement.id
        if not statement_id:
            raise ValueError(
                "StatementStructure must have a valid non-empty id to be registered."
            )

        if statement_id in self._statements:
            # Policy: Raise error on conflict
            logger.error(
                f"Attempted to register duplicate statement ID: '{statement_id}'"
            )
            raise StatementError(
                message=f"Statement with ID '{statement_id}' is already registered.",
                # statement_id=statement_id # Add if StatementError accepts this arg
            )

        self._statements[statement_id] = statement
        logger.info(f"Registered statement '{statement.name}' with ID '{statement_id}'")

    def get(self, statement_id: str) -> Optional[StatementStructure]:
        """Get a registered statement by its ID.

        Returns:
            The `StatementStructure` instance associated with the given ID if
            it exists, otherwise returns `None`.

        Example:
            >>> registry = StatementRegistry()
            >>> # Assume 'income_statement' is a valid StatementStructure instance
            >>> # registry.register(income_statement)
            >>> retrieved_statement = registry.get("income_statement_id")
            >>> if retrieved_statement:
            ...     logger.info(f"Found: {retrieved_statement.name}")
            ... else:
            ...     logger.info("Statement not found.")
        """
        return self._statements.get(statement_id)

    def get_all_ids(self) -> list[str]:
        """Get the IDs of all registered statements.

        Returns:
            A list containing the unique IDs of all statements currently held
            in the registry.
        """
        return list(self._statements.keys())

    def get_all_statements(self) -> list[StatementStructure]:
        """Get all registered statement structure objects.

        Returns:
            A list containing all `StatementStructure` objects currently held
            in the registry.
        """
        return list(self._statements.values())

    def clear(self) -> None:
        """Remove all statement structures from the registry.

        Resets the registry to an empty state.
        """
        self._statements = {}
        logger.info("StatementRegistry cleared.")

    def __len__(self) -> int:
        """Return the number of registered statements."""
        return len(self._statements)

    def __contains__(self, statement_id: str) -> bool:
        """Check if a statement ID exists in the registry.

        Allows using the `in` operator with the registry.

        Args:
            statement_id: The statement ID to check for.

        Returns:
            `True` if a statement with the given ID is registered, `False` otherwise.

        Example:
            >>> registry = StatementRegistry()
            >>> # Assume 'income_statement' is registered with ID 'IS_2023'
            >>> # registry.register(income_statement)
            >>> print("IS_2023" in registry)  # Output: True
            >>> print("BS_2023" in registry)  # Output: False
        """
        return statement_id in self._statements
