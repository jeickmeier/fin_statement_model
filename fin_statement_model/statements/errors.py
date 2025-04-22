"""Exceptions for the statements package."""

from typing import Optional
from fin_statement_model.core.errors import FinancialModelError


class StatementError(FinancialModelError):
    """Base exception for statement-related errors."""


class ConfigurationError(StatementError):
    """Exception raised for statement configuration errors."""

    def __init__(
        self,
        message: str,
        config_path: Optional[str] = None,
        errors: Optional[list[str]] = None,
    ):
        """Initialize a configuration error.

        Args:
            message: Main error message
            config_path: Path to the configuration file that caused the error
            errors: List of specific validation errors
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
