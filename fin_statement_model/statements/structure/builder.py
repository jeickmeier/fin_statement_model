"""Builds StatementStructure objects from validated StatementConfig models.

This module provides the `StatementStructureBuilder`, which translates the
deserialized and validated configuration (represented by `StatementConfig`
containing Pydantic models) into the hierarchical `StatementStructure` object
used internally for representing the layout and components of a financial
statement.
"""

import logging
from typing import Union, Optional, Any, cast

# Assuming config and structure modules are accessible
from fin_statement_model.statements.configs.validator import StatementConfig
from fin_statement_model.statements.configs.models import (
    SectionModel,
    BaseItemModel,
    LineItemModel,
    CalculatedItemModel,
    MetricItemModel,
    SubtotalModel,
    StatementModel,
    AdjustmentFilterSpec,
)
from fin_statement_model.statements.structure import (
    StatementStructure,
    Section,
    LineItem,
    MetricLineItem,
    CalculatedLineItem,
    SubtotalLineItem,
)
from fin_statement_model.statements.errors import ConfigurationError

# Import UnifiedNodeValidator for optional node validation during build
from fin_statement_model.statements.validation import UnifiedNodeValidator
from fin_statement_model.config.access import cfg
from fin_statement_model.core.nodes import standard_node_registry

# Import Result types for enhanced error handling
from fin_statement_model.statements.utilities.result_types import (
    ErrorCollector,
    ErrorSeverity,
)

# Import adjustment types for filter conversion
from fin_statement_model.core.adjustments.models import AdjustmentFilter, AdjustmentType

logger = logging.getLogger(__name__)

__all__ = ["StatementStructureBuilder"]


