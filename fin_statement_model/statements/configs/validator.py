"""Statement configuration handling for Financial Statement Model.

This module provides utilities for parsing and validating statement configuration data
(provided as a dictionary) and building StatementStructure objects.
"""

# Removed json, yaml, Path imports as file loading moved to IO
import logging
from typing import Any

from pydantic import ValidationError  # Import directly

from fin_statement_model.core.nodes import standard_node_registry

# Use absolute imports
# Import Pydantic models for building from validated configuration
from fin_statement_model.statements.configs.models import (
    BaseItemModel,
    CalculatedItemModel,
    CalculationSpec,
    LineItemModel,
    MetricItemModel,
    SectionModel,
    StatementModel,
    SubtotalModel,
)

# Import Result types for enhanced error handling
from fin_statement_model.statements.utilities.result_types import (
    ErrorCollector,
    ErrorDetail,
    ErrorSeverity,
)

# Import UnifiedNodeValidator for node ID validation
from fin_statement_model.statements.validation import UnifiedNodeValidator

# Configure logging
logger = logging.getLogger(__name__)


class StatementConfig:
    """Manages configuration parsing and building for financial statement structures.

    This class handles validating statement configuration data (provided as a dictionary)
    and building StatementStructure objects from these configurations.
    It does NOT handle file loading.
    """

    def __init__(
        self,
        config_data: dict[str, Any],
        enable_node_validation: bool = False,
        node_validation_strict: bool = False,
        node_validator: UnifiedNodeValidator | None = None,
    ):
        """Initialize a statement configuration processor.

        Args:
            config_data: Dictionary containing the raw configuration data.
            enable_node_validation: If True, validates node IDs using UnifiedNodeValidator.
            node_validation_strict: If True, treats node validation failures as errors.
                                   If False, treats them as warnings.
            node_validator: Optional pre-configured UnifiedNodeValidator instance.
                           If None and enable_node_validation is True, creates a default instance.

        Raises:
            ValueError: If config_data is not a non-empty dictionary.
        """
        if not config_data or not isinstance(config_data, dict):
            raise ValueError("config_data must be a non-empty dictionary.")

        self.config_data = config_data
        self.model: StatementModel | None = None  # Store validated model

        # Node validation configuration
        self.enable_node_validation = enable_node_validation
        self.node_validation_strict = node_validation_strict

        # Initialize node_validator attribute
        self.node_validator: UnifiedNodeValidator | None = None
        if enable_node_validation:
            if node_validator is not None:
                self.node_validator = node_validator
            else:
                # Create default validator
                self.node_validator = UnifiedNodeValidator(
                    standard_node_registry,
                    strict_mode=node_validation_strict,
                    auto_standardize=True,
                    warn_on_non_standard=True,
                    enable_patterns=True,
                )

    def validate_config(self) -> list[ErrorDetail]:
        """Validate the configuration data using Pydantic models and optional node validation.

        Returns:
            list[ErrorDetail]: List of validation errors, or empty list if valid.
                     Stores the validated model in self.model on success.
        """
        error_collector = ErrorCollector()

        try:
            # First perform Pydantic validation
            self.model = StatementModel.model_validate(self.config_data)

            # If node validation is enabled, perform additional validation
            if self.enable_node_validation and self.node_validator:
                self._validate_node_ids(self.model, error_collector)

            # Collect structured errors (always include errors)
            errors: list[ErrorDetail] = error_collector.get_errors()
            warnings: list[ErrorDetail] = error_collector.get_warnings()

            if self.node_validation_strict:
                result: list[ErrorDetail] = errors + warnings
            else:
                # Log warnings but exclude from returned errors
                for warning in warnings:
                    logger.warning("Node validation warning: %s", warning)
                result = errors

        except ValidationError as ve:
            # Convert Pydantic errors to structured ErrorDetail list
            error_details: list[ErrorDetail] = []
            for err in ve.errors():
                loc = ".".join(str(x) for x in err.get("loc", []))
                msg = err.get("msg", "")
                error_details.append(
                    ErrorDetail(
                        code="pydantic_validation",
                        message=msg,
                        context=loc,
                        severity=ErrorSeverity.ERROR,
                    )
                )
            self.model = None  # Ensure model is not set on validation error
            return error_details
        except Exception as e:
            # Catch other potential validation issues
            logger.exception("Unexpected error during configuration validation")
            self.model = None
            return [
                ErrorDetail(
                    code="unexpected_validation_error",
                    message=str(e),
                    severity=ErrorSeverity.ERROR,
                )
            ]
        else:
            return result

    def _validate_node_ids(self, model: StatementModel, error_collector: ErrorCollector) -> None:
        """Validate all node IDs in the statement model using UnifiedNodeValidator.

        Args:
            model: The validated StatementModel to check.
            error_collector: ErrorCollector to accumulate validation issues.
        """
        logger.debug("Starting node ID validation for statement '%s'", model.id)

        # Validate statement ID itself
        self._validate_single_node_id(model.id, "statement", "statement.id", error_collector)

        # Validate all sections recursively
        for section in model.sections:
            self._validate_section_node_ids(section, error_collector, f"statement.{model.id}")

    def _validate_section_node_ids(
        self,
        section: SectionModel,
        error_collector: ErrorCollector,
        parent_context: str,
    ) -> None:
        """Validate node IDs within a section and its items.

        Args:
            section: The section model to validate.
            error_collector: ErrorCollector to accumulate validation issues.
            parent_context: Context string for error reporting.
        """
        section_context = f"{parent_context}.section.{section.id}"

        # Validate section ID
        self._validate_single_node_id(section.id, "section", f"{section_context}.id", error_collector)

        # Validate all items in the section
        for item in section.items:
            self._validate_item_node_ids(item, error_collector, section_context)

        # Validate subsections recursively
        for subsection in section.subsections:
            self._validate_section_node_ids(subsection, error_collector, section_context)

        # Validate section subtotal if present
        if section.subtotal:
            self._validate_item_node_ids(section.subtotal, error_collector, section_context)

    def _validate_item_node_ids(
        self, item: BaseItemModel, error_collector: ErrorCollector, parent_context: str
    ) -> None:
        """Validate node IDs within a specific item.

        Args:
            item: The item model to validate.
            error_collector: ErrorCollector to accumulate validation issues.
            parent_context: Context string for error reporting.
        """
        item_context = f"{parent_context}.item.{item.id}"

        # Validate the item ID itself
        self._validate_single_node_id(item.id, "item", f"{item_context}.id", error_collector)

        # Type-specific validation
        if isinstance(item, LineItemModel):
            # Validate node_id if present
            if item.node_id:
                self._validate_single_node_id(item.node_id, "node", f"{item_context}.node_id", error_collector)

            # Validate standard_node_ref if present
            if item.standard_node_ref:
                self._validate_single_node_id(
                    item.standard_node_ref,
                    "standard_node",
                    f"{item_context}.standard_node_ref",
                    error_collector,
                )

        elif isinstance(item, CalculatedItemModel):
            # Validate calculation inputs
            self._validate_calculation_inputs(item.calculation, error_collector, item_context)

        elif isinstance(item, MetricItemModel):
            # Validate metric inputs (the values, not the keys)
            for input_key, input_id in item.inputs.items():
                self._validate_single_node_id(
                    input_id,
                    "metric_input",
                    f"{item_context}.inputs.{input_key}",
                    error_collector,
                )

        elif isinstance(item, SubtotalModel):
            # Validate items_to_sum if present
            if item.items_to_sum:
                for i, input_id in enumerate(item.items_to_sum):
                    self._validate_single_node_id(
                        input_id,
                        "subtotal_input",
                        f"{item_context}.items_to_sum[{i}]",
                        error_collector,
                    )

            # Validate calculation inputs if present
            if item.calculation:
                self._validate_calculation_inputs(item.calculation, error_collector, item_context)

        elif isinstance(item, SectionModel):
            # Recursive validation for nested sections
            self._validate_section_node_ids(item, error_collector, parent_context)

    def _validate_calculation_inputs(
        self,
        calculation: CalculationSpec,
        error_collector: ErrorCollector,
        parent_context: str,
    ) -> None:
        """Validate inputs within a calculation specification.

        Args:
            calculation: The calculation specification to validate.
            error_collector: ErrorCollector to accumulate validation issues.
            parent_context: Context string for error reporting.
        """
        for i, input_id in enumerate(calculation.inputs):
            self._validate_single_node_id(
                input_id,
                "calculation_input",
                f"{parent_context}.calculation.inputs[{i}]",
                error_collector,
            )

    def _validate_single_node_id(
        self,
        node_id: str,
        node_type: str,
        context: str,
        error_collector: ErrorCollector,
    ) -> None:
        """Validate a single node ID using the UnifiedNodeValidator.

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
                parent_nodes=None,  # Could be enhanced to track parent context
                use_cache=True,
            )

            # Determine severity based on validation result and configuration
            if not validation_result.is_valid:
                severity = ErrorSeverity.ERROR if self.node_validation_strict else ErrorSeverity.WARNING
                message = f"Invalid {node_type} ID '{node_id}': {validation_result.message}"
                if severity == ErrorSeverity.ERROR:
                    error_collector.add_error(
                        code="invalid_node_id",
                        message=message,
                        context=context,
                        source=node_id,
                    )
                else:
                    error_collector.add_warning(
                        code="invalid_node_id",
                        message=message,
                        context=context,
                        source=node_id,
                    )

            elif validation_result.category in [
                "alternate",
                "subnode_nonstandard",
                "custom",
            ]:
                # These are valid but could be improved
                error_collector.add_warning(
                    code="non_standard_node_id",
                    message=f"Non-standard {node_type} ID '{node_id}': {validation_result.message}",
                    context=context,
                    source=node_id,
                )

            # Add suggestions if available
            if validation_result.suggestions:
                suggestion_msg = (
                    f"Suggestions for {node_type} ID '{node_id}': {'; '.join(validation_result.suggestions)}"
                )
                error_collector.add_warning(
                    code="node_id_suggestions",
                    message=suggestion_msg,
                    context=context,
                    source=node_id,
                )

        except Exception as e:
            logger.exception("Error validating node ID '%s' in context '%s'", node_id, context)
            error_collector.add_warning(
                code="node_validation_error",
                message=f"Failed to validate {node_type} ID '{node_id}': {e}",
                context=context,
                source=node_id,
            )
