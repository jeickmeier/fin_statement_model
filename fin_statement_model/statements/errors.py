"""Custom Exception classes for the `fin_statement_model.statements` package.

These exceptions provide more specific error information related to statement
definition, configuration, building, and processing, inheriting from the base
`FinancialModelError` defined in `fin_statement_model.core.errors`.
"""

from typing import Optional
from fin_statement_model.core.errors import FinancialModelError

__all__ = ["ConfigurationError", "StatementError"]


class StatementError(FinancialModelError):
    """Base exception for errors specific to the statements package.

    Indicates a general issue related to statement structure, processing, or
    management (e.g., duplicate registration, invalid item type).
    """


class ConfigurationError(StatementError):
    """Exception raised for errors during statement configuration processing.

    This includes errors encountered while loading, parsing, validating, or
    building statement structures from configuration files (e.g., YAML).

    Attributes:
        message (str): The main error message summarizing the issue.
        config_path (Optional[str]): The path to the configuration file that
            caused the error, if applicable.
        errors (List[str]): A list of specific validation errors or details
            related to the configuration issue.
    """

    def __init__(
        self,
        message: str,
        config_path: Optional[str] = None,
        errors: Optional[list[str]] = None,
    ):
        """Initialize a ConfigurationError.

        Args:
            message: The primary error message describing the configuration issue.
            config_path: Optional path to the configuration file involved.
            errors: Optional list of specific validation errors or related details.
        """
        self.message = message
        self.config_path = config_path
        self.errors = errors or []

        # Build detailed error message
        details = []
        if config_path:
            details.append(f"Config file: {config_path}")
        if errors:
            details.append("Validation errors:")
            details.extend([f"  - {error}" for error in errors])

        full_message = message
        if details:
            full_message = f"{message}\n" + "\n".join(details)

        super().__init__(full_message)
