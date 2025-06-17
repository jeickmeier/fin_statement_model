"""Helper class for rendering StatementStructure to markdown format."""

import logging
from typing import Optional, Union

from fin_statement_model.core.graph import Graph
from fin_statement_model.statements.structure import (
    Section,
    StatementItem,
    StatementItemType,
    StatementStructure,
    LineItem,
    CalculatedLineItem,
    SubtotalLineItem,
    MetricLineItem,
)
from fin_statement_model.io.formats.markdown.models import MarkdownStatementItem
from fin_statement_model.core.nodes import standard_node_registry

logger = logging.getLogger(__name__)


class MarkdownStatementRenderer:
    """Helper class that renders StatementStructure to markdown format.

    This class handles the recursive traversal of a StatementStructure and
    extracts values from the graph to create formatted items for markdown output.
    """

    def __init__(self, graph: Graph, indent_spaces: int = 4):
        """Initialize the renderer.

        Args:
            graph: The Graph object containing financial data.
            indent_spaces: Number of spaces per indentation level.
        """
        self.graph = graph
        self.indent_spaces = indent_spaces
        self.periods = sorted(list(graph.periods))

    def render_structure(
        self,
        structure: StatementStructure,
        historical_periods: Optional[set[str]] = None,
        forecast_periods: Optional[set[str]] = None,
    ) -> list[MarkdownStatementItem]:
        """Traverse StatementStructure and extract formatted items.

        Args:
            structure: The StatementStructure to render.
            historical_periods: Set of historical period names.
            forecast_periods: Set of forecast period names.

        Returns:
            List of MarkdownStatementItem objects ready for formatting.
        """
        logger.debug(f"Rendering statement structure: {structure.id}")
        items = []

        for section in structure.sections:
            items.extend(self._render_section(section, level=0))

        logger.debug(f"Rendered {len(items)} items from structure")
        return items

    def _render_section(
        self, section: Section, level: int
    ) -> list[MarkdownStatementItem]:
        """Recursively render a section and its contents.

        Args:
            section: The Section to render.
            level: Current indentation level.

        Returns:
            List of rendered items from this section.
        """
        items = []

        # Process items within the section
        for item in section.items:
            if isinstance(item, Section):
                # Nested section - recurse
                items.extend(self._render_section(item, level + 1))
            else:
                # Statement item (LineItem, CalculatedLineItem, etc.)
                rendered_item = self._render_item(item, level + 1)
                if rendered_item:
                    items.append(rendered_item)

        # Process section subtotal if exists
        if hasattr(section, "subtotal") and section.subtotal:
            rendered_subtotal = self._render_item(section.subtotal, level + 1)
            if rendered_subtotal:
                items.append(rendered_subtotal)

        return items

    def _render_item(
        self, item: StatementItem, level: int
    ) -> Optional[MarkdownStatementItem]:
        """Render a single statement item with values from graph.

        Args:
            item: The StatementItem to render.
            level: Current indentation level.

        Returns:
            MarkdownStatementItem or None if item couldn't be rendered.
        """
        try:
            # Extract values based on item type
            values = self._extract_values(item)

            return MarkdownStatementItem(
                name=item.name,
                values=values,
                level=level,
                is_subtotal=(item.item_type == StatementItemType.SUBTOTAL),
                sign_convention=getattr(item, "sign_convention", 1),
                display_format=item.display_format,
                units=item.units,
                display_scale_factor=item.display_scale_factor,
                is_contra=item.is_contra,
            )
        except Exception as e:
            logger.warning(f"Failed to render item {item.id}: {e}")
            return None

    def _extract_values(
        self, item: StatementItem
    ) -> dict[str, Union[float, int, str, None]]:
        """Extract values for an item from the graph.

        Args:
            item: The StatementItem to extract values for.

        Returns:
            Dictionary mapping periods to values.
        """
        values = {}

        # Get the node ID based on item type
        node_id = self._get_node_id(item)
        if not node_id:
            logger.warning(f"Could not determine node ID for item: {item.id}")
            return {period: None for period in self.periods}

        try:
            node = self.graph.get_node(node_id)
            if node is None:
                logger.warning(f"Node '{node_id}' returned None for item: {item.id}")
                return {period: None for period in self.periods}

            for period in self.periods:
                raw_value = None

                # Calculation items use graph.calculate, pure line items use node.calculate
                if isinstance(
                    item, (CalculatedLineItem, SubtotalLineItem, MetricLineItem)
                ):
                    # Calculate value for derived items
                    try:
                        raw_value = self.graph.calculate(node_id, period)
                    except Exception as calc_error:
                        logger.warning(
                            f"Calculation failed for node '{node_id}' period '{period}': {calc_error}"
                        )
                        raw_value = "CALC_ERR"
                elif isinstance(item, LineItem):
                    # Direct value from node for basic line items
                    raw_value = node.calculate(period)
                else:
                    logger.warning(
                        f"Unsupported item type: {type(item)} for item: {item.id}"
                    )
                    raw_value = None

                # Apply sign convention and scaling
                values[period] = self._apply_formatting(raw_value, item)

        except KeyError:
            logger.warning(f"Node '{node_id}' not found in graph for item: {item.id}")
            values = {period: None for period in self.periods}
        except Exception:
            logger.exception(f"Error extracting values for item {item.id}")
            values = {period: "ERROR" for period in self.periods}

        return values

    def _get_node_id(self, item: StatementItem) -> Optional[str]:
        """Get the node ID for a statement item.

        Args:
            item: The StatementItem to get node ID for.

        Returns:
            The node ID or None if it couldn't be determined.
        """
        if isinstance(item, LineItem):
            # For LineItem, try to resolve node_id or standard_node_ref
            if item.node_id:
                return item.node_id
            elif item.standard_node_ref:
                return item.get_resolved_node_id(standard_node_registry)
            else:
                return None
        elif isinstance(item, CalculatedLineItem | SubtotalLineItem | MetricLineItem):
            # For calculated items, use the item ID as node ID
            return item.id
        else:
            logger.warning(f"Unknown item type for node ID resolution: {type(item)}")
            return None

    def _apply_formatting(
        self, raw_value: Union[float, int, str, None], item: StatementItem
    ) -> Union[float, int, str, None]:
        """Apply sign convention and scaling to a raw value.

        Args:
            raw_value: The raw value from the graph.
            item: The StatementItem containing formatting info.

        Returns:
            The formatted value.
        """
        if raw_value is None or isinstance(raw_value, str):
            # Keep None and error strings as-is
            return raw_value

        if isinstance(raw_value, int | float):
            # Apply sign convention
            sign_convention = getattr(item, "sign_convention", 1)
            formatted_value = raw_value * sign_convention

            # Apply display scale factor
            scale_factor = item.display_scale_factor
            if scale_factor != 1.0:
                formatted_value = formatted_value * scale_factor

            return formatted_value

        return raw_value
