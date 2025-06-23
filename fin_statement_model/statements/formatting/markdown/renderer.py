"""Helper class for rendering StatementStructure to markdown format.

Moved from `io.formats.markdown.renderer`.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fin_statement_model.core.errors import FinStatementModelError
from fin_statement_model.core.nodes import standard_node_registry
from fin_statement_model.statements.structure import (
    CalculatedLineItem,
    LineItem,
    MetricLineItem,
    Section,
    StatementItem,
    StatementItemType,
    StatementStructure,
    SubtotalLineItem,
)

from .models import MarkdownStatementItem

if TYPE_CHECKING:
    from fin_statement_model.core.graph import Graph

logger = logging.getLogger(__name__)


class MarkdownStatementRenderer:
    """Render StatementStructure to markdown items list."""

    def __init__(self, graph: Graph, indent_spaces: int = 4):
        """Initialise the renderer.

        Args:
            graph: Source graph providing values for line items.
            indent_spaces: Spaces used to indent nested sections.
        """
        self.graph = graph
        self.indent_spaces = indent_spaces
        self.periods = sorted(graph.periods)

    def render_structure(
        self,
        structure: StatementStructure,
        historical_periods: set[str] | None = None,
        forecast_periods: set[str] | None = None,
    ) -> list[MarkdownStatementItem]:
        """Render *structure* into a flat list of MarkdownStatementItem.

        Args:
            structure: The (potentially nested) statement structure object.
            historical_periods: Period identifiers that should be considered
                historical (used further downstream for header labelling).
            forecast_periods: Period identifiers marked as forecast.

        Returns:
            A list of items preserving the hierarchical *level* information so
            that the table formatter can indent each description accordingly.
        """
        _ = (historical_periods, forecast_periods)  # Parameters intentionally unused
        items: list[MarkdownStatementItem] = []
        for section in structure.sections:
            items.extend(self._render_section(section, level=0))
        return items

    def _render_section(self, section: Section, level: int) -> list[MarkdownStatementItem]:
        items: list[MarkdownStatementItem] = []
        for item in section.items:
            if isinstance(item, Section):
                items.extend(self._render_section(item, level + 1))
            else:
                rendered = self._render_item(item, level + 1)
                if rendered:
                    items.append(rendered)
        if hasattr(section, "subtotal") and section.subtotal:
            subtotal_rendered = self._render_item(section.subtotal, level + 1)
            if subtotal_rendered:
                items.append(subtotal_rendered)
        return items

    def _render_item(self, item: StatementItem, level: int) -> MarkdownStatementItem | None:
        try:
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
        except Exception as exc:  # noqa: BLE001 - broad catch required for renderer robustness
            logger.warning("Failed to render item %s: %s", item.id, exc)

            # Legacy behaviour expected by the test-suite: still return a
            # MarkdownStatementItem so that downstream formatters can include
            # the row, but flag all period values with an "ERROR" marker.
            error_values: dict[str, float | int | str | None] = dict.fromkeys(self.periods, "ERROR")

            return MarkdownStatementItem(
                name=item.name,
                values=error_values,
                level=level,
                is_subtotal=(item.item_type == StatementItemType.SUBTOTAL),
                sign_convention=getattr(item, "sign_convention", 1),
                display_format=item.display_format,
                units=item.units,
                display_scale_factor=item.display_scale_factor,
                is_contra=item.is_contra,
            )

    def _extract_values(self, item: StatementItem) -> dict[str, float | int | str | None]:
        values: dict[str, float | int | str | None] = {}
        node_id = self._get_node_id(item)

        # If we cannot resolve the node ID we follow legacy behaviour expected
        # by the test-suite: return a dict filled with ``None``.
        if not node_id:
            logger.warning("Could not determine node ID for item: %s", item.id)
            return dict.fromkeys(self.periods)

        try:
            try:
                node = self.graph.get_node(node_id)
            except KeyError as err:
                logger.warning("Error extracting values for item %s: %s", item.id, err)
                return dict.fromkeys(self.periods)

            if node is None:
                logger.warning("Node '%s' not found for item: %s", node_id, item.id)
                return dict.fromkeys(self.periods)

            for period in self.periods:
                raw_val: float | int | str | None

                if isinstance(item, CalculatedLineItem | SubtotalLineItem | MetricLineItem):
                    try:
                        raw_val = self.graph.calculate(node_id, period)
                    except (FinStatementModelError, Exception):
                        logger.warning("Calculation error for %s@%s", node_id, period)
                        values[period] = "CALC_ERR"
                        continue
                else:  # Simple LineItem with direct access
                    try:
                        raw_val = node.calculate(period)
                    except (FinStatementModelError, Exception):  # pragma: no cover - defensive catch-all
                        logger.warning("Error calling calculate on node %s@%s", node_id, period)
                        values[period] = "CALC_ERR"
                        continue

                values[period] = self._apply_formatting(raw_val, item)

        except FinStatementModelError as e:  # pragma: no cover - unexpected issues
            logger.warning("Error extracting values for item %s: %s", item.id, e)
            return dict.fromkeys(self.periods, "ERROR")

        return values

    def _get_node_id(self, item: StatementItem) -> str | None:
        if isinstance(item, LineItem):
            if item.node_id:
                return item.node_id
            if item.standard_node_ref:
                return item.get_resolved_node_id(standard_node_registry)
            return None
        if isinstance(item, CalculatedLineItem | SubtotalLineItem | MetricLineItem):
            return item.id
        return None

    def _apply_formatting(self, raw_val: float | int | str | None, item: StatementItem) -> float | int | str | None:
        if raw_val is None or isinstance(raw_val, str):
            return raw_val
        if isinstance(raw_val, int | float):
            signed = raw_val * getattr(item, "sign_convention", 1)
            scaled = signed * item.display_scale_factor
            return scaled
        return raw_val
