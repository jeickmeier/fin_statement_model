"""Statement configuration handling for Financial Statement Model.

This module provides utilities for parsing and validating statement configuration data
(provided as a dictionary) and building StatementStructure objects.
"""

# Removed json, yaml, Path imports as file loading moved to IO
import logging
from typing import Any, Union, Optional

# Use absolute imports
from fin_statement_model.statements.errors import ConfigurationError
from fin_statement_model.statements.structure import (
    StatementStructure,
    Section,
    LineItem,
    CalculatedLineItem,
    SubtotalLineItem,
)
# Import Pydantic models for building from validated configuration
from fin_statement_model.statements.config.models import (
    StatementModel,
    SectionModel,
    BaseItemModel,
    LineItemModel,
    CalculatedItemModel,
    SubtotalModel,
)
from pydantic import ValidationError # Import directly

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
        self.model: Optional[StatementModel] = None # Store validated model

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
            self.model = None # Ensure model is not set on validation error
            return errors
        except Exception as e:
            # Catch other potential validation issues
            logger.exception("Unexpected error during configuration validation")
            self.model = None
            return [f"Unexpected validation error: {e}"]

    def build_statement_structure(self) -> StatementStructure:
        """Build a StatementStructure object from validated configuration data.

        Returns:
            The constructed StatementStructure object.

        Raises:
            ConfigurationError: If the configuration has not been validated successfully,
                                or if building fails.
        """
        # Ensure validation has run successfully first
        if self.model is None:
            errors = self.validate_config()
            if errors:
                error_msg = "Configuration validation failed"
                logger.error(f"{error_msg}: {'; '.join(errors)}")
                # Pass config_path=None or remove it if StatementManager handles paths
                raise ConfigurationError(message=error_msg, errors=errors)

        # Build from the validated Pydantic model stored in self.model
        try:
            # Add assertion for type checker, validation ensures it's not None here
            assert self.model is not None
            stmt_model = self.model
            statement = StatementStructure(
                id=stmt_model.id,
                name=stmt_model.name,
                description=stmt_model.description,
                metadata=stmt_model.metadata,
            )
            for sec_model in stmt_model.sections:
                section = self._build_section_model(sec_model)
                statement.add_section(section)
            return statement
        except Exception as e:
             # Catch potential errors during the building process itself
             logger.exception(f"Error building statement structure from validated model for ID '{self.model.id if self.model else 'unknown'}'")
             raise ConfigurationError(
                 message=f"Failed to build statement structure from validated config: {e}",
                 errors=[str(e)]
             ) from e

    def _build_section_model(self, section_model: SectionModel) -> Section:
        """Build a Section object from a section configuration.

        Args:
            section_model: Pydantic section model

        Returns:
            Section: The constructed section

        Raises:
            ConfigurationError: If the section configuration is invalid
        """
        section = Section(
            id=section_model.id,
            name=section_model.name,
            description=section_model.description,
            metadata=section_model.metadata,
        )
        for item in section_model.items:
            section.add_item(self._build_item_model(item))
        for sub in section_model.subsections:
            section.add_item(self._build_section_model(sub))
        if section_model.subtotal:
            section.subtotal = self._build_subtotal_model(section_model.subtotal)
        return section

    def _build_item_model(
        self, item_model: BaseItemModel
    ) -> Union[LineItem, CalculatedLineItem, SubtotalLineItem, Section]:
        """Build a LineItem object from an item configuration.

        Args:
            item_model: Pydantic item model instance

        Returns:
            Union[LineItem, CalculatedLineItem, SubtotalLineItem, Section]:
                The constructed item

        Raises:
            ConfigurationError: If the item configuration is invalid
        """
        # Dispatch by model instance type
        if isinstance(item_model, SectionModel):
            return self._build_section_model(item_model)
        if isinstance(item_model, LineItemModel):
            return LineItem(
                id=item_model.id,
                name=item_model.name,
                node_id=item_model.node_id,
                description=item_model.description,
                sign_convention=item_model.sign_convention,
                metadata=item_model.metadata,
            )
        if isinstance(item_model, CalculatedItemModel):
            return CalculatedLineItem(
                id=item_model.id,
                name=item_model.name,
                calculation=item_model.calculation.model_dump(),
                description=item_model.description,
                sign_convention=item_model.sign_convention,
                metadata=item_model.metadata,
            )
        if isinstance(item_model, SubtotalModel):
            return self._build_subtotal_model(item_model)
        raise ConfigurationError(
            message=f"Unknown item model type: {type(item_model).__name__}",
            errors=[f"Item '{getattr(item_model, 'id', '<unknown>')}' has invalid model type."],
        )

    def _build_subtotal_model(self, subtotal_model: SubtotalModel) -> SubtotalLineItem:
        """Build a SubtotalLineItem object from a subtotal configuration.

        Args:
            subtotal_model: Pydantic subtotal model

        Returns:
            SubtotalLineItem: The constructed subtotal line item

        Raises:
            ConfigurationError: If the subtotal configuration is invalid
        """
        item_ids = (
            subtotal_model.calculation.inputs
            if subtotal_model.calculation
            else subtotal_model.items_to_sum
        )
        return SubtotalLineItem(
            id=subtotal_model.id,
            name=subtotal_model.name,
            item_ids=item_ids,
            description=subtotal_model.description,
            sign_convention=subtotal_model.sign_convention,
            metadata=subtotal_model.metadata,
        )
