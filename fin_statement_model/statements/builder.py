"""Builds StatementStructure objects from validated StatementConfig models.

This module provides the `StatementStructureBuilder`, which translates the
deserialized and validated configuration (represented by `StatementConfig`
containing Pydantic models) into the hierarchical `StatementStructure` object
used internally for representing the layout and components of a financial
statement.
"""

import logging
from typing import Union

# Assuming config and structure modules are accessible
from .config.config import StatementConfig
from .config.models import (
    SectionModel,
    BaseItemModel,
    LineItemModel,
    CalculatedItemModel,
    SubtotalModel,
)
from .structure import (
    StatementStructure,
    Section,
    LineItem,
    CalculatedLineItem,
    SubtotalLineItem,
)
from .errors import ConfigurationError

logger = logging.getLogger(__name__)

__all__ = ["StatementStructureBuilder"]


class StatementStructureBuilder:
    """Constructs a `StatementStructure` object from a validated configuration.

    Takes a `StatementConfig` instance (which should have successfully passed
    validation, populating its `.model` attribute) and recursively builds the
    corresponding `StatementStructure`, including its sections, line items,
    calculated items, subtotals, and nested sections.
    """

    def build(self, config: StatementConfig) -> StatementStructure:
        """Build a `StatementStructure` from a validated `StatementConfig`.

        This is the main public method of the builder. It orchestrates the
        conversion process, calling internal helper methods to build sections
        and items.

        Args:
            config: A `StatementConfig` instance whose `.validate_config()`
                method has been successfully called, populating `config.model`.

        Returns:
            The fully constructed `StatementStructure` object, ready to be
            registered or used.

        Raises:
            ValueError: If the provided `config` object has not been validated
                (i.e., `config.model` is `None`).
            ConfigurationError: If an unexpected error occurs during the building
                process, potentially indicating an issue not caught by the
                initial Pydantic validation or an internal inconsistency.
        """
        if config.model is None:
             # Ensure validation has run successfully before building
             raise ValueError(
                 "StatementConfig must be validated (config.model must be set) "
                 "before building the structure."
             )

        # Build from the validated Pydantic model stored in config.model
        try:
            stmt_model = config.model # Use validated model from config
            statement = StatementStructure(
                id=stmt_model.id,
                name=stmt_model.name,
                description=stmt_model.description,
                metadata=stmt_model.metadata,
            )
            for sec_model in stmt_model.sections:
                section = self._build_section_model(sec_model)
                statement.add_section(section)
            logger.info(f"Successfully built StatementStructure for ID '{statement.id}'")
            return statement
        except Exception as e:
             # Catch potential errors during the building process itself
             logger.exception(f"Error building statement structure from validated model for ID '{config.model.id}'")
             raise ConfigurationError(
                 message=f"Failed to build statement structure from validated config: {e}",
                 errors=[str(e)]
             ) from e

    def _build_section_model(self, section_model: SectionModel) -> Section:
        """Build a `Section` object from a `SectionModel`.

        Recursively builds the items and subsections within this section.

        Args:
            section_model: The Pydantic model representing the section configuration.

        Returns:
            A `Section` instance corresponding to the model.
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
            # Recursively build subsections
            section.add_item(self._build_section_model(sub))
        if section_model.subtotal:
            section.subtotal = self._build_subtotal_model(section_model.subtotal)
        return section

    def _build_item_model(
        self, item_model: BaseItemModel
    ) -> Union[LineItem, CalculatedLineItem, SubtotalLineItem, Section]:
        """Build a statement item object from its corresponding Pydantic model.

        Dispatches the building process based on the specific type of the input
        model (`LineItemModel`, `CalculatedItemModel`, `SubtotalModel`, or
        `SectionModel` for nested sections).

        Args:
            item_model: The Pydantic model representing a line item, calculated
                item, subtotal, or nested section.

        Returns:
            The corresponding `StatementStructure` component (`LineItem`,
            `CalculatedLineItem`, `SubtotalLineItem`, or `Section`).

        Raises:
            ConfigurationError: If an unknown or unexpected model type is
                encountered.
        """
        # Dispatch by model instance type
        if isinstance(item_model, SectionModel):
            # Handle nested sections directly
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
            # Pass the calculation model directly or its dict representation
            return CalculatedLineItem(
                id=item_model.id,
                name=item_model.name,
                # Pass the nested Pydantic model if structure expects it, else dump
                calculation=item_model.calculation.model_dump(), # Assuming structure expects dict
                description=item_model.description,
                sign_convention=item_model.sign_convention,
                metadata=item_model.metadata,
            )
        if isinstance(item_model, SubtotalModel):
            return self._build_subtotal_model(item_model)

        # Should be unreachable if Pydantic validation works
        logger.error(f"Encountered unknown item model type during build: {type(item_model).__name__}")
        raise ConfigurationError(
            message=f"Unknown item model type: {type(item_model).__name__}",
            errors=[f"Item '{getattr(item_model, 'id', '<unknown>')}' has invalid model type."],
        )

    def _build_subtotal_model(self, subtotal_model: SubtotalModel) -> SubtotalLineItem:
        """Build a `SubtotalLineItem` object from a `SubtotalModel`.

        Extracts the relevant item IDs to be summed, either from the explicit
        `items_to_sum` list or from the `calculation.inputs` if provided.

        Args:
            subtotal_model: The Pydantic model representing the subtotal configuration.

        Returns:
            A `SubtotalLineItem` instance.
        """
        # Consolidate logic for getting item IDs
        item_ids = (
            subtotal_model.calculation.inputs
            if subtotal_model.calculation and subtotal_model.calculation.inputs
            else subtotal_model.items_to_sum
        )
        if not item_ids:
             logger.warning(f"Subtotal '{subtotal_model.id}' has no items_to_sum or calculation inputs defined.")
             # Decide handling: error or allow empty subtotal?
             # Allowing for now, may need adjustment based on desired behavior.

        return SubtotalLineItem(
            id=subtotal_model.id,
            name=subtotal_model.name,
            item_ids=item_ids or [], # Ensure it's a list
            description=subtotal_model.description,
            sign_convention=subtotal_model.sign_convention,
            metadata=subtotal_model.metadata,
        )
