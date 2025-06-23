"""Custom Exception classes for the `fin_statement_model.statements` package.

These exceptions provide more specific error information related to statement
definition, configuration, building, and processing, inheriting from the base
`FinancialModelError` defined in `fin_statement_model.core.errors`.
"""

from fin_statement_model.core.errors import (
    ConfigurationError,
    StatementError,
)

__all__ = [
    "ConfigurationError",
    "StatementBuilderError",
    "StatementError",
    "StatementValidationError",
]


class StatementBuilderError(StatementError):
    """Exception raised during statement structure building.

    This includes errors encountered while constructing nodes from statement
    definitions or creating graph relationships.
    """

    def __init__(
        self,
        message: str,
        item_id: str | None = None,
        statement_type: str | None = None,
    ):
        """Initialize a StatementBuilderError.

        Args:
            message: The primary error message.
            item_id: Optional ID of the item causing the error.
            statement_type: Optional type of statement being built.
        """
        self.item_id = item_id
        self.statement_type = statement_type

        details = []
        if statement_type:
            details.append(f"Statement type: {statement_type}")
        if item_id:
            details.append(f"Item ID: {item_id}")

        full_message = message
        if details:
            full_message = f"{message} ({', '.join(details)})"

        super().__init__(full_message)


class StatementValidationError(StatementError):
    """Exception raised during statement validation.

    This includes structural validation errors, consistency checks,
    and statement-specific rule violations.
    """

    def __init__(
        self,
        message: str,
        validation_errors: list[str] | None = None,
        statement_id: str | None = None,
    ):
        """Initialize a StatementValidationError.

        Args:
            message: The primary error message.
            validation_errors: Optional list of specific validation failures.
            statement_id: Optional ID of the statement being validated.
        """
        self.validation_errors = validation_errors or []

        full_message = message
        if statement_id:
            full_message = f"{message} for statement '{statement_id}'"
        if validation_errors:
            full_message = f"{full_message}:\n" + "\n".join(f"  - {error}" for error in validation_errors)

        super().__init__(full_message, statement_id=statement_id)
