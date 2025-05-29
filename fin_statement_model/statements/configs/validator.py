"""Statement configuration handling for Financial Statement Model.

This module provides utilities for parsing and validating statement configuration data
(provided as a dictionary) and building StatementStructure objects.
"""

# Removed json, yaml, Path imports as file loading moved to IO
import logging
from typing import Any, Optional

# Use absolute imports
# Import Pydantic models for building from validated configuration
from fin_statement_model.statements.configs.models import (
    StatementModel,
)
from pydantic import ValidationError  # Import directly

# Configure logging
logger = logging.getLogger(__name__)


class StatementConfig:
    """Manages configuration parsing and building for financial statement structures.

    This class handles validating statement configuration data (provided as a dictionary)
    and building StatementStructure objects from these configurations.
    It does NOT handle file loading.
    """

    def __init__(self, config_data: dict[str, Any]):
        """Initialize a statement configuration processor.

        Args:
            config_data: Dictionary containing the raw configuration data.

        Raises:
            ValueError: If config_data is not a non-empty dictionary.
        """
        if not config_data or not isinstance(config_data, dict):
            raise ValueError("config_data must be a non-empty dictionary.")
        self.config_data = config_data
        # Remove config_path attribute
        # self.config_path = None # No longer needed
        self.model: Optional[StatementModel] = None  # Store validated model

    # Removed load_config method
    # def load_config(self, config_path: str) -> None:
    #     ...

    def validate_config(self) -> list[str]:
        """Validate the configuration data using Pydantic models.

        Returns:
            list[str]: List of validation errors, or empty list if valid.
                     Stores the validated model in self.model on success.
        """
        try:
            # Validate against Pydantic StatementModel
            # Removed redundant import from inside method
            self.model = StatementModel.model_validate(self.config_data)
            return []
        except ValidationError as ve:
            # Convert Pydantic errors to list of strings
            errors: list[str] = []
            for err in ve.errors():
                loc = ".".join(str(x) for x in err.get("loc", []))
                msg = err.get("msg", "")
                errors.append(f"{loc}: {msg}")
            self.model = None  # Ensure model is not set on validation error
            return errors
        except Exception as e:
            # Catch other potential validation issues
            logger.exception("Unexpected error during configuration validation")
            self.model = None
            return [f"Unexpected validation error: {e}"]
