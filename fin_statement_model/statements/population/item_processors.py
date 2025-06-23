"""Item processors for converting statement items into graph nodes.

This module provides a processor hierarchy that handles the conversion of different
statement item types (MetricLineItem, CalculatedLineItem, SubtotalLineItem) into
graph nodes. Each processor encapsulates the logic for its specific item type,
reducing complexity and improving testability.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging
from typing import Any

from fin_statement_model.core.errors import (
    CalculationError,
    CircularDependencyError,
    ConfigurationError,
    MetricError,
    NodeError,
)
from fin_statement_model.core.graph import Graph
from fin_statement_model.core.metrics import metric_registry
from fin_statement_model.statements.population.id_resolver import IDResolver
from fin_statement_model.statements.structure import (
    CalculatedLineItem,
    MetricLineItem,
    StatementItem,
    StatementStructure,
    SubtotalLineItem,
)
from fin_statement_model.statements.utilities.result_types import (
    ErrorDetail,
    ErrorSeverity,
    Failure,
    Result,
    Success,
)

logger = logging.getLogger(__name__)

__all__ = [
    "CalculatedItemProcessor",
    "ItemProcessor",
    "ItemProcessorManager",
    "MetricItemProcessor",
    "ProcessorResult",
    "SubtotalItemProcessor",
]


@dataclass
class ProcessorResult:
    """Result of processing a statement item.

    Attributes:
        success: Whether the processing was successful.
        node_added: Whether a new node was added to the graph.
        error_message: Error message if processing failed.
        missing_inputs: List of missing input details (item_id, resolved_node_id).
    """

    success: bool
    node_added: bool = False
    error_message: str | None = None
    missing_inputs: list[tuple[str, str | None]] | None = None

    def to_result(self) -> Result[bool]:
        """Convert to the new Result type."""
        if self.success:
            return Success(value=self.node_added)

        errors = []
        if self.error_message:
            errors.append(
                ErrorDetail(
                    code="processing_error",
                    message=self.error_message,
                    severity=ErrorSeverity.ERROR,
                )
            )

        if self.missing_inputs:
            for item_id, node_id in self.missing_inputs:
                msg = (
                    f"Missing input: item '{item_id}' needs node '{node_id}'"
                    if node_id
                    else f"Missing input: item '{item_id}' not found/mappable"
                )
                errors.append(
                    ErrorDetail(
                        code="missing_input",
                        message=msg,
                        context=f"item_id={item_id}, node_id={node_id}",
                        severity=ErrorSeverity.ERROR,
                    )
                )

        return Failure(errors=errors)


class ItemProcessor(ABC):
    """Abstract base class for processing statement items into graph nodes.

    This base class provides common functionality for resolving input IDs
    and handling missing inputs across different item types.
    """

    def __init__(self, id_resolver: IDResolver, graph: Graph, statement: StatementStructure):
        """Initialize the processor.

        Args:
            id_resolver: ID resolver for mapping statement IDs to graph node IDs.
            graph: The graph to add nodes to.
            statement: The statement structure being processed.
        """
        self.id_resolver = id_resolver
        self.graph = graph
        self.statement = statement

    @abstractmethod
    def can_process(self, item: StatementItem) -> bool:
        """Check if this processor can handle the given item type.

        Args:
            item: The statement item to check.

        Returns:
            True if this processor can handle the item type.
        """

    @abstractmethod
    def process(self, item: StatementItem, is_retry: bool = False) -> ProcessorResult:
        """Process the item and add it to the graph if needed.

        Args:
            item: The statement item to process.
            is_retry: Whether this is a retry attempt (affects error logging).

        Returns:
            ProcessorResult indicating success/failure and details.
        """

    def resolve_inputs(self, input_ids: list[str]) -> tuple[list[str], list[tuple[str, str | None]]]:
        """Resolve input IDs to graph node IDs.

        Args:
            input_ids: List of statement item IDs to resolve.

        Returns:
            Tuple of (resolved_node_ids, missing_details).
            missing_details contains tuples of (item_id, resolved_node_id_or_none).
        """
        resolved = []
        missing = []

        for input_id in input_ids:
            node_id = self.id_resolver.resolve(input_id, self.graph)
            if node_id and self.graph.has_node(node_id):
                resolved.append(node_id)
            else:
                missing.append((input_id, node_id))

        return resolved, missing

    def _handle_missing_inputs(
        self,
        item: StatementItem,
        missing: list[tuple[str, str | None]],
        is_retry: bool,
    ) -> ProcessorResult:
        """Handle missing input nodes consistently across processors.

        Args:
            item: The item being processed.
            missing: List of missing input details.
            is_retry: Whether this is a retry attempt.

        Returns:
            ProcessorResult with appropriate error details.
        """
        missing_summary = [
            (f"item '{i_id}' needs node '{n_id}'" if n_id else f"item '{i_id}' not found/mappable")
            for i_id, n_id in missing
        ]

        if is_retry:
            logger.error(
                "Retry failed for %s '%s' in statement '%s': missing required inputs: %s",
                type(item).__name__,
                item.id,
                self.statement.id,
                "; ".join(missing_summary),
            )
            return ProcessorResult(
                success=False,
                error_message=f"Missing inputs on retry: {missing_summary}",
                missing_inputs=missing,
            )
        else:
            # Don't log on first attempt - allows dependency resolution
            return ProcessorResult(success=False, missing_inputs=missing)


class MetricItemProcessor(ItemProcessor):
    """Processor for MetricLineItem objects.

    Handles the creation of metric-based calculation nodes by:
    1. Looking up the metric in the registry
    2. Validating input mappings
    3. Resolving input IDs to graph nodes
    4. Adding the metric node to the graph
    """

    def can_process(self, item: StatementItem) -> bool:
        """Check if item is a MetricLineItem."""
        return isinstance(item, MetricLineItem)

    def process(self, item: StatementItem, is_retry: bool = False) -> ProcessorResult:
        """Process a MetricLineItem and add it to the graph."""
        # Early validation
        if not isinstance(item, MetricLineItem):
            return ProcessorResult(success=False, error_message="Invalid item type")

        # Check if node already exists
        if self.graph.has_node(item.id):
            return ProcessorResult(success=True, node_added=False)

        # Initialize result variables
        error_message = None
        node_added = False

        # Get metric from registry
        try:
            metric = metric_registry.get(item.metric_id)
        except MetricError as e:
            logger.exception("Cannot populate item '%s': Metric '%s' not found in registry", item.id, item.metric_id)
            error_message = f"Metric '{item.metric_id}' not found: {e}"

        # Validate input mappings if no error yet
        if not error_message:
            error_message = self._validate_metric_inputs(metric, item)

        # Resolve metric inputs if no error yet
        if not error_message:
            resolved_map, missing = self._resolve_metric_inputs(metric, item)
            if missing:
                return self._handle_missing_inputs(item, missing, is_retry)

            # Add to graph
            try:
                self.graph.add_metric(
                    metric_name=item.metric_id,
                    node_name=item.id,
                    input_node_map=resolved_map,
                )
                node_added = True
            except Exception as e:
                logger.exception("Failed to add metric node '%s'", item.id)
                error_message = f"Failed to add metric node: {e}"

        # Single exit point
        if error_message:
            return ProcessorResult(success=False, error_message=error_message)
        return ProcessorResult(success=True, node_added=node_added)

    def _validate_metric_inputs(self, metric: Any, item: MetricLineItem) -> str | None:
        """Validate that the item provides all required metric inputs."""
        provided_inputs = set(item.inputs.keys())
        required_inputs = set(metric.inputs)

        if provided_inputs != required_inputs:
            missing_req = required_inputs - provided_inputs
            extra_prov = provided_inputs - required_inputs
            error_msg = f"Input mapping mismatch for metric '{item.metric_id}' in item '{item.id}'."

            if missing_req:
                error_msg += f" Missing required metric inputs: {missing_req}."
            if extra_prov:
                error_msg += f" Unexpected inputs provided: {extra_prov}."

            logger.error(error_msg)
            return error_msg

        return None

    def _resolve_metric_inputs(
        self, metric: Any, item: MetricLineItem
    ) -> tuple[dict[str, str], list[tuple[str, str | None]]]:
        """Resolve metric input mappings to graph node IDs."""
        resolved_map = {}
        missing = []

        for metric_input_name in metric.inputs:
            input_item_id = item.inputs[metric_input_name]
            node_id = self.id_resolver.resolve(input_item_id, self.graph)

            if node_id and self.graph.has_node(node_id):
                resolved_map[metric_input_name] = node_id
            else:
                missing.append((input_item_id, node_id))

        return resolved_map, missing


class CalculatedItemProcessor(ItemProcessor):
    """Processor for CalculatedLineItem objects.

    Handles the creation of calculation nodes with specific operations by:
    1. Resolving input IDs to graph nodes
    2. Getting sign conventions from input items
    3. Creating the calculation node with proper sign handling
    """

    def can_process(self, item: StatementItem) -> bool:
        """Check if item is a CalculatedLineItem."""
        return isinstance(item, CalculatedLineItem)

    def process(self, item: StatementItem, is_retry: bool = False) -> ProcessorResult:
        """Process a CalculatedLineItem and add it to the graph."""
        if not isinstance(item, CalculatedLineItem):
            return ProcessorResult(success=False, error_message="Invalid item type")

        # Check if node already exists
        if self.graph.has_node(item.id):
            return ProcessorResult(success=True, node_added=False)

        # Command: create any needed signed nodes
        neg_base_ids: list[str] = []
        for input_id in item.input_ids:
            input_item = self.statement.find_item_by_id(input_id)
            if input_item and getattr(input_item, "sign_convention", 1) == -1:
                node_id = self.id_resolver.resolve(input_id, self.graph)
                if node_id:
                    neg_base_ids.append(node_id)
        if neg_base_ids:
            self.graph.ensure_signed_nodes(neg_base_ids)

        # Query: resolve inputs without mutating graph
        resolved_inputs, missing = self._resolve_inputs(item)
        if missing:
            return self._handle_missing_inputs(item, missing, is_retry)

        # Add calculation node
        error_message = None
        try:
            self.graph.add_calculation(
                name=item.id,
                input_names=resolved_inputs,
                operation_type=item.calculation_type,
                **item.parameters,
            )
        except (
            NodeError,
            CircularDependencyError,
            CalculationError,
            ConfigurationError,
        ) as e:
            error_msg = f"Failed to add calculation node '{item.id}': {e}"
            logger.exception(error_msg)
            error_message = str(e)
        except Exception as e:
            error_msg = f"Unexpected error adding calculation node '{item.id}': {e}"
            logger.exception(error_msg)
            error_message = f"Unexpected error: {e}"

        if error_message:
            return ProcessorResult(success=False, error_message=error_message)
        return ProcessorResult(success=True, node_added=True)

    def _resolve_inputs(self, item: CalculatedLineItem) -> tuple[list[str], list[tuple[str, str | None]]]:
        """Resolve input IDs to graph node or signed-node IDs without side effects.

        Args:
            item: The CalculatedLineItem being processed.

        Returns:
            Tuple of (resolved_node_ids, missing_details).
        """
        resolved: list[str] = []
        missing: list[tuple[str, str | None]] = []

        for input_id in item.input_ids:
            node_id = self.id_resolver.resolve(input_id, self.graph)
            # Missing base node
            if not node_id or not self.graph.has_node(node_id):
                missing.append((input_id, node_id))
                continue
            # Determine sign
            input_item = self.statement.find_item_by_id(input_id)
            sign = getattr(input_item, "sign_convention", 1) if input_item else 1
            if sign == -1:
                signed_id = f"{node_id}_signed"
                # Represent signed node if exists, else missing
                if signed_id in self.graph.nodes:
                    resolved.append(signed_id)
                else:
                    missing.append((input_id, signed_id))
            else:
                resolved.append(node_id)
        return resolved, missing


class SubtotalItemProcessor(ItemProcessor):
    """Processor for SubtotalLineItem objects.

    Handles the creation of subtotal (addition) nodes by:
    1. Resolving input IDs to graph nodes
    2. Adding an addition calculation node
    """

    def can_process(self, item: StatementItem) -> bool:
        """Check if item is a SubtotalLineItem."""
        return isinstance(item, SubtotalLineItem)

    def process(self, item: StatementItem, is_retry: bool = False) -> ProcessorResult:
        """Process a SubtotalLineItem and add it to the graph."""
        if not isinstance(item, SubtotalLineItem):
            return ProcessorResult(success=False, error_message="Invalid item type")

        # Check if node already exists
        if self.graph.has_node(item.id):
            return ProcessorResult(success=True, node_added=False)

        # Handle empty subtotals
        if not item.item_ids:
            logger.debug("Subtotal item '%s' has no input items", item.id)
            return ProcessorResult(success=True, node_added=False)

        # Resolve inputs
        resolved, missing = self.resolve_inputs(item.item_ids)
        if missing:
            return self._handle_missing_inputs(item, missing, is_retry)

        # Add subtotal as addition calculation
        error_message = None
        try:
            self.graph.add_calculation(name=item.id, input_names=resolved, operation_type="addition")
        except (
            NodeError,
            CircularDependencyError,
            CalculationError,
            ConfigurationError,
        ) as e:
            error_msg = f"Failed to add subtotal node '{item.id}': {e}"
            logger.exception(error_msg)
            error_message = str(e)
        except Exception as e:
            error_msg = f"Unexpected error adding subtotal node '{item.id}': {e}"
            logger.exception(error_msg)
            error_message = f"Unexpected error: {e}"

        if error_message:
            return ProcessorResult(success=False, error_message=error_message)
        return ProcessorResult(success=True, node_added=True)


class ItemProcessorManager:
    """Manages the collection of item processors.

    This class coordinates the processing of different statement item types
    by delegating to the appropriate processor based on the item type.
    """

    def __init__(self, id_resolver: IDResolver, graph: Graph, statement: StatementStructure):
        """Initialize the processor manager with all available processors.

        Args:
            id_resolver: ID resolver for mapping statement IDs to graph node IDs.
            graph: The graph to add nodes to.
            statement: The statement structure being processed.
        """
        self.processors = [
            MetricItemProcessor(id_resolver, graph, statement),
            CalculatedItemProcessor(id_resolver, graph, statement),
            SubtotalItemProcessor(id_resolver, graph, statement),
        ]

    def process_item(self, item: StatementItem, is_retry: bool = False) -> ProcessorResult:
        """Process a statement item using the appropriate processor.

        Args:
            item: The statement item to process.
            is_retry: Whether this is a retry attempt.

        Returns:
            ProcessorResult from the appropriate processor, or a success result
            if no processor handles the item type (e.g., for LineItem).
        """
        for processor in self.processors:
            if processor.can_process(item):
                return processor.process(item, is_retry)

        # No processor found - this is OK for non-calculation items like LineItem
        logger.debug(
            "No processor for item type %s with ID '%s'. This is expected for non-calculation items.",
            type(item).__name__,
            item.id,
        )
        return ProcessorResult(success=True, node_added=False)