class StatementStructureBuilder:
    """Constructs a `StatementStructure` object from a validated configuration.

    Takes a `StatementConfig` instance (which should have successfully passed
    validation, populating its `.model` attribute) and recursively builds the
    corresponding `StatementStructure`, including its sections, line items,
    calculated items, subtotals, and nested sections.
    """

    def __init__(
        self,
        enable_node_validation: Optional[bool] = None,
        node_validation_strict: Optional[bool] = None,
        node_validator: Optional[UnifiedNodeValidator] = None,
    ) -> None:
        """Initialize the StatementStructureBuilder.

        Defaults for validation flags come from the global statements config, but can be overridden locally.
        Args:
            enable_node_validation: If True, validates node IDs during build.
            node_validation_strict: If True, treats validation failures as errors.
            node_validator: Optional pre-configured UnifiedNodeValidator instance.
        """
        # Pull defaults from global config if not provided
        if enable_node_validation is None:
            enable_node_validation = cfg("statements.enable_node_validation")
        if node_validation_strict is None:
            node_validation_strict = cfg("statements.node_validation_strict")
        self.enable_node_validation = enable_node_validation
        self.node_validation_strict = node_validation_strict

        # Initialize node_validator
        self.node_validator: Optional[UnifiedNodeValidator] = None
        if self.enable_node_validation:
            if node_validator is not None:
                self.node_validator = node_validator
            else:
                # Create default validator using strict flag
                self.node_validator = UnifiedNodeValidator(
                    standard_node_registry,
                    strict_mode=self.node_validation_strict,
                    auto_standardize=True,
                    warn_on_non_standard=True,
                    enable_patterns=True,
                )
        else:
            self.node_validator = None

    def _convert_adjustment_filter(
        self, filter_input: Optional[Union[AdjustmentFilterSpec, list[str]]]
    ) -> Optional[Any]:
        """Convert configuration adjustment filter to core AdjustmentFilter or tag set.

        Args:
            filter_input: The filter specification from configuration.

        Returns:
            AdjustmentFilter instance, set of tags, or None.
        """
        # Use global default adjustment filter if none provided
        if filter_input is None:
            default_filter = cfg("statements.default_adjustment_filter")
            if default_filter is None:
                return None
            filter_input = default_filter
        # Simple list of tags - convert to set
        elif isinstance(filter_input, list):
            return set(filter_input)
        # Configuration spec to core filter conversion
        elif isinstance(filter_input, AdjustmentFilterSpec):
            # Convert AdjustmentFilterSpec to AdjustmentFilter
            kwargs: dict[str, Any] = {}

            # Convert list fields to sets
            if filter_input.include_scenarios:
                kwargs["include_scenarios"] = set(filter_input.include_scenarios)
            if filter_input.exclude_scenarios:
                kwargs["exclude_scenarios"] = set(filter_input.exclude_scenarios)
            if filter_input.include_tags:
                kwargs["include_tags"] = set(filter_input.include_tags)
            if filter_input.exclude_tags:
                kwargs["exclude_tags"] = set(filter_input.exclude_tags)
            if filter_input.require_all_tags:
                kwargs["require_all_tags"] = set(filter_input.require_all_tags)

            # Convert string types to AdjustmentType enums
            if filter_input.include_types:
                kwargs["include_types"] = cast(
                    set[AdjustmentType],
                    {
                        AdjustmentType(type_str)
                        for type_str in filter_input.include_types
                    },
                )
            if filter_input.exclude_types:
                kwargs["exclude_types"] = cast(
                    set[AdjustmentType],
                    {
                        AdjustmentType(type_str)
                        for type_str in filter_input.exclude_types
                    },
                )

            # Pass through period
            if filter_input.period:
                kwargs["period"] = filter_input.period

            # Create AdjustmentFilter from kwargs
            return AdjustmentFilter(**kwargs)

        # Unknown type - log warning and return None
        logger.warning(f"Unknown adjustment filter type: {type(filter_input)}")
        return None

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
            stmt_model = config.model  # Use validated model from config

            # Optional node validation during build
            if self.enable_node_validation and self.node_validator:
                error_collector = ErrorCollector()
                self._validate_structure_node_ids(stmt_model, error_collector)

                # Handle validation results
                if error_collector.has_errors() and self.node_validation_strict:
                    # Fail build on validation errors in strict mode
                    error_messages = [
                        str(error) for error in error_collector.get_errors()
                    ]
                    raise ConfigurationError(
                        message=f"Node validation failed for statement '{stmt_model.id}'",
                        errors=error_messages,
                    )
                elif error_collector.has_warnings() or error_collector.has_errors():
                    # Log warnings and non-strict errors
                    for warning in error_collector.get_warnings():
                        logger.warning(f"Build-time node validation: {warning}")
                    if not self.node_validation_strict:
                        for error in error_collector.get_errors():
                            logger.warning(f"Build-time node validation: {error}")

            statement = StatementStructure(
                id=stmt_model.id,
                name=stmt_model.name,
                description=cast(str, stmt_model.description),
                metadata=stmt_model.metadata,
                units=stmt_model.units,
                display_scale_factor=stmt_model.display_scale_factor,
            )
            for sec_model in stmt_model.sections:
                section = self._build_section_model(sec_model)
                statement.add_section(section)
            logger.info(
                f"Successfully built StatementStructure for ID '{statement.id}'"
            )
            return statement
        except Exception as e:
            # Catch potential errors during the building process itself
            logger.exception(
                f"Error building statement structure from validated model for ID '{config.model.id}'"
            )
            raise ConfigurationError(
                message=f"Failed to build statement structure from validated config: {e}",
                errors=[str(e)],
            ) from e

    def _validate_structure_node_ids(
        self, stmt_model: StatementModel, error_collector: ErrorCollector
    ) -> None:
        """Validate node IDs in the statement structure during build.

        This is a simpler validation focused on the final structure,
        complementing the config-level validation.

        Args:
            stmt_model: The StatementModel to validate.
            error_collector: ErrorCollector to accumulate validation issues.
        """
        logger.debug(f"Build-time node validation for statement '{stmt_model.id}'")

        # Validate key node references that will be used in the built structure
        collected_node_refs = set()

        # Collect all node references from the structure
        def collect_node_refs(items: list[Any]) -> None:
            for item in items:
                if isinstance(item, LineItemModel):
                    if item.node_id:
                        collected_node_refs.add(
                            (item.node_id, "line_item_node", f"item.{item.id}.node_id")
                        )
                    if item.standard_node_ref:
                        collected_node_refs.add(
                            (
                                item.standard_node_ref,
                                "standard_node",
                                f"item.{item.id}.standard_node_ref",
                            )
                        )
                elif isinstance(item, CalculatedItemModel):
                    collected_node_refs.add(
                        (item.id, "calculated_node", f"item.{item.id}.id")
                    )
                elif isinstance(item, MetricItemModel):
                    collected_node_refs.add(
                        (item.id, "metric_node", f"item.{item.id}.id")
                    )
                elif isinstance(item, SubtotalModel):
                    collected_node_refs.add(
                        (item.id, "subtotal_node", f"item.{item.id}.id")
                    )
                elif isinstance(item, SectionModel):
                    collect_node_refs(item.items)
                    collect_node_refs(item.subsections)
                    if item.subtotal:
                        collected_node_refs.add(
                            (
                                item.subtotal.id,
                                "subtotal_node",
                                f"section.{item.id}.subtotal.id",
                            )
                        )

        # Collect all node references
        for section in stmt_model.sections:
            collect_node_refs([section, *section.items, *section.subsections])

        # Validate collected references
        for node_id, node_type, context in collected_node_refs:
            self._validate_single_build_node_id(
                node_id, node_type, context, error_collector
            )

    def _validate_single_build_node_id(
        self,
        node_id: str,
        node_type: str,
        context: str,
        error_collector: ErrorCollector,
    ) -> None:
        """Validate a single node ID during build process.

        Args:
            node_id: The node ID to validate.
            node_type: Type description for error messages.
            context: Context string for error reporting.
            error_collector: ErrorCollector to accumulate validation issues.
        """
        if not self.node_validator:
            return

        try:
            validation_result = self.node_validator.validate(
                node_id,
                node_type=node_type,
                use_cache=True,
            )

            # Only report significant issues during build
            if not validation_result.is_valid:
                severity = (
                    ErrorSeverity.ERROR
                    if self.node_validation_strict
                    else ErrorSeverity.WARNING
                )
                message = f"Build validation: Invalid {node_type} '{node_id}': {validation_result.message}"

                if severity == ErrorSeverity.ERROR:
                    error_collector.add_error(
                        code="build_invalid_node_id",
                        message=message,
                        context=context,
                        source=node_id,
                    )
                else:
                    error_collector.add_warning(
                        code="build_invalid_node_id",
                        message=message,
                        context=context,
                        source=node_id,
                    )

        except Exception as e:
            logger.exception(
                f"Error during build-time validation of node ID '{node_id}'"
            )
            error_collector.add_warning(
                code="build_node_validation_error",
                message=f"Build validation error for {node_type} '{node_id}': {e}",
                context=context,
                source=node_id,
            )

    def _build_section_model(self, section_model: SectionModel) -> Section:
        """Build a `Section` object from a `SectionModel`.

        Recursively builds the items and subsections within this section.

        Args:
            section_model: The Pydantic model representing the section configuration.

        Returns:
            A `Section` instance corresponding to the model.
        """
        # Convert adjustment filter
        adjustment_filter = self._convert_adjustment_filter(
            section_model.default_adjustment_filter
        )

        section = Section(
            id=section_model.id,
            name=section_model.name,
            description=cast(str, section_model.description),
            metadata=section_model.metadata,
            default_adjustment_filter=adjustment_filter,
            display_format=section_model.display_format,
            hide_if_all_zero=section_model.hide_if_all_zero,
            css_class=section_model.css_class,
            notes_references=section_model.notes_references,
            units=section_model.units,
            display_scale_factor=section_model.display_scale_factor,
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
    ) -> Union[LineItem, CalculatedLineItem, MetricLineItem, SubtotalLineItem, Section]:
        """Build a statement item object from its corresponding Pydantic model.

        Dispatches the building process based on the specific type of the input
        model (`LineItemModel`, `CalculatedItemModel`, `MetricItemModel`,
        `SubtotalModel`, or `SectionModel` for nested sections).

        Args:
            item_model: The Pydantic model representing a line item, calculated
                item, metric item, subtotal, or nested section.

        Returns:
            The corresponding `StatementStructure` component (`LineItem`,
            `CalculatedLineItem`, `MetricLineItem`, `SubtotalLineItem`, or `Section`).

        Raises:
            TypeError: If an unexpected model type is encountered.
        """
        # Convert adjustment filter for all item types
        adjustment_filter = self._convert_adjustment_filter(
            item_model.default_adjustment_filter
        )

        # Dispatch by model instance type
        if isinstance(item_model, SectionModel):
            # Handle nested sections directly
            return self._build_section_model(item_model)
        if isinstance(item_model, LineItemModel):
            return LineItem(
                id=item_model.id,
                name=item_model.name,
                node_id=item_model.node_id,
                standard_node_ref=item_model.standard_node_ref,
                description=cast(str, item_model.description),
                sign_convention=item_model.sign_convention,
                metadata=item_model.metadata,
                default_adjustment_filter=adjustment_filter,
                display_format=item_model.display_format,
                hide_if_all_zero=item_model.hide_if_all_zero,
                css_class=item_model.css_class,
                notes_references=item_model.notes_references,
                units=item_model.units,
                display_scale_factor=item_model.display_scale_factor,
                is_contra=item_model.is_contra,
            )
        if isinstance(item_model, CalculatedItemModel):
            # Pass the calculation model directly or its dict representation
            return CalculatedLineItem(
                id=item_model.id,
                name=item_model.name,
                # Pass the nested Pydantic model if structure expects dict
                calculation=item_model.calculation.model_dump(),
                description=cast(str, item_model.description),
                sign_convention=item_model.sign_convention,
                metadata=item_model.metadata,
                default_adjustment_filter=adjustment_filter,
                display_format=item_model.display_format,
                hide_if_all_zero=item_model.hide_if_all_zero,
                css_class=item_model.css_class,
                notes_references=item_model.notes_references,
                units=item_model.units,
                display_scale_factor=item_model.display_scale_factor,
                is_contra=item_model.is_contra,
            )
        if isinstance(item_model, MetricItemModel):
            return MetricLineItem(
                id=item_model.id,
                name=item_model.name,
                metric_id=item_model.metric_id,
                inputs=item_model.inputs,
                description=cast(str, item_model.description),
                sign_convention=item_model.sign_convention,
                metadata=item_model.metadata,
                default_adjustment_filter=adjustment_filter,
                display_format=item_model.display_format,
                hide_if_all_zero=item_model.hide_if_all_zero,
                css_class=item_model.css_class,
                notes_references=item_model.notes_references,
                units=item_model.units,
                display_scale_factor=item_model.display_scale_factor,
                is_contra=item_model.is_contra,
            )
        if isinstance(item_model, SubtotalModel):
            return self._build_subtotal_model(item_model)

        # Should be unreachable if Pydantic validation works
        raise TypeError(f"Unhandled type: {type(item_model)}")

    def _build_subtotal_model(self, subtotal_model: SubtotalModel) -> SubtotalLineItem:
        """Build a `SubtotalLineItem` object from a `SubtotalModel`.

        Extracts the relevant item IDs to be summed, either from the explicit
        `items_to_sum` list or from the `calculation.inputs` if provided.

        Args:
            subtotal_model: The Pydantic model representing the subtotal configuration.

        Returns:
            A `SubtotalLineItem` instance.
        """
        # Convert adjustment filter
        adjustment_filter = self._convert_adjustment_filter(
            subtotal_model.default_adjustment_filter
        )

        # Consolidate logic for getting item IDs
        item_ids = (
            subtotal_model.calculation.inputs
            if subtotal_model.calculation and subtotal_model.calculation.inputs
            else subtotal_model.items_to_sum
        )
        if not item_ids:
            logger.warning(
                f"Subtotal '{subtotal_model.id}' has no items_to_sum or calculation inputs defined."
            )
            # Decide handling: error or allow empty subtotal?
            # Allowing for now, may need adjustment based on desired behavior.

        return SubtotalLineItem(
            id=subtotal_model.id,
            name=subtotal_model.name,
            item_ids=item_ids or [],  # Ensure it's a list
            description=cast(str, subtotal_model.description),
            sign_convention=subtotal_model.sign_convention,
            metadata=subtotal_model.metadata,
            default_adjustment_filter=adjustment_filter,
            display_format=subtotal_model.display_format,
            hide_if_all_zero=subtotal_model.hide_if_all_zero,
            css_class=subtotal_model.css_class,
            notes_references=subtotal_model.notes_references,
            units=subtotal_model.units,
            display_scale_factor=subtotal_model.display_scale_factor,
            is_contra=subtotal_model.is_contra,
        )
